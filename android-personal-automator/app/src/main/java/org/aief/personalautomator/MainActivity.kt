package org.aief.personalautomator

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.WindowInsets
import android.text.InputType
import android.text.InputFilter
import android.widget.EditText
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

    private val gate = ProposalGate()
    private var client: ProposalClient? = null
    private var requestGeneration = 0
    private lateinit var proposal: TextView
    private lateinit var ask: Button
    private lateinit var approve: Button
    private lateinit var endpoint: EditText
    private lateinit var token: EditText
    private lateinit var task: EditText
    private lateinit var model: EditText
    private lateinit var localRoute: CheckBox

    private fun discardProposal() {
        requestGeneration++
        client?.cancel()
        client = null
        gate.clear()
        if (::approve.isInitialized) approve.isEnabled = false
    }

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
        layout.addView(TextView(this).apply {
            text = "AI proposal connection\nOnly your typed task is sent to your selected server or local OmniRoute and its AI providers. No screen contents are sent. Approving can only open the demo PR. This is separate from this ChatGPT conversation."
        })
        fun field(label: String, max: Int, secret: Boolean = false): EditText = EditText(this).apply {
            hint = label
            isSaveEnabled = false
            filters = arrayOf(InputFilter.LengthFilter(max))
            inputType = if (secret) InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                else InputType.TYPE_CLASS_TEXT
            importantForAutofill = android.view.View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
            layout.addView(this)
        }
        endpoint = field("Trusted server HTTPS URL, ending /proposal", 2048)
        token = field("Server access token (not an OpenAI API key)", 512, true)
        task = field("Task to send (up to 2000 characters)", 2000)
        model = field("OmniRoute model or combo ID (from your dashboard)", 200)
        localRoute = CheckBox(this).apply {
            text = "Use OmniRoute running on this tablet"
            isSaveEnabled = false
            setOnCheckedChangeListener { _, checked ->
                discardProposal()
                endpoint.setText(if (checked) "http://localhost:20128/v1" else "")
                endpoint.isEnabled = !checked
                token.hint = if (checked) "OmniRoute inference API token" else "Bridge access token"
                token.text.clear()
                model.isEnabled = checked
                if (::proposal.isInitialized) proposal.text = "Connection mode changed; proposal cleared."
                if (::ask.isInitialized) refresh()
            }
            layout.addView(this)
        }
        localRoute.isChecked = true
        proposal = TextView(this).also { layout.addView(it) }
        ask = Button(this).apply {
            text = "Send task to AI server"
            setOnClickListener { requestProposal() }
            layout.addView(this)
        }
        approve = Button(this).apply {
            text = "Approve: open demo PR #299"
            isEnabled = false
            setOnClickListener {
                val service = DemoAccessibilityService.instance
                if (service != null && gate.consume(service.session)) service.openDemo()
                discardProposal()
                proposal.text = "Proposal consumed. Check the session audit for dispatch result."
                refresh()
            }
            layout.addView(this)
        }
        layout.addView(Button(this).apply {
            text = "Reject / cancel AI request"
            setOnClickListener {
                discardProposal()
                proposal.text = "Request cancelled; proposal discarded."
                refresh()
            }
        })
        audit = TextView(this).also { layout.addView(it) }
        setContentView(scroll)
        scroll.requestApplyInsets()
        refresh()
    }

    private fun requestProposal() {
        discardProposal()
        val service = DemoAccessibilityService.instance ?: return
        if (!consent.isChecked || service.session.state != SessionState.READY) return
        val revision = service.session.revision
        val generation = requestGeneration
        val request = ProposalClient()
        client = request
        val address = endpoint.text.toString().trim()
        val accessToken = token.text.toString()
        val instruction = task.text.toString()
        val useLocalRoute = localRoute.isChecked
        val modelId = model.text.toString().trim()
        proposal.text = "Waiting for AI proposal…"
        refresh()
        Thread {
            val result = runCatching { request.request(address, accessToken, instruction, useLocalRoute, modelId) }
            runOnUiThread {
                if (generation == requestGeneration) {
                    client = null
                    if (DemoAccessibilityService.instance !== service ||
                        service.session.revision != revision ||
                        service.session.state != SessionState.READY || !consent.isChecked) {
                        discardProposal()
                        proposal.text = "Session changed; response discarded."
                    } else result.fold(onSuccess = { (action, explanation) ->
                        approve.isEnabled = gate.offer(action, service.session)
                        proposal.text = "AI explanation (untrusted):\n$explanation\n\n" +
                            if (action == "OPEN_DEMO") "Proposed action: open $DEMO_URL" else "No supported action proposed."
                    }, onFailure = {
                        gate.clear()
                        approve.isEnabled = false
                        proposal.text = "Request failed. Check connection, token and model ID. Nothing executed."
                    })
                    refresh()
                }
            }
        }.start()
    }

    private fun refresh() {
        if (!::arm.isInitialized) return
        val service = DemoAccessibilityService.instance
        val state = service?.session?.state ?: SessionState.STOPPED
        if (::ask.isInitialized) {
            if (state != SessionState.READY) {
                discardProposal()
                proposal.text = "AI proposal cleared: session is not ready."
            }
            ask.isEnabled = state == SessionState.READY && consent.isChecked && client == null
        }
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
        discardProposal()
        if (::proposal.isInitialized) proposal.text = "AI request and proposal cleared when app left foreground."
        DemoAccessibilityService.changed = null
        super.onStop()
    }
}
