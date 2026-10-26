package org.aief.personalautomator

import org.junit.Assert.*
import org.junit.Test

class ProposalGateTest {
    @Test fun requiresReadyAndExactSupportedAction() {
        val session = SessionController()
        val gate = ProposalGate()
        val demoProposal = TaskProposal(TaskCategory.DEVICE_ACTION, Capability.OPEN_DEMO, "Open demo")
        val unsupportedProposal = TaskProposal(TaskCategory.UNSUPPORTED, Capability.UNSUPPORTED, "Unsupported")
        assertFalse(gate.offer(demoProposal, session))
        session.arm()
        assertFalse(gate.offer(unsupportedProposal, session))
        assertNull(gate.consume(session))
        assertTrue(gate.offer(demoProposal, session))
        assertNotNull(gate.consume(session))
        assertNull(gate.consume(session))
    }
    @Test fun pauseResumeInvalidatesApproval() {
        val session = SessionController().apply { arm() }
        val gate = ProposalGate()
        val demoProposal = TaskProposal(TaskCategory.DEVICE_ACTION, Capability.OPEN_DEMO, "Open demo")
        gate.offer(demoProposal, session)
        session.pause()
        session.resume()
        assertNull(gate.consume(session))
    }
    @Test fun stopAndRearmInvalidatesApproval() {
        val session = SessionController().apply { arm() }
        val gate = ProposalGate()
        val demoProposal = TaskProposal(TaskCategory.DEVICE_ACTION, Capability.OPEN_DEMO, "Open demo")
        gate.offer(demoProposal, session)
        session.stop()
        session.arm()
        assertNull(gate.consume(session))
    }
    @Test fun rejectAndUnsupportedReplacementClearApproval() {
        val session = SessionController().apply { arm() }
        val gate = ProposalGate()
        val demoProposal = TaskProposal(TaskCategory.DEVICE_ACTION, Capability.OPEN_DEMO, "Open demo")
        val unsupportedProposal = TaskProposal(TaskCategory.UNSUPPORTED, Capability.UNSUPPORTED, "Unsupported")
        gate.offer(demoProposal, session)
        gate.clear()
        assertNull(gate.consume(session))
        gate.offer(demoProposal, session)
        gate.offer(unsupportedProposal, session)
        assertNull(gate.consume(session))
    }
}

