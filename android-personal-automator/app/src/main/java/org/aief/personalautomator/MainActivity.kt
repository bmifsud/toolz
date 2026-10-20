package org.aief.personalautomator

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.WindowInsets
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var audit: TextView
    private lateinit var consent: CheckBox
    private lateinit var arm: Button
    private lateinit var demo: Button
    private lateinit var pause: Button
    private lateinit var resume: Button
    private lateinit var stop: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val padding = (16 * resources.displayMetrics.density).toInt()
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        val scroll = ScrollView(this).apply { addView(layout) }
        scroll.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            } else {
                @Suppress("DEPRECATION")
                view.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop,
                    insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
            }
            insets
        }
        layout.addView(TextView(this).apply { setText(R.string.app_name); textSize = 24f })
        layout.addView(TextView(this).apply { setText(R.string.disclosure); textSize = 16f })
        layout.addView(TextView(this).apply { text = DEMO_URL })
        consent = CheckBox(this).apply {
            setText(R.string.consent)
            isSaveEnabled = false
            setOnCheckedChangeListener { _, checked ->
                if (!checked) DemoAccessibilityService.instance?.stop()
                refresh()
            }
        }
        layout.addView(consent)
        fun button(label: Int, action: () -> Unit): Button = Button(this).apply {
            setText(label)
            setOnClickListener { action() }
            layout.addView(this)
        }
        button(R.string.settings) {
            if (consent.isChecked) {
                DemoAccessibilityService.instance?.stop()
                try { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
                catch (_: RuntimeException) { status.setText(R.string.settings_failed) }
            } else status.setText(R.string.consent_required)
        }
        status = TextView(this).also { layout.addView(it) }
        arm = button(R.string.arm) {
            if (consent.isChecked) DemoAccessibilityService.instance?.arm()
            refresh()
        }
        demo = button(R.string.open_demo) { DemoAccessibilityService.instance?.openDemo() }
        pause = button(R.string.pause) { DemoAccessibilityService.instance?.pause() }
        resume = button(R.string.resume) { DemoAccessibilityService.instance?.resume() }
        stop = button(R.string.stop) { DemoAccessibilityService.instance?.stop() }
        audit = TextView(this).also { layout.addView(it) }
        setContentView(scroll)
        scroll.requestApplyInsets()
        refresh()
    }

    private fun refresh() {
        if (!::arm.isInitialized) return
        val service = DemoAccessibilityService.instance
        val state = service?.session?.state ?: SessionState.STOPPED
        status.text = if (service == null) getString(R.string.disconnected)
            else "${state.name}\n${service.message}"
        arm.isEnabled = service != null && consent.isChecked && state == SessionState.STOPPED
        demo.isEnabled = state == SessionState.READY
        pause.isEnabled = state == SessionState.READY
        resume.isEnabled = state == SessionState.PAUSED
        stop.isEnabled = state != SessionState.STOPPED
        audit.text = getString(R.string.audit) + "\n" + (service?.session?.audit?.joinToString("\n") ?: "")
    }

    override fun onStart() {
        super.onStart()
        DemoAccessibilityService.changed = { refresh() }
        refresh()
    }

    override fun onStop() {
        DemoAccessibilityService.changed = null
        super.onStop()
    }
}
