package org.aief.personalautomator

/** One-use proposals tied to the exact uninterrupted authorization interval and supported capabilities. */
class ProposalGate {
    private var revision: Long? = null
    private var currentProposal: TaskProposal? = null

    fun offer(proposal: TaskProposal, session: SessionController): Boolean {
        clear()
        if (session.state != SessionState.READY) return false
        if (proposal.action == Capability.UNSUPPORTED) return false
        revision = session.revision
        currentProposal = proposal
        return true
    }

    fun consume(session: SessionController): TaskProposal? {
        val proposal = currentProposal
        val allowed = revision == session.revision && session.state == SessionState.READY && proposal != null
        val result = if (allowed) proposal else null
        clear()
        return result
    }

    fun clear() {
        revision = null
        currentProposal = null
    }
}
