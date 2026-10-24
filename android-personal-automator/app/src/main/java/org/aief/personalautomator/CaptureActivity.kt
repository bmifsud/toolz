package org.aief.personalautomator

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView

/** No saved state, files, sharing or network path for captured pixels. */
class CaptureActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private val policy = CapturePolicy()
    private var bitmap: Bitmap? = null
    private lateinit var preview: ImageView
    private lateinit var status: TextView
    private var waitingConsent = false
    private var started = false
    private val timeout = Runnable { cancel() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        if (savedInstanceState != null || current != null) { finish(); return }
        current = this
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 64, 24, 48)
        }
        status = TextView(this).apply {
            text = "One shot only. Android asks permission every time. Preview stays in memory for at most 30 seconds; never saved or uploaded. Protected content remains hidden."
        }
        root.addView(status)
        root.addView(Button(this).apply {
            text = "Request one-shot OS consent"
            setOnClickListener {
                if (android.os.Build.VERSION.SDK_INT >= 33 &&
                    checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
                    android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    waitingConsent = true
                    handler.postDelayed(timeout, 60000)
                    requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 2)
                    status.text = "Allow notifications, then tap capture again. Capture requires a visible notification."
                    return@setOnClickListener
                }
                if (!(getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager).areNotificationsEnabled()) {
                    status.text = "Enable this app's notifications in Android Settings before capture."
                    return@setOnClickListener
                }
                val session = DemoAccessibilityService.instance?.session
                if (started || session == null || !policy.begin(session)) return@setOnClickListener
                started = true
                isEnabled = false
                waitingConsent = true
                handler.postDelayed(timeout, 60000)
                try {
                    val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                    startActivityForResult(manager.createScreenCaptureIntent(), 1)
                } catch (_: RuntimeException) { cancel() }
            }
        })
        root.addView(Button(this).apply { text = "STOP / discard"; setOnClickListener { cancel() } })
        preview = ImageView(this).apply { isSaveEnabled = false; adjustViewBounds = true }
        root.addView(preview, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 2) {
            waitingConsent = false
            handler.removeCallbacks(timeout)
            if (grantResults.firstOrNull() != android.content.pm.PackageManager.PERMISSION_GRANTED) cancel()
        }
    }

    @Deprecated("Platform activity result callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 1) return
        waitingConsent = false
        if (current !== this || resultCode != RESULT_OK || data == null ||
            !policy.consume(DemoAccessibilityService.instance?.session)) { cancel(); return }
        handler.removeCallbacks(timeout)
        handler.postDelayed(timeout, 10000)
        try {
            startForegroundService(Intent(this, CaptureService::class.java)
                .putExtra("consent", data))
        } catch (_: RuntimeException) { cancel() }
    }

    internal fun authorized(): Boolean = current === this && started &&
        policy.valid(DemoAccessibilityService.instance?.session)

    internal fun show(image: Bitmap) {
        if (!authorized()) { image.recycle(); cancel(); return }
        bitmap = image
        preview.setImageBitmap(image)
        status.text = "Projection stopped. Local preview only; discarded in 30 seconds. Black regions may be protected content."
        handler.removeCallbacks(timeout)
        handler.postDelayed(timeout, 30000)
    }

    private fun cancel() { clear(); finish() }
    private fun clear() {
        if (current !== this) return
        current = null
        policy.clear()
        handler.removeCallbacksAndMessages(null)
        CaptureService.active?.shutdown()
        stopService(Intent(this, CaptureService::class.java))
        if (::preview.isInitialized) preview.setImageDrawable(null)
        bitmap?.recycle()
        bitmap = null
    }
    override fun onStop() {
        // The system consent UI may cover this Activity; all other departures discard.
        if (!waitingConsent) clear()
        super.onStop()
    }
    override fun onDestroy() { clear(); super.onDestroy() }

    companion object {
        internal var current: CaptureActivity? = null
            private set
        fun invalidate() { current?.cancel(); CaptureService.active?.shutdown() }
    }
}
