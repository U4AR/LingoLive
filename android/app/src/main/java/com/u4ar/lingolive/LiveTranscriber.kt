package com.u4ar.lingolive

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Handler
import android.os.Looper
import android.util.Base64
import okhttp3.*
import okhttp3.HttpUrl.Companion.toHttpUrl
import okio.ByteString
import org.json.JSONObject
import java.util.ArrayDeque
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.sqrt

interface Microphone {
    fun start(frame: (ByteArray) -> Unit, level: (Float) -> Unit, failure: () -> Unit)
    fun stop()
}
class PcmMicrophone: Microphone {
    private val running = AtomicBoolean(false)
    @Volatile private var recorder: AudioRecord? = null
    @Suppress("MissingPermission")
    override fun start(frame: (ByteArray) -> Unit, level: (Float) -> Unit, failure: () -> Unit) {
        if (!running.compareAndSet(false, true)) return
        Thread({
            var audio: AudioRecord? = null
            try {
                val size = maxOf(6400, AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT))
                audio = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,size)
                check(audio.state == AudioRecord.STATE_INITIALIZED)
                recorder = audio; if (!running.get()) return@Thread
                audio.startRecording(); val buffer = ByteArray(3200)
                while (running.get()) {
                    val n = audio.read(buffer,0,buffer.size,AudioRecord.READ_BLOCKING)
                    if (n <= 0) { if (running.get()) failure(); break }
                    val data = buffer.copyOf(n - n % 2)
                    var energy = 0.0
                    for (i in data.indices step 2) { val sample = ((data[i].toInt() and 255) or (data[i+1].toInt() shl 8)).toShort().toDouble()/32768; energy += sample*sample }
                    level(sqrt(energy / (data.size/2)).toFloat()); frame(data)
                }
            } catch (_: Exception) { if (running.get()) failure() }
            finally { running.set(false); recorder = null; try { audio?.stop() } catch (_: Exception) {}; audio?.release() }
        },"LingoLive microphone").start()
    }
    override fun stop() { running.set(false); try { recorder?.stop() } catch (_: Exception) {} }
}

/** Google's dedicated Transcribe Live protocol; PCM never becomes a prompt to Flash. */
class LiveTranscriber(private val connection: Connection, private val microphone: Microphone,
    private val event: (LiveEvent) -> Unit, private val level: (Float) -> Unit, private val status: (String) -> Unit,
    private val client: OkHttpClient = OkHttpClient.Builder().connectTimeout(15,TimeUnit.SECONDS).readTimeout(0,TimeUnit.MILLISECONDS).pingInterval(20,TimeUnit.SECONDS).build(),
    private val testUrl: String? = null) {
    private val handler = Handler(Looper.getMainLooper())
    private var wanted = false
    private var ready = false
    private var microphoneStarted = false
    private var generation = 0
    private var retry = 0
    private var current: WebSocket? = null
    private val sockets = mutableSetOf<WebSocket>()
    private val pending = ArrayDeque<ByteArray>()
    private var stoppedAt = 0L
    @Synchronized fun start() {
        check(!wanted); connection.validate(); check(connection.configured)
        wanted = true; open()
    }
    private fun request(): Request {
        val builder = if (testUrl != null) {
            check(BuildConfig.DEBUG); Request.Builder().url(testUrl)
        } else if (connection.hosted) Request.Builder().url(connection.serverUrl.replaceFirst("https://","wss://").trimEnd('/')+"/v1/listen")
        else Request.Builder().url("https://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent".toHttpUrl().newBuilder().addQueryParameter("key",connection.apiKey).build())
        if (connection.hosted) builder.header("Authorization","Bearer ${connection.accessToken}")
        return builder.build()
    }
    @Synchronized private fun open() {
        if (!wanted) return
        ready = false; generation++; val own = generation
        status(if (microphoneStarted) "Reconnecting · briefly buffering speech…" else "Connecting to Google Transcribe…")
        val socket = client.newWebSocket(request(), object: WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                synchronized(this@LiveTranscriber) { if (!wanted || own != generation) { webSocket.close(1000,"Stopped"); return }; sockets.add(webSocket) }
                webSocket.send(LiveProtocol.setup(connection.transcribeModel))
            }
            override fun onMessage(webSocket: WebSocket, text: String) = receive(webSocket,text,own)
            override fun onMessage(webSocket: WebSocket, bytes: ByteString) = receive(webSocket,bytes.utf8(),own)
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                synchronized(this@LiveTranscriber) {
                    sockets.remove(webSocket)
                    if (!wanted || own != generation) return
                    if (response?.code in listOf(400,401,403,404)) fail("Google Transcribe access was denied or the model is unavailable. Check Settings.")
                    else reconnect()
                }
            }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                synchronized(this@LiveTranscriber) { sockets.remove(webSocket); if (wanted && own == generation) reconnect() }
            }
            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) { webSocket.close(1000,"Closing") }
        })
        current = socket
        handler.postDelayed({ synchronized(this) { if (wanted && own == generation && !ready) fail("Google Transcribe did not connect. Check your key, model access and network.") } },15000)
    }
    @Synchronized private fun receive(socket: WebSocket, text: String, own: Int) {
        if ((!wanted && System.currentTimeMillis()-stoppedAt>4500) || text.length>500000) return
        val events = try { LiveProtocol.events(JSONObject(text)) } catch (_: Exception) { fail("Google returned an unreadable transcription response. Tap to retry."); return }
        for (message in events) when(message) {
            LiveEvent.Ready -> if (own == generation && wanted) {
                ready = true; retry = 0
                while (pending.isNotEmpty()) if (!send(pending.removeFirst())) return
                if (!microphoneStarted) {
                    microphoneStarted = true
                    microphone.start({ data -> frame(data) },level,{ synchronized(this) { fail("Microphone unavailable. Check microphone access and tap to try again.") } })
                }
                status("Listening · all languages · lessons saved on this phone"); event(message)
                handler.postDelayed({ synchronized(this) { if (wanted && own == generation) rotate() } },570000)
            }
            is LiveEvent.Final -> event(message)
            is LiveEvent.Interim -> if (wanted && own == generation) event(message)
            LiveEvent.Renew -> if (wanted && own == generation) rotate()
            is LiveEvent.Error -> if(own==generation) fail(message.message)
        }
    }
    @Synchronized private fun frame(data: ByteArray) {
        if (!wanted) return
        if (ready) send(data) else {
            pending.addLast(data)
            if (pending.sumOf { it.size } > 160000) fail("Connection is too slow. Listening paused; the last few words may not have arrived. Tap to reconnect.")
        }
    }
    private fun send(data: ByteArray): Boolean {
        val socket = current ?: return false
        if (socket.queueSize()>128000) { fail("Connection is too slow. Listening paused; check your network and tap to reconnect."); return false }
        val sent = socket.send(JSONObject().put("realtimeInput",JSONObject().put("audio",JSONObject().put("data",Base64.encodeToString(data,Base64.NO_WRAP)).put("mimeType","audio/pcm;rate=16000"))).toString())
        if (!sent) { pending.addLast(data); reconnect() }
        return sent
    }
    private fun rotate() {
        val previous = current; ready = false
        previous?.send("{\"realtimeInput\":{\"audioStreamEnd\":true}}")
        open()
        handler.postDelayed({ previous?.close(1000,"Session renewed") },3500)
    }
    private fun reconnect() {
        ready = false; retry++
        if (retry>3) { fail("Google Transcribe disconnected. Your completed transcripts are saved; tap to reconnect."); return }
        val previous = current; generation++; val own = generation
        status("Connection interrupted · reconnecting…")
        handler.postDelayed({ synchronized(this) { if (wanted && own == generation) { previous?.cancel(); open() } } },(1L shl (retry-1))*1000)
    }
    private fun fail(message: String) { stop(false); event(LiveEvent.Error(message)) }
    @Synchronized fun stop(flush: Boolean = true) {
        if (!wanted) return
        wanted = false; ready = false; stoppedAt = System.currentTimeMillis(); microphone.stop(); microphoneStarted=false; pending.clear()
        val closing = sockets.toList(); val connecting = current
        if (flush) connecting?.send("{\"realtimeInput\":{\"audioStreamEnd\":true}}")
        handler.postDelayed({ synchronized(this) { closing.forEach { it.close(1000,"Stopped") }; connecting?.close(1000,"Stopped"); sockets.clear() } },if(flush)4500 else 0)
    }
}
