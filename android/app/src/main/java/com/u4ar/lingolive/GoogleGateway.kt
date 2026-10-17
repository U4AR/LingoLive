package com.u4ar.lingolive

import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class GoogleFailure(override val message: String, val retrySeconds: Int = 0): Exception(message)
interface Teacher { fun teach(text: String, profile: Profile, connection: Connection): Lesson }
class GoogleGateway(context: Context, private val client: OkHttpClient = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(90, TimeUnit.SECONDS).build(),
    private val testOrigin: String? = null): Teacher {
    private val schema = context.assets.open("lesson_schema.json").bufferedReader().use { JSONObject(it.readText()) }
    private val instructions = context.assets.open("teach_prompt.txt").bufferedReader().use { it.readText() }
    override fun teach(text: String, profile: Profile, connection: Connection): Lesson {
        require(text.length <= 3000) { "This passage is saved. Edit it into a shorter phrase to make a lesson (3,000 characters maximum)." }
        profile.validate(); connection.validate(); check(connection.configured) { "Add your Google key or hosted connection in Settings." }
        val hosted = connection.hosted
        val endpoint = testOrigin?.also { check(BuildConfig.DEBUG) } ?: if (hosted) connection.serverUrl.trimEnd('/') else "https://generativelanguage.googleapis.com"
        val path = if (hosted) "/v1/teach" else "/v1beta/models/${connection.flashModel}:generateContent"
        val input = profile.json().put("text", text)
        val body = if (hosted) input else JSONObject()
            .put("systemInstruction", JSONObject().put("parts", JSONArray().put(JSONObject().put("text", instructions))))
            .put("contents", JSONArray().put(JSONObject().put("role", "user").put("parts", JSONArray().put(JSONObject().put("text", input.toString())))))
            .put("generationConfig", JSONObject().put("responseMimeType", "application/json").put("responseJsonSchema", schema).put("maxOutputTokens", 16384))
        val request = Request.Builder().url(endpoint + path).header(if (hosted) "Authorization" else "x-goog-api-key", if (hosted) "Bearer ${connection.accessToken}" else connection.apiKey)
            .post(body.toString().toRequestBody("application/json; charset=utf-8".toMediaType())).build()
        val value = try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw GoogleFailure(when (response.code) {
                    401,403 -> "Access denied. Check your saved Google key or backend access token."
                    404 -> "The model or backend endpoint is unavailable. Check the model IDs and connection in Settings."
                    429 -> "Google's rate limit was reached. Your transcript is saved; retry in a moment."
                    else -> "The lesson service could not finish (HTTP ${response.code}). Your transcript is saved."
                }, if (response.code == 429) response.header("Retry-After")?.toIntOrNull()?.coerceIn(5,120) ?: 15 else 0)
                val source = requireNotNull(response.body).source(); source.request(500001)
                require(source.buffer.size <= 500000) { "The lesson response was too large. Try a shorter phrase." }
                val bytes = source.buffer.readByteArray()
                JSONObject(String(bytes, Charsets.UTF_8))
            }
        } catch (failure: GoogleFailure) { throw failure }
        catch (_: java.io.IOException) { throw GoogleFailure("Cannot reach the lesson service. Your transcript is saved; check your connection and retry.") }
        if (hosted) return Lesson.parse(value, text)
        val candidate = value.optJSONArray("candidates")?.optJSONObject(0) ?: throw GoogleFailure("Google did not return a lesson. Try another phrase.")
        if (candidate.optString("finishReason", "STOP") != "STOP") throw GoogleFailure("The lesson was incomplete. Your transcript is saved; try a shorter phrase.")
        val parts = candidate.getJSONObject("content").getJSONArray("parts")
        val json = (0 until parts.length()).map { parts.getJSONObject(it) }.filter { !it.optBoolean("thought") }.joinToString("") { it.optString("text") }
        return Lesson.parse(JSONObject(json), text)
    }
}
