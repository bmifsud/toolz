package org.aief.personalautomator

import org.junit.Assert.*
import org.junit.Test

class ProviderEndpointTest {
    @Test fun localModeUsesOnlyFixedInferencePath() {
        for (host in listOf("localhost", "127.0.0.1")) {
            assertEquals("http://$host:20128/v1/chat/completions",
                ProviderEndpoint.target("http://$host:20128/v1", true, "my-combo").toString())
        }
    }
    @Test fun rejectsRemoteHttpAndChangedLocalRoutes() {
        for (url in listOf("http://example.com:20128/v1", "http://localhost:8080/v1",
            "http://localhost:20128/admin", "http://user:pass@localhost:20128/v1",
            "http://localhost:20128/v1?key=secret", "http://localhost:20128/v1#fragment",
            "https://localhost:20128/v1", "http://localhost.example.com:20128/v1")) {
            try {
                ProviderEndpoint.target(url, true, "my-combo")
                fail("Accepted invalid endpoint: $url")
            } catch (_: IllegalArgumentException) { }
        }
    }
    @Test fun localModeRequiresModelAndBridgeModeRequiresTls() {
        try {
            ProviderEndpoint.target("http://localhost:20128/v1", true, " ")
            fail("Accepted missing model")
        } catch (_: IllegalArgumentException) { }
        try {
            ProviderEndpoint.target("http://localhost:20128/v1", false, "")
            fail("Accepted cleartext bridge")
        } catch (_: IllegalArgumentException) { }
        assertEquals("https://bridge.example/proposal",
            ProviderEndpoint.target("https://bridge.example/proposal", false, "").toString())
    }
}
