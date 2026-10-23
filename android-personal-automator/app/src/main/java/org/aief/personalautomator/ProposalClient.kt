package org.aief.personalautomator

import org.json.JSONObject
import java.net.HttpURLConnection

/** No redirects, persistence or screen data. One foreground request. */
class ProposalClient {
    @Volatile private var connection: HttpURLConnection? = null
    @Volatile private var cancelled = false
    fun cancel() { cancelled = true; connection?.disconnect() }
    fun request(endpoint: String, token: String, task: String, localRoute: Boolean = false, model: String = ""): Pair<String, String> {
        require(task.isNotBlank() && task.length <= 2000 && token.length in (if (localRoute) 1..512 else 32..512))
        require(token.all { it.code in 33..126 })
        val selectedModel = if (localRoute) model.trim().ifBlank { "auto" } else model
        val target = ProviderEndpoint.target(endpoint, localRoute, selectedModel)
        val conn = target.openConnection() as HttpURLConnection
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
            val body = if (localRoute) JSONObject().put("model", selectedModel).put("stream", false)
                .put("max_tokens", 1200).put("messages", org.json.JSONArray()
                    .put(JSONObject().put("role", "system").put("content",
                        "You propose actions for a supervised Android demo. The ONLY supported action is OPEN_DEMO, " +
                        "opening $DEMO_URL. For other requests use NONE. Never claim to view or control the device. " +
                        "Return only JSON with exactly two string keys: action (OPEN_DEMO or NONE) and " +
                        "explanation (1-2000 characters). No markdown. The user must separately approve."))
                    .put(JSONObject().put("role", "user").put("content", task))).toString()
                else JSONObject().put("task", task).put("version", 1).toString()
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            check(conn.responseCode == 200)
            val bytes = conn.inputStream.use { it.readBytesLimited(if (localRoute) 262144 else 8192) }
            check(!cancelled)
            val response = JSONObject(String(bytes, Charsets.UTF_8))
            val json = if (localRoute) {
                val choices = response.getJSONArray("choices")
                require(choices.length() == 1)
                val choice = choices.getJSONObject(0)
                require(choice.getString("finish_reason") == "stop")
                val message = choice.getJSONObject("message")
                require(message.isNull("tool_calls") && message.isNull("function_call"))
                require(message.isNull("refusal"))
                JSONObject(message.getString("content"))
            } else response
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
