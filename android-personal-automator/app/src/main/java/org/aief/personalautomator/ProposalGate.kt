package org.aief.personalautomator

/** One-use proposals tied to the exact uninterrupted authorization interval. */
class ProposalGate {
    private var revision: Long? = null
    fun offer(action: String, session: SessionController): Boolean {
        clear()
        if (action != "OPEN_DEMO" || session.state != SessionState.READY) return false
        revision = session.revision
        return true
    }
    fun consume(session: SessionController): Boolean {
        val allowed = revision == session.revision && session.state == SessionState.READY
        clear()
        return allowed
    }
    fun clear() { revision = null }
}
