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
    private lateinit var testConnection: Button
    private lateinit var endpoint: EditText
    private lateinit var token: EditText
    private lateinit var task: EditText
    private lateinit var model: EditText
    private lateinit var localRoute: CheckBox
    private lateinit var vault: ConnectionVault
    private lateinit var savedStatus: TextView
    private var connectionBusy = false
    private val storage = java.util.concurrent.Executors.newSingleThreadExecutor()

    private fun connectionEnabled(enabled: Boolean) {
        connectionBusy = !enabled
        localRoute.isEnabled = enabled
        endpoint.isEnabled = enabled && !localRoute.isChecked
        token.isEnabled = enabled
        model.isEnabled = enabled && localRoute.isChecked
        task.isEnabled = enabled
        if (::ask.isInitialized) refresh()
    }

    private fun restoreConnection() {
        val local = localRoute.isChecked
        connectionEnabled(false)
        storage.execute {
            val result = runCatching { vault.settings(local) }
            runOnUiThread {
                result.fold(onSuccess = { saved ->
                    endpoint.setText(saved?.endpoint ?: if (local) "http://localhost:20128/v1" else "")
                    model.setText(saved?.model ?: "auto")
                    task.setText(saved?.task ?: "")
                    savedStatus.text = if (saved?.hasToken == true) "Token saved securely; leave token field blank to use it."
                        else "No saved token. Enter one, then Save connection or Send."
                }, onFailure = {
                    savedStatus.text = "Saved connection unavailable. Forget saved connection, then re-enter it."
                })
                token.text.clear()
                connectionEnabled(true)
            }
        }
    }

    private fun saveConnection() {
        if (connectionBusy) return
        discardProposal()
        val local = localRoute.isChecked
        val address = endpoint.text.toString().trim()
        val modelId = model.text.toString()
        val instruction = task.text.toString()
        val replacement = token.text.toString()
        connectionEnabled(false)
        storage.execute {
            val result = runCatching {
                vault.save(local, address, modelId, instruction, replacement)
                vault.settings(local)?.hasToken == true
            }
            runOnUiThread {
                result.fold(onSuccess = { hasToken ->
                    token.text.clear()
                    savedStatus.text = if (hasToken) "Connection saved. Saved token can be used without displaying it."
                        else "Settings saved. Enter a token before sending."
                }, onFailure = { savedStatus.text = "Could not save. Check URL/token; nothing was sent." })
                connectionEnabled(true)
            }
        }
    }

    private fun discardProposal() {
        requestGeneration++
        client?.cancel()
        client = null
        gate.clear()
        if (::approve.isInitialized) approve.isEnabled = false
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        vault = ConnectionVault(applicationContext)
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
        layout.addView(Button(this).apply {
            text = "Inspect one screenshot locally"
            setOnClickListener {
                discardProposal()
                if (DemoAccessibilityService.instance?.session?.state == SessionState.READY) {
                    startActivity(Intent(this@MainActivity, CaptureActivity::class.java))
                } else status.text = "Arm the supervised session before requesting capture."
            }
        })
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
        model = field("Model override (optional; auto lets OmniRoute choose)", 200).apply { setText("auto") }
        localRoute = CheckBox(this).apply {
            text = "Use OmniRoute running on this tablet"
            isSaveEnabled = false
            setOnCheckedChangeListener { _, checked ->
                discardProposal()
                token.hint = if (checked) "New OmniRoute token (blank uses saved token)" else "New bridge token (blank uses saved token)"
                token.text.clear()
                if (::savedStatus.isInitialized) restoreConnection()
                if (::proposal.isInitialized) proposal.text = "Connection mode changed; proposal cleared."
                if (::ask.isInitialized) refresh()
            }
            layout.addView(this)
        }
        localRoute.isChecked = vault.selectedLocal()
        savedStatus = TextView(this).also { layout.addView(it) }
        layout.addView(Button(this).apply {
            text = "Save connection securely"
            setOnClickListener { saveConnection() }
        })
        layout.addView(Button(this).apply {
            text = "Forget saved connection and token"
            setOnClickListener {
                if (!connectionBusy) {
                    discardProposal()
                    val local = localRoute.isChecked
                    connectionEnabled(false)
                    storage.execute {
                        val result = runCatching { vault.forget(local) }
                        runOnUiThread {
                            token.text.clear()
                            savedStatus.text = if (result.isSuccess) "Saved connection and token forgotten."
                                else "Could not remove saved connection."
                            connectionEnabled(true)
                        }
                    }
                }
            }
        })
        proposal = TextView(this).also { layout.addView(it) }
        ask = Button(this).apply {
            text = "Send task to AI server"
            setOnClickListener { requestProposal() }
            layout.addView(this)
        }
        testConnection = Button(this).apply {
            text = "Test saved connection (no action)"
            setOnClickListener { requestProposal(testOnly = true) }
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
        restoreConnection()
        refresh()
    }

    private fun requestProposal(testOnly: Boolean = false) {
        if (connectionBusy) return
        discardProposal()
        val service = DemoAccessibilityService.instance ?: return
        if (!consent.isChecked || service.session.state != SessionState.READY) return
        val revision = service.session.revision
        val generation = requestGeneration
        val request = ProposalClient()
        client = request
        val address = endpoint.text.toString().trim()
        val accessToken = token.text.toString()
        val savedTask = task.text.toString()
        val instruction = if (testOnly) "Connection test: return action NONE and explain briefly that this is only a connection test."
            else savedTask
        val useLocalRoute = localRoute.isChecked
        val modelId = model.text.toString().trim()
        proposal.text = "Waiting for AI proposal…"
        connectionEnabled(false)
        storage.execute {
            val result = runCatching {
                vault.save(useLocalRoute, address, modelId, savedTask, accessToken)
                vault.useToken(useLocalRoute, address) { savedToken ->
                    request.request(address, savedToken, instruction, useLocalRoute, modelId)
                }
            }
            runOnUiThread {
                token.text.clear()
                savedStatus.text = "Connection saved if valid. Token is never restored into this field."
                connectionEnabled(true)
                if (generation == requestGeneration) {
                    client = null
                    if (DemoAccessibilityService.instance !== service ||
                        service.session.revision != revision ||
                        service.session.state != SessionState.READY || !consent.isChecked) {
                        discardProposal()
                        proposal.text = "Session changed; response discarded."
                    } else result.fold(onSuccess = { (action, explanation) ->
                        approve.isEnabled = !testOnly && gate.offer(action, service.session)
                        if (testOnly) {
                            gate.clear()
                            proposal.text = "Connection test passed. Saved token authenticated and model returned a valid proposal. No action was authorized or executed."
                        } else proposal.text = "AI explanation (untrusted):\n$explanation\n\n" +
                            if (action == "OPEN_DEMO") "Proposed action: open $DEMO_URL" else "No supported action proposed."
                    }, onFailure = {
                        gate.clear()
                        approve.isEnabled = false
                        proposal.text = requestFailureMessage(it)
                    })
                    refresh()
                }
            }
        }
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
            ask.isEnabled = state == SessionState.READY && consent.isChecked && client == null && !connectionBusy
            if (::testConnection.isInitialized) testConnection.isEnabled = ask.isEnabled
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

    override fun onDestroy() {
        storage.shutdown()
        super.onDestroy()
    }

    override fun onStop() {
        if (::savedStatus.isInitialized && !connectionBusy) {
            val local = localRoute.isChecked
            val address = endpoint.text.toString().trim()
            val modelId = model.text.toString()
            val savedTask = task.text.toString()
            val replacement = token.text.toString()
            token.text.clear()
            storage.execute { runCatching { vault.save(local, address, modelId, savedTask, replacement) } }
        }
        discardProposal()
        if (::proposal.isInitialized) proposal.text = "AI request and proposal cleared when app left foreground."
        DemoAccessibilityService.changed = null
        super.onStop()
    }
}
