package org.aief.personalautomator

import org.json.JSONObject
import java.net.URL
import javax.net.ssl.HttpsURLConnection

/** No redirects, persistence, screen data or provider API keys. One foreground request. */
class ProposalClient {
    @Volatile private var connection: HttpsURLConnection? = null
    @Volatile private var cancelled = false
    fun cancel() { cancelled = true; connection?.disconnect() }
    fun request(endpoint: String, token: String, task: String): Pair<String, String> {
        require(task.isNotBlank() && task.length <= 2000 && token.length in 32..512)
        require(token.all { it.code in 33..126 })
        val url = URL(endpoint)
        require(url.protocol == "https" && url.host.isNotBlank() && url.userInfo == null &&
            url.ref == null && url.query == null)
        val conn = url.openConnection() as HttpsURLConnection
        connection = conn
        try {
            check(!cancelled)
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 10000
            conn.readTimeout = 45000
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Authorization", "Bearer $token")
            val body = JSONObject().put("task", task).put("version", 1).toString()
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            check(conn.responseCode == 200)
            val bytes = conn.inputStream.use { it.readBytesLimited(8192) }
            check(!cancelled)
            val json = JSONObject(String(bytes, Charsets.UTF_8))
            require(json.length() == 2)
            val action = json.getString("action")
            val explanation = json.getString("explanation")
            require(action in listOf("OPEN_DEMO", "NONE") && explanation.length in 1..2000)
            return action to explanation
        } finally { conn.disconnect(); connection = null }
    }
    private fun java.io.InputStream.readBytesLimited(limit: Int): ByteArray {
        val output = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(1024)
        while (true) {
            val count = read(buffer)
            if (count < 0) break
            require(output.size() + count <= limit)
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }
}
