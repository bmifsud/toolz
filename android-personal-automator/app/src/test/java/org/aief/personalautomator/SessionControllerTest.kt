package org.aief.personalautomator

import org.junit.Assert.*
import org.junit.Test

class SessionControllerTest {
    @Test fun startsStoppedAndRejectsActions() {
        val session = SessionController()
        assertEquals(SessionState.STOPPED, session.state)
        assertFalse(session.authorize(Capability.OPEN_DEMO))
    }

    @Test fun pauseBlocksActionsUntilExplicitResume() {
        val session = SessionController()
        session.arm()
        assertTrue(session.authorize(Capability.OPEN_DEMO))
        session.pause()
        assertFalse(session.authorize(Capability.OPEN_DEMO))
        session.arm() // Arming must not bypass pause.
        assertEquals(SessionState.PAUSED, session.state)
        session.resume()
        assertTrue(session.authorize(Capability.OPEN_DEMO))
    }

    @Test fun stopCannotBeUndoneByResume() {
        val session = SessionController()
        session.arm()
        session.stop()
        session.resume()
        assertFalse(session.authorize(Capability.OPEN_DEMO))
        session.arm()
        assertTrue(session.authorize(Capability.OPEN_DEMO))
    }

    @Test fun recreationDoesNotRestoreAuthorization() {
        val old = SessionController()
        old.arm()
        assertEquals(SessionState.STOPPED, SessionController().state)
    }

    @Test fun auditIsBoundedAndReturnedAsSnapshot() {
        val session = SessionController()
        val snapshot = session.audit
        repeat(100) { session.authorize(Capability.OPEN_DEMO) }
        assertTrue(snapshot.isEmpty())
        assertEquals(50, session.audit.size)
        assertTrue(session.audit.last().contains("denied"))
        session.recordResult(false)
        assertEquals("Demo URL intent failed", session.audit.last())
    }

    @Test fun pauseAndResumeCannotArmStoppedSession() {
        val session = SessionController()
        session.pause()
        session.resume()
        assertEquals(SessionState.STOPPED, session.state)
    }
}
