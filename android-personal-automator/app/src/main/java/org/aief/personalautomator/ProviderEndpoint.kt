package org.aief.personalautomator

import java.net.URL

/** Local HTTP is restricted to the tablet's OmniRoute inference route. */
object ProviderEndpoint {
    fun target(endpoint: String, localRoute: Boolean, model: String): URL {
        val url = URL(endpoint)
        require(url.userInfo == null && url.ref == null && url.query == null)
        if (localRoute) {
            require(url.protocol == "http" && url.host in listOf("localhost", "127.0.0.1") &&
                url.port == 20128 && url.path == "/v1")
            require(model.isNotBlank() && model.length <= 200)
            return URL(endpoint + "/chat/completions")
        }
        require(url.protocol == "https" && url.host.isNotBlank())
        return url
    }
}
