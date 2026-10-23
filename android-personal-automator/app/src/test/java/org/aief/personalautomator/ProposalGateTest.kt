package org.aief.personalautomator

import org.junit.Assert.*
import org.junit.Test

class ProposalGateTest {
    @Test fun requiresReadyAndExactSupportedAction() {
        val session = SessionController()
        val gate = ProposalGate()
        assertFalse(gate.offer("OPEN_DEMO", session))
        session.arm()
        assertFalse(gate.offer("TAP", session))
        assertFalse(gate.consume(session))
        assertTrue(gate.offer("OPEN_DEMO", session))
        assertTrue(gate.consume(session))
        assertFalse(gate.consume(session))
    }
    @Test fun pauseResumeInvalidatesApproval() {
        val session = SessionController().apply { arm() }
        val gate = ProposalGate()
        gate.offer("OPEN_DEMO", session)
        session.pause()
        session.resume()
        assertFalse(gate.consume(session))
    }
    @Test fun stopAndRearmInvalidatesApproval() {
        val session = SessionController().apply { arm() }
        val gate = ProposalGate()
        gate.offer("OPEN_DEMO", session)
        session.stop()
        session.arm()
        assertFalse(gate.consume(session))
    }
    @Test fun rejectAndUnsupportedReplacementClearApproval() {
        val session = SessionController().apply { arm() }
        val gate = ProposalGate()
        gate.offer("OPEN_DEMO", session)
        gate.clear()
        assertFalse(gate.consume(session))
        gate.offer("OPEN_DEMO", session)
        gate.offer("NONE", session)
        assertFalse(gate.consume(session))
    }
}
