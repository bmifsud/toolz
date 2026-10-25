package org.aief.personalautomator

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*

/** One fresh projection, one display, one frame. Main-thread state and callbacks. */
class CaptureService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var used = false
    private var closed = false
    private val callback = object : MediaProjection.Callback() {
        override fun onStop() { if (!closed) CaptureActivity.invalidate() }
    }
    private fun foreground() {
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(NotificationChannel("capture", "Screen capture", NotificationManager.IMPORTANCE_LOW))
        check(manager.areNotificationsEnabled() &&
            manager.getNotificationChannel("capture").importance != NotificationManager.IMPORTANCE_NONE)
        val stop = PendingIntent.getService(this, 1, Intent(this, CaptureService::class.java).setAction("STOP"),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = Notification.Builder(this, "capture")
            .setSmallIcon(android.R.drawable.ic_menu_camera).setContentTitle("One-shot screen capture active")
            .setContentText("Local memory only · STOP to cancel").setOngoing(true)
            .addAction(Notification.Action.Builder(null, "STOP", stop).build()).build()
        if (Build.VERSION.SDK_INT >= 29) startForeground(42, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        else startForeground(42, notification)
    }

    internal fun shutdown() {
        if (closed) return
        closed = true
        handler.removeCallbacksAndMessages(null)
        runCatching { reader?.setOnImageAvailableListener(null, null) }
        runCatching { display?.release() }; display = null
        runCatching { reader?.close() }; reader = null
        projection?.let { runCatching { it.unregisterCallback(callback) }; runCatching { it.stop() } }
        projection = null
        if (active === this) active = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    override fun onDestroy() { shutdown(); super.onDestroy() }
    override fun onTaskRemoved(rootIntent: Intent?) { CaptureActivity.invalidate(); shutdown() }
    companion object {
        internal var active: CaptureService? = null
            private set
    }
    override fun onBind(intent: Intent?) = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // A queued start must not resurrect a service already being torn down.
        if (closed) { stopSelf(); return START_NOT_STICKY }
        if (intent?.action == "STOP") {
            CaptureActivity.invalidate(); shutdown(); return START_NOT_STICKY
        }
        try { foreground() } catch (_: RuntimeException) {
            CaptureActivity.invalidate(); shutdown(); return START_NOT_STICKY
        }
        val activity = CaptureActivity.current
        if (used || activity?.authorized() != true) {
            CaptureActivity.invalidate(); shutdown(); return START_NOT_STICKY
        }
        used = true
        active = this
        try {
            @Suppress("DEPRECATION")
            val consent = intent?.getParcelableExtra<Intent>("consent") ?: error("Missing consent")
            intent.removeExtra("consent")
            val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            val granted = manager.getMediaProjection(Activity.RESULT_OK, consent)
                ?: error("Projection unavailable")
            projection = granted
            granted.registerCallback(callback, handler)
            // <= 1024 x 1024 RGBA pixels; two reader buffers.
            val metrics = resources.displayMetrics
            val scale = minOf(1.0, 1024.0 / maxOf(metrics.widthPixels, metrics.heightPixels))
            val width = maxOf(1, (metrics.widthPixels * scale).toInt())
            val height = maxOf(1, (metrics.heightPixels * scale).toInt())
            val images = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
            reader = images
            images.setOnImageAvailableListener({ source ->
                if (!closed) takeFrame(source, activity, width, height)
            }, handler)
            display = granted.createVirtualDisplay("One-shot local preview", width, height,
                metrics.densityDpi, DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                images.surface, null, handler)
            handler.postDelayed({ if (!closed) CaptureActivity.invalidate() }, 8000)
        } catch (_: RuntimeException) { CaptureActivity.invalidate(); shutdown() }
        return START_NOT_STICKY
    }

    private fun takeFrame(source: ImageReader, activity: CaptureActivity, width: Int, height: Int) {
        var result: Bitmap? = null
        try {
            if (!activity.authorized()) { CaptureActivity.invalidate(); return }
            val image = source.acquireLatestImage() ?: return
            image.use {
                val plane = it.planes[0]
                require(plane.pixelStride == 4 && plane.rowStride >= width * 4)
                val pixels = IntArray(width * height)
                val buffer = plane.buffer
                for (y in 0 until height) for (x in 0 until width) {
                    val offset = y * plane.rowStride + x * 4
                    val r = buffer.get(offset).toInt() and 255
                    val g = buffer.get(offset + 1).toInt() and 255
                    val b = buffer.get(offset + 2).toInt() and 255
                    pixels[y * width + x] = (255 shl 24) or (r shl 16) or (g shl 8) or b
                }
                result = Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888)
                pixels.fill(0)
            }
            shutdown()
            result?.let { activity.show(it) }
            result = null
        } catch (_: RuntimeException) { result?.recycle(); CaptureActivity.invalidate(); shutdown() }
    }
}
