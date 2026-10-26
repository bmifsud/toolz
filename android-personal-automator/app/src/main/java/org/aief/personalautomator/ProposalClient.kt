package org.aief.personalautomator

import org.json.JSONObject
import java.net.HttpURLConnection

/** Versioned, structured task-planning protocol client supporting general-purpose task categories. */
class ProposalClient {
    @Volatile private var connection: HttpURLConnection? = null
    @Volatile private var cancelled = false
    fun cancel() { cancelled = true; connection?.disconnect() }
    
    fun request(endpoint: String, token: String, task: String, localRoute: Boolean = false, model: String = ""): TaskProposal {
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
            
            val systemPrompt = "You propose actions and answers for a supervised Android personal automator. " +
                "Supported categories and actions: " +
                "1. ANSWER (action: ANSWER) - for general questions without device execution. " +
                "2. READ_ONLY (action: READ_UPTIME) - for obtaining authorized device or environment information. " +
                "3. DEVELOPMENT (action: RUN_TESTS) - for running test suites or development tasks. " +
                "4. DEVICE_ACTION (action: OPEN_DEMO) - for opening the demo link $DEMO_URL. " +
                "5. UNSUPPORTED (action: UNSUPPORTED) - when requested capability is unavailable or unsafe. " +
                "Return ONLY a JSON object with exactly four keys: category (ANSWER, READ_ONLY, DEVELOPMENT, DEVICE_ACTION, or UNSUPPORTED), " +
                "action (ANSWER, READ_UPTIME, RUN_TESTS, OPEN_DEMO, or UNSUPPORTED), explanation (1-2000 characters), and command (optional string). No markdown."

            val body = if (localRoute) JSONObject().put("model", selectedModel).put("stream", false)
                .put("max_tokens", 1200).put("messages", org.json.JSONArray()
                    .put(JSONObject().put("role", "system").put("content", systemPrompt))
                    .put(JSONObject().put("role", "user").put("content", task))).toString()
                else JSONObject().put("task", task).put("version", 2).toString()
                
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            val status = conn.responseCode
            if (status != 200) throw httpFailure(status)
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
                val content = message.getString("content").trim()
                // Strip markdown code blocks if present
                val cleaned = if (content.startsWith("```")) {
                    content.substringAfter("\n").substringBeforeLast("```").trim()
                } else content
                JSONObject(cleaned)
            } else response
            
            val categoryStr = if (json.has("category")) json.getString("category") else {
                if (json.optString("action") == "OPEN_DEMO") "DEVICE_ACTION" else "UNSUPPORTED"
            }
            val rawActionStr = json.optString("action", "NONE")
            val actionStr = when (rawActionStr) {
                "NONE" -> if (categoryStr == "ANSWER") "ANSWER" else "UNSUPPORTED"
                else -> rawActionStr
            }
            val explanation = json.getString("explanation")
            val command = json.optString("command", "")
            
            val category = runCatching { TaskCategory.valueOf(categoryStr) }.getOrDefault(TaskCategory.UNSUPPORTED)
            val action = runCatching { Capability.valueOf(actionStr) }.getOrDefault(Capability.UNSUPPORTED)
            require(explanation.length in 1..2000)
            
            return TaskProposal(category, action, explanation, command)
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

