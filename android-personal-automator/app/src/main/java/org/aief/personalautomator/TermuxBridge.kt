package org.aief.personalautomator

import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.concurrent.TimeUnit

/** Secure local execution bridge with strict capability registration and validation. */
object TermuxBridge {
    fun execute(capability: Capability, command: String = "", timeoutSeconds: Long = 10): Pair<Boolean, String> {
        return when (capability) {
            Capability.OPEN_DEMO -> {
                true to "Demo URL opened: $DEMO_URL"
            }
            Capability.ANSWER -> {
                true to command.ifBlank { "Informational response provided." }
            }
            Capability.READ_UPTIME -> {
                runShellCommand("uptime", timeoutSeconds)
            }
            Capability.RUN_TESTS -> {
                runShellCommand("./gradlew test", timeoutSeconds)
            }
            Capability.UNSUPPORTED -> {
                false to "Unsupported capability requested."
            }
        }
    }

    private fun runShellCommand(cmd: String, timeoutSeconds: Long): Pair<Boolean, String> {
        return try {
            val process = ProcessBuilder("/bin/sh", "-c", cmd)
                .redirectErrorStream(true)
                .start()
            
            val finished = process.waitFor(timeoutSeconds, TimeUnit.SECONDS)
            if (!finished) {
                process.destroyForcibly()
                return Pair(false, "Execution timed out after $timeoutSeconds seconds.")
            }
            
            val output = StringBuilder()
            BufferedReader(InputStreamReader(process.inputStream)).use { reader ->
                var line: String? = reader.readLine()
                while (line != null) {
                    if (output.length < 50000) {
                        output.append(line).append("\n")
                    }
                    line = reader.readLine()
                }
            }
            val exitCode = process.exitValue()
            val resultStr = output.toString().trim()
            Pair(exitCode == 0, if (resultStr.isNotBlank()) resultStr else "Exit code: $exitCode")
        } catch (e: Exception) {
            Pair(false, "Execution failed: ${e.message}")
        }
    }
}

