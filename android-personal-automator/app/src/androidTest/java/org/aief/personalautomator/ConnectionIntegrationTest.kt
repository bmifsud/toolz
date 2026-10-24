package org.aief.personalautomator

import android.content.Context
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.CheckBox
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import org.junit.runner.RunWith
import org.json.JSONObject
import java.net.ServerSocket
import java.net.InetAddress
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class ConnectionIntegrationTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private val address = "http://localhost:20128/v1"
    private val fakeToken = "synthetic-test-token-DO-NOT-USE"
    @Before fun clean() {
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        ConnectionVault(context).apply { forget(true); forget(false) }
    }
    @After fun cleanup() {
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        clean()
    }

    @Test fun encryptedPersistenceReuseReplacementAndForget() {
        val first = ConnectionVault(context)
        first.save(true, address, "", "Open the demo PR", fakeToken)
        val restarted = ConnectionVault(context)
        val settings = restarted.settings(true)!!
        assertEquals("auto", settings.model)
        assertTrue(settings.hasToken)
        assertFalse(settings.toString().contains(fakeToken))
        val prefs = context.getSharedPreferences("connection_vault", Context.MODE_PRIVATE)
        val stored = prefs.getString("local", "")!!
        assertFalse(stored.contains(fakeToken))
        assertFalse(stored.contains("Open the demo PR"))
        restarted.save(true, address, "auto", "Saved task", "")
        assertTrue(restarted.useToken(true, address) { it == fakeToken })
        restarted.save(true, address, "auto", "Saved task", "synthetic-replacement")
        assertTrue(ConnectionVault(context).useToken(true, address) { it == "synthetic-replacement" })
        restarted.forget(true)
        assertNull(ConnectionVault(context).settings(true))
    }

    @Test fun bridgeDestinationChangeCannotReuseToken() {
        val vault = ConnectionVault(context)
        val bridgeToken = "x".repeat(48)
        vault.save(false, "https://one.example/proposal", "auto", "task", bridgeToken)
        vault.save(false, "https://two.example/proposal", "auto", "task", "")
        assertFalse(vault.settings(false)!!.hasToken)
        assertFalse(vault.selectedLocal())
        try { vault.useToken(false, "https://two.example/proposal") { true }; fail("Reused destination-bound token") }
        catch (_: IllegalStateException) { }
        assertNull(vault.settings(true))
    }

    @Test fun tamperedCiphertextFailsClosed() {
        val vault = ConnectionVault(context)
        vault.save(true, address, "auto", "task", fakeToken)
        val prefs = context.getSharedPreferences("connection_vault", Context.MODE_PRIVATE)
        prefs.edit().putString("local", "tampered:invalid").commit()
        try { vault.settings(true); fail("Accepted tampered credentials") } catch (_: Exception) { }
        vault.forget(true)
        assertNull(vault.settings(true))
    }

    @Test fun savedTokenAuthenticatesRealLoopbackRequestWithAutoModel() {
        val receivedAuth = AtomicBoolean(false)
        val receivedAuto = AtomicBoolean(false)
        ServerSocket(20128, 1, InetAddress.getByName("127.0.0.1")).use { server ->
            server.soTimeout = 10000
            val worker = Thread {
                server.accept().use { socket ->
                    socket.soTimeout = 10000
                    val input = socket.getInputStream().bufferedReader()
                    var length = 0
                    var line = input.readLine()
                    assertTrue(line.startsWith("POST /v1/chat/completions "))
                    while (true) {
                        line = input.readLine() ?: break
                        if (line.isEmpty()) break
                        if (line.startsWith("Authorization:", true))
                            receivedAuth.set(line.substringAfter(":").trim() == "Bearer $fakeToken")
                        if (line.startsWith("Content-Length:", true)) length = line.substringAfter(":").trim().toInt()
                    }
                    val chars = CharArray(length)
                    var read = 0
                    while (read < length) { val n = input.read(chars, read, length - read); if (n < 0) break; read += n }
                    receivedAuto.set(JSONObject(String(chars, 0, read)).getString("model") == "auto")
                    val proposal = "{\"action\":\"NONE\",\"explanation\":\"Test connection works\"}"
                    val body = JSONObject().put("choices", org.json.JSONArray().put(JSONObject()
                        .put("finish_reason", "stop").put("message", JSONObject().put("content", proposal)
                        .put("tool_calls", JSONObject.NULL)))).toString().toByteArray()
                    socket.getOutputStream().apply {
                        write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ${body.size}\r\nConnection: close\r\n\r\n".toByteArray())
                        write(body); flush()
                    }
                }
            }.apply { isDaemon = true; start() }
            ConnectionVault(context).save(true, address, "", "test", fakeToken)
            val response = ConnectionVault(context).useToken(true, address) {
                ProposalClient().request(address, it, "Open the demo PR", true, "")
            }
            worker.join(10000)
            assertFalse(worker.isAlive)
            assertTrue(receivedAuth.get())
            assertTrue(receivedAuto.get())
            assertEquals("NONE", response.first)
        }
    }

    @Test fun httpErrorIsUsefulAndContainsNoProviderBodyOrToken() {
        ServerSocket(20128, 1, InetAddress.getByName("127.0.0.1")).use { server ->
            server.soTimeout = 10000
            val worker = Thread {
                server.accept().use { socket ->
                    socket.soTimeout = 10000
                    val input = socket.getInputStream().bufferedReader()
                    input.readLine()
                    var length = 0
                    while (true) {
                        val line = input.readLine() ?: break
                        if (line.isEmpty()) break
                        if (line.startsWith("Content-Length:", true)) length = line.substringAfter(":").trim().toInt()
                    }
                    repeat(length) { input.read() }
                    val body = fakeToken.toByteArray()
                    socket.getOutputStream().apply {
                        write("HTTP/1.1 401 Unauthorized\r\nContent-Length: ${body.size}\r\nConnection: close\r\n\r\n".toByteArray())
                        write(body); flush()
                    }
                }
            }.apply { isDaemon = true; start() }
            val error = runCatching { ProposalClient().request(address, fakeToken, "test", true, "auto") }.exceptionOrNull()!!
            val message = requestFailureMessage(error)
            assertTrue(message.contains("401"))
            assertFalse(message.contains(fakeToken))
            worker.join(10000)
        }
    }

    private fun descendants(view: View): List<View> = listOf(view) +
        if (view is ViewGroup) (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()

    @Test fun activityRecreationRestoresSettingsButNeverTokenOrConsent() {
        ConnectionVault(context).save(true, address, "auto", "Saved task text", fakeToken)
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            fun assertRestored() {
                var restored = false
                for (attempt in 0..100) {
                    scenario.onActivity { activity ->
                        val views = descendants(activity.window.decorView)
                        val fields = views.filterIsInstance<EditText>()
                        restored = fields.size == 4 && fields[2].text.toString() == "Saved task text" && fields[2].isEnabled
                        if (restored) {
                            assertEquals("", fields[1].text.toString())
                            assertEquals("auto", fields[3].text.toString())
                            val consent = views.filterIsInstance<CheckBox>().first()
                            assertFalse(consent.isChecked)
                        }
                    }
                    if (restored) break
                    Thread.sleep(50)
                }
                assertTrue(restored)
            }
            assertRestored()
            scenario.recreate()
            assertRestored()
        }
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
    }
}
