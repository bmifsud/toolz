package org.aief.personalautomator

const val DEMO_URL = "https://github.com/bmifsud/POC-ARTRIOUT/pull/299"
enum class SessionState { STOPPED, READY, PAUSED }

enum class Capability(val requiresApproval: Boolean) {
    OPEN_DEMO(true),
    ANSWER(false),
    READ_UPTIME(false),
    RUN_TESTS(true),
    UNSUPPORTED(false)
}

enum class TaskCategory {
    ANSWER,
    READ_ONLY,
    DEVELOPMENT,
    DEVICE_ACTION,
    UNSUPPORTED
}

data class TaskProposal(
    val category: TaskCategory,
    val action: Capability,
    val explanation: String,
    val command: String = "",
    val requiresApproval: Boolean = action.requiresApproval
)

/** Main-thread session policy. No persistence: process/service recreation fails closed. */
class SessionController {
    var state: SessionState = SessionState.STOPPED
        private set
    var revision = 0L
        private set
    private val records = ArrayDeque<String>()
    val audit: List<String> get() = records.toList()

    fun arm() {
        if (state == SessionState.STOPPED) {
            revision++
            state = SessionState.READY
            record("Session armed by user")
        }
    }

    fun pause() {
        if (state == SessionState.READY) {
            revision++
            state = SessionState.PAUSED
            record("Session paused")
        }
    }

    fun resume() {
        if (state == SessionState.PAUSED) {
            revision++
            state = SessionState.READY
            record("Session resumed by user")
        }
    }

    fun stop() {
        revision++
        state = SessionState.STOPPED
        record("Session stopped")
    }

    fun authorize(action: Capability): Boolean {
        val allowed = state == SessionState.READY
        record("${action.name}: ${if (allowed) "authorized" else "denied"}")
        return allowed
    }

    fun recordResult(success: Boolean) {
        record(if (success) "Demo URL intent dispatched" else "Demo URL intent failed")
    }

    private fun record(message: String) {
        if (records.size == 50) records.removeFirst()
        records.addLast(message)
    }
}
