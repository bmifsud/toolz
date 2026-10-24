package org.aief.personalautomator

/** Main-thread, one-use authorization; neither consent tokens nor pixels are persisted. */
class CapturePolicy {
    private var owner: SessionController? = null
    private var revision = -1L
    private var consumed = false
    fun begin(session: SessionController): Boolean {
        if (owner != null || session.state != SessionState.READY) return false
        owner = session
        revision = session.revision
        consumed = false
        return true
    }
    fun valid(session: SessionController?): Boolean = session != null && owner != null && owner === session &&
        session.state == SessionState.READY && session.revision == revision
    fun consume(session: SessionController?): Boolean {
        if (!valid(session) || consumed) return false
        consumed = true
        return true
    }
    fun clear() { owner = null; revision = -1L; consumed = false }
}
