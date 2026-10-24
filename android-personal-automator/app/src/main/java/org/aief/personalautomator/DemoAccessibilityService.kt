package org.aief.personalautomator

import android.accessibilityservice.AccessibilityService
import android.animation.ObjectAnimator
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.net.Uri
import android.os.Build
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** No node inspection or gestures. Only an explicitly armed, fixed-URL demonstration. */
class DemoAccessibilityService : AccessibilityService() {
    val session = SessionController()
    var message = ""
        private set
    private var panel: LinearLayout? = null
    private var pointer: TextView? = null
    private var pauseButton: Button? = null
    private var resumeButton: Button? = null
    private var demoButton: Button? = null
    private var pulse: ObjectAnimator? = null
    private val windows get() = getSystemService(WINDOW_SERVICE) as WindowManager

    override fun onServiceConnected() {
        super.onServiceConnected()
        stop()
        instance = this
        changed?.invoke()
    }

    fun arm() {
        if (instance !== this || session.state != SessionState.STOPPED) return
        session.arm()
        try {
            showPanel()
            message = getString(R.string.armed)
            update()
        } catch (_: RuntimeException) {
            stop()
            message = getString(R.string.overlay_failed)
            changed?.invoke()
        }
    }

    fun pause() {
        session.pause()
        CaptureActivity.invalidate()
        cancelPulse()
        update()
    }

    fun resume() {
        if (instance !== this || panel == null) { stop(); return }
        session.resume()
        update()
    }

    fun stop() {
        session.stop()
        CaptureActivity.invalidate()
        cancelPulse()
        panel?.let { try { windows.removeViewImmediate(it) } catch (_: RuntimeException) { } }
        panel = null
        pointer = null
        pauseButton = null
        resumeButton = null
        demoButton = null
        message = getString(R.string.stopped)
        changed?.invoke()
    }

    fun openDemo() {
        if (instance !== this || panel == null) { stop(); return }
        if (!session.authorize(Capability.OPEN_DEMO)) { update(); return }
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(DEMO_URL)).apply {
                addCategory(Intent.CATEGORY_BROWSABLE)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            })
            session.recordResult(true)
            message = getString(R.string.opened)
            cancelPulse()
            pointer?.let {
                pulse = ObjectAnimator.ofFloat(it, View.ALPHA, 1f, 0.25f, 1f).apply {
                    duration = 650
                    start()
                }
            }
            update()
        } catch (_: RuntimeException) {
            session.recordResult(false)
            stop()
            message = getString(R.string.browser_failed)
            changed?.invoke()
        }
    }

    private fun cancelPulse() {
        pulse?.cancel()
        pulse = null
        pointer?.alpha = 1f
    }

    private fun update() {
        pauseButton?.isEnabled = session.state == SessionState.READY
        resumeButton?.isEnabled = session.state == SessionState.PAUSED
        demoButton?.isEnabled = session.state == SessionState.READY
        pointer?.contentDescription = getString(R.string.pointer) + ": " + session.state.name
        changed?.invoke()
    }

    private fun showPanel() {
        val density = resources.displayMetrics.density
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(12, 8, 12, 8)
            setBackgroundColor(Color.rgb(24, 33, 45))
            elevation = 8 * density
        }
        pointer = TextView(this).apply {
            text = "●  " + getString(R.string.app_name)
            textSize = 16f
            setTextColor(Color.CYAN)
            setShadowLayer(10f, 0f, 0f, Color.CYAN)
            setLayerType(View.LAYER_TYPE_SOFTWARE, null)
            gravity = Gravity.CENTER
        }
        root.addView(pointer)
        fun button(label: Int, action: () -> Unit): Button = Button(this).apply {
            setText(label)
            setOnClickListener { action() }
            root.addView(this)
        }
        demoButton = button(R.string.open_demo) { openDemo() }
        pauseButton = button(R.string.pause) { pause() }
        resumeButton = button(R.string.resume) { resume() }
        button(R.string.stop) { stop() }
        val params = WindowManager.LayoutParams(
            (220 * density).toInt(), WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
            if (Build.VERSION.SDK_INT >= 30) {
                setFitInsetsTypes(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            }
        }
        panel = root
        windows.addView(root, params)
    }

    private fun disconnect() {
        stop()
        if (instance === this) instance = null
        changed?.invoke()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit
    override fun onInterrupt() { stop() }
    override fun onUnbind(intent: Intent?): Boolean { disconnect(); return super.onUnbind(intent) }
    override fun onDestroy() { disconnect(); super.onDestroy() }

    companion object {
        var instance: DemoAccessibilityService? = null
            private set
        var changed: (() -> Unit)? = null
    }
}
