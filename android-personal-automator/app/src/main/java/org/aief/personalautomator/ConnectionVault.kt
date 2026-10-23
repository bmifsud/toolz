package org.aief.personalautomator

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Tokens are never returned as settings or placed back into editable UI fields. */
class ConnectionVault(context: Context) {
    private val prefs = context.getSharedPreferences("connection_vault", Context.MODE_PRIVATE)
    data class Settings(val endpoint: String, val model: String, val task: String, val hasToken: Boolean)

    @Synchronized fun selectedLocal(): Boolean = prefs.getBoolean("selected_local", true)
    private fun slot(local: Boolean) = if (local) "local" else "bridge"
    private fun key(create: Boolean): SecretKey = synchronized(KEY_LOCK) {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(ALIAS, null) as? SecretKey)?.let { return@synchronized it }
        check(create) { "Saved credentials unavailable; forget and re-enter them" }
        KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build())
            generateKey()
        }
    }
    private fun read(local: Boolean): JSONObject? {
        val saved = prefs.getString(slot(local), null) ?: return null
        val parts = saved.split(":")
        require(parts.size == 2)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(false), GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)))
        cipher.updateAAD(slot(local).toByteArray(Charsets.UTF_8))
        return JSONObject(String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), Charsets.UTF_8))
    }
    @Synchronized fun settings(local: Boolean): Settings? = read(local)?.let {
        Settings(it.getString("endpoint"), it.getString("model"), it.getString("task"), it.getString("token").isNotEmpty())
    }
    @Synchronized fun save(local: Boolean, endpoint: String, model: String, task: String, replacement: String) {
        val selectedModel = model.trim().ifBlank { "auto" }
        ProviderEndpoint.target(endpoint, local, selectedModel)
        require(task.length <= 2000 && replacement.length <= 512)
        require(replacement.all { it.code in 33..126 })
        val previous = read(local)
        // A saved bridge token must never follow an edited destination.
        val token = replacement.ifEmpty {
            if (previous?.optString("endpoint") == endpoint) previous?.optString("token").orEmpty() else ""
        }
        if (token.isNotEmpty()) require(token.length in (if (local) 1..512 else 32..512))
        val data = JSONObject().put("endpoint", endpoint).put("model", selectedModel)
            .put("task", task).put("token", token).toString().toByteArray(Charsets.UTF_8)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key(true))
        cipher.updateAAD(slot(local).toByteArray(Charsets.UTF_8))
        val encrypted = cipher.doFinal(data)
        val saved = Base64.encodeToString(cipher.iv, Base64.NO_WRAP) + ":" + Base64.encodeToString(encrypted, Base64.NO_WRAP)
        check(prefs.edit().putString(slot(local), saved).putBoolean("selected_local", local).commit())
    }
    /** Plaintext is supplied only to the in-process authenticated request, never to UI/logs. */
    @Synchronized fun <T> useToken(local: Boolean, endpoint: String, action: (String) -> T): T {
        val data = read(local) ?: error("No saved connection")
        check(data.getString("endpoint") == endpoint)
        val token = data.getString("token")
        check(token.isNotEmpty()) { "No saved token" }
        return action(token)
    }
    @Synchronized fun forget(local: Boolean) {
        check(prefs.edit().remove(slot(local)).commit())
    }
    companion object {
        private const val ALIAS = "personal_automator_connections_v1"
        private val KEY_LOCK = Any()
    }
}
