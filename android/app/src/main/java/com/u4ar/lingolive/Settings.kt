package com.u4ar.lingolive

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class Connection(val hosted: Boolean, val apiKey: String, val serverUrl: String, val accessToken: String,
    val flashModel: String = "gemini-3.6-flash", val transcribeModel: String = "gemini-3.5-transcribe-live") {
    val configured get() = if (hosted) serverUrl.isNotBlank() && accessToken.isNotBlank() else apiKey.isNotBlank()
    fun validate() {
        require(flashModel.matches(Regex("gemini-[a-zA-Z0-9.-]{1,80}")) && transcribeModel.matches(Regex("gemini-[a-zA-Z0-9.-]{1,80}-transcribe-live"))) { "Check the Google model IDs." }
        if (hosted) validateServer(serverUrl)
    }
    companion object {
        fun validateServer(url: String) {
            val uri = try { URI(url.trim()) } catch (_: Exception) { throw IllegalArgumentException("Enter a valid HTTPS backend address.") }
            require(uri.scheme == "https" && !uri.host.isNullOrEmpty() && uri.userInfo == null && uri.query == null && uri.fragment == null && uri.path.orEmpty().trim('/').isEmpty()) {
                "Use an HTTPS backend origin, such as https://your-service.run.app, without a path or credentials."
            }
        }
    }
}
class Settings(private val context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)
    val languages: List<Language> by lazy {
        val values = context.assets.open("languages.json").bufferedReader().use { JSONArray(it.readText()) }
        (0 until values.length()).map { val v = values.getJSONObject(it); Language(v.getString("code"), v.getString("name")) }
    }
    fun language(code: String) = languages.firstOrNull { it.code == code } ?: languages.first { it.code == "en-US" }
    fun profile() = Profile(language(prefs.getString("known", "en-US")!!), language(prefs.getString("learning", "ja-JP")!!))
    fun saveProfile(profile: Profile) { profile.validate(); prefs.edit().putString("known", profile.known.code).putString("learning", profile.learning.code).commit() }
    fun pronunciation() = prefs.getBoolean("pronunciation", false)
    fun setPronunciation(value: Boolean) { prefs.edit().putBoolean("pronunciation", value).apply() }
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("lingolive.settings", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("lingolive.settings", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    private fun secrets(): JSONObject = try {
        val saved = prefs.getString("vault", null) ?: return JSONObject()
        val parts = saved.split(':'); require(parts.size == 2)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP))) }
        JSONObject(String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), Charsets.UTF_8))
    } catch (_: Exception) { JSONObject() }
    fun connection(): Connection {
        val secrets = secrets()
        return Connection(prefs.getBoolean("hosted", false), secrets.optString("google_key"), prefs.getString("server_url", "")!!,
            secrets.optString("access_token"), prefs.getString("flash_model", "gemini-3.6-flash")!!, prefs.getString("transcribe_model", "gemini-3.5-transcribe-live")!!)
    }
    fun saveConnection(value: Connection) {
        value.validate()
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
        val secret = JSONObject().put("google_key", value.apiKey).put("access_token", value.accessToken).toString().toByteArray()
        val encrypted = Base64.encodeToString(cipher.iv, Base64.NO_WRAP) + ":" + Base64.encodeToString(cipher.doFinal(secret), Base64.NO_WRAP)
        prefs.edit().putBoolean("hosted", value.hosted).putString("vault", encrypted).putString("server_url", value.serverUrl.trim().trimEnd('/'))
            .putString("flash_model", value.flashModel).putString("transcribe_model", value.transcribeModel).commit()
    }
    fun clearCredentials() { prefs.edit().remove("vault").commit() }
}
