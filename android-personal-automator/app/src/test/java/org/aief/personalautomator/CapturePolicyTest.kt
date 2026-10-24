package org.aief.personalautomator

import org.junit.Assert.*
import org.junit.Test

class CapturePolicyTest {
    @Test fun stoppedSessionCannotBegin() {
        assertFalse(CapturePolicy().begin(SessionController()))
    }
    @Test fun consentIsSingleUse() {
        val session = SessionController().apply { arm() }
        val policy = CapturePolicy()
        assertTrue(policy.begin(session))
        assertFalse(policy.begin(session))
        assertTrue(policy.consume(session))
        assertFalse(policy.consume(session))
    }
    @Test fun pauseResumeInvalidatesConsent() {
        val session = SessionController().apply { arm() }
        val policy = CapturePolicy().apply { begin(session) }
        session.pause(); session.resume()
        assertFalse(policy.valid(session))
        assertFalse(policy.consume(session))
    }
    @Test fun stopRearmInvalidatesConsent() {
        val session = SessionController().apply { arm() }
        val policy = CapturePolicy().apply { begin(session) }
        session.stop(); session.arm()
        assertFalse(policy.consume(session))
    }
    @Test fun replacementServiceAndProcessFailClosed() {
        val session = SessionController().apply { arm() }
        val policy = CapturePolicy().apply { begin(session) }
        assertFalse(policy.consume(null))
        assertFalse(policy.consume(SessionController().apply { arm() }))
        assertFalse(CapturePolicy().consume(session))
    }
    @Test fun discardRevokesPreviewAuthorization() {
        val session = SessionController().apply { arm() }
        val policy = CapturePolicy().apply { begin(session); consume(session) }
        assertTrue(policy.valid(session))
        policy.clear()
        assertFalse(policy.valid(session))
        assertFalse(policy.consume(session))
    }
}
