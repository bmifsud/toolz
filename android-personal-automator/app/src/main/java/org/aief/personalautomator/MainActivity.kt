package org.aief.personalautomator

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** Read-only, user-initiated first milestone. No accessibility or overlay permissions requested. */
class MainActivity : Activity() {
    private var paused = false
    private var stopped = false
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(32, 32, 32, 32)
        }
        val ball = TextView(this).apply {
            text = "●"
            textSize = 64f
            setTextColor(Color.CYAN)
            gravity = Gravity.CENTER
            contentDescription = "Glowing ball placeholder"
        }
        val status = TextView(this).apply { text = "Ready: read-only GitHub demo"; textSize = 18f }
        fun addButton(label: String, action: () -> Unit) {
            layout.addView(Button(this).apply { text = label; setOnClickListener { action() } })
        }
        layout.addView(ball)
        layout.addView(status)
        addButton("Open PR #299 (read-only)") {
            if (!paused && !stopped) {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/bmifsud/POC-ARTRIOUT/pull/299")))
                status.text = "Opened GitHub PR in browser"
            }
        }
        addButton("Pause") { paused = true; status.text = "Paused" }
        addButton("Resume") {
            if (!stopped) { paused = false; status.text = "Ready: read-only GitHub demo" }
        }
        addButton("Stop") { stopped = true; paused = true; status.text = "Stopped — restart app to reset" }
        setContentView(layout)
    }
}
