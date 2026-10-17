package com.u4ar.lingolive

import android.app.Application
import android.os.Handler
import android.os.Looper
import com.google.mlkit.nl.languageid.LanguageIdentification
import com.google.mlkit.nl.languageid.LanguageIdentificationOptions
import java.util.concurrent.CopyOnWriteArraySet
import java.util.concurrent.Executors
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

interface Detector { fun detect(text: String, done: (List<Pair<String,Float>>) -> Unit) }
class GoogleDetector: Detector {
    private val detector = LanguageIdentification.getClient(LanguageIdentificationOptions.Builder().setConfidenceThreshold(.20f).build())
    override fun detect(text: String, done: (List<Pair<String,Float>>) -> Unit) {
        detector.identifyPossibleLanguages(text).addOnSuccessListener { found -> done(found.map { it.languageTag to it.confidence }) }.addOnFailureListener { done(emptyList()) }
    }
}
class LearningController(val settings: Settings, val memory: Memory, private val teacher: Teacher,
    private val detector: Detector = GoogleDetector(), private val microphoneFactory: () -> Microphone = { PcmMicrophone() },
    private val transcriberFactory: ((Connection,Microphone,(LiveEvent)->Unit,(Float)->Unit,(String)->Unit)->LiveTranscriber)? = null) {
    private val ui = Handler(Looper.getMainLooper())
    private val worker = Executors.newSingleThreadExecutor()
    private val listeners = CopyOnWriteArraySet<() -> Unit>()
    private val pending = ConcurrentHashMap.newKeySet<String>()
    private val count = AtomicInteger(0)
    private val updates = AtomicInteger(0)
    val revision get() = updates.get()
    @Volatile var listening = false; private set
    @Volatile var status = "Tap to listen, or try an example."; private set
    @Volatile var interim = ""; private set
    @Volatile var level = 0f; private set
    @Volatile var selected: String? = null; private set
    private var transcriber: LiveTranscriber? = null
    private var lastCall = 0L
    fun observe(listener: () -> Unit) { listeners.add(listener) }
    fun remove(listener: () -> Unit) { listeners.remove(listener) }
    private fun changed(data: Boolean = false) { if(data) updates.incrementAndGet(); ui.post { listeners.forEach { it() } } }
    fun select(id: String?) { selected=id; changed(true) }
    fun start() {
        if (listening) return
        val profile = settings.profile(); val connection=settings.connection(); profile.validate(); connection.validate()
        check(connection.configured) { "Add your Google API key or Cloud Run connection in Settings first." }
        listening=true; status="Connecting to Google Transcribe…"; interim=""; changed()
        val callback: (LiveEvent)->Unit = { event -> when(event) {
            is LiveEvent.Interim -> { interim=event.text; changed() }
            is LiveEvent.Final -> { interim=""; accept(event.text,profile); changed() }
            is LiveEvent.Error -> { listening=false; interim=""; level=0f; status=event.message; changed() }
            else -> {}
        } }
        val updateStatus: (String)->Unit = { status=it; changed() }
        val updateLevel: (Float)->Unit = { level=it }
        transcriber = transcriberFactory?.invoke(connection,microphoneFactory(),callback,updateLevel,updateStatus)
            ?: LiveTranscriber(connection,microphoneFactory(),callback,updateLevel,updateStatus)
        try { transcriber!!.start() } catch (_: Exception) { listening=false; status="Unable to start. Check microphone access and Settings."; changed() }
    }
    fun stop(message: String = "Listening paused. Completed transcripts stay on this phone.") {
        transcriber?.stop(); listening=false; interim=""; level=0f; status=message; changed()
    }
    fun accept(text: String, profile: Profile = settings.profile(), autoTeach: Boolean = true): String {
        val id=memory.add(text,profile); selected=id; changed(true)
        detector.detect(text) { candidates ->
            val current=memory.find(id) ?: return@detect
            val found=candidates.maxByOrNull { it.second }?.first ?: "und"
            if(current.state=="Detecting") memory.state(id,if(found=="und")"Language uncertain" else "Transcript",found)
            if(autoTeach && current.lesson==null && LanguageCodes.shouldTeach(candidates,profile.learning.code)) learn(id)
            changed(true)
        }
        return id
    }
    fun learn(id: String) {
        val utterance=memory.find(id) ?: return
        if (!pending.add(id)) return
        val connection=settings.connection()
        if (!connection.configured) { pending.remove(id); memory.state(id,"Retry lesson",error="Add your key or backend connection in Settings, then retry."); changed(true); return }
        if(count.incrementAndGet()>20) { count.decrementAndGet(); pending.remove(id); memory.state(id,"Retry lesson",error="Your transcript is saved. The lesson queue is full; tap to learn it later."); changed(true); return }
        memory.state(id,"Queued"); changed(true)
        worker.execute {
            try {
                if(memory.find(id)==null) return@execute
                val wait=maxOf(0,lastCall+2500-System.currentTimeMillis()); if(wait>0)Thread.sleep(wait)
                lastCall=System.currentTimeMillis(); memory.state(id,"Learning"); changed(true)
                val lesson=teacher.teach(utterance.text,utterance.profile,connection)
                memory.save(id,lesson)
            } catch(failure:Exception) {
                memory.state(id,"Retry lesson",error=when(failure) {
                    is GoogleFailure -> failure.message
                    is IllegalArgumentException -> failure.message ?: "The lesson was incomplete; tap to retry."
                    else -> "The lesson could not finish. Your transcript is saved; tap to retry."
                })
            } finally { pending.remove(id); count.decrementAndGet(); changed(true) }
        }
    }
    fun queued()=count.get()
}
class LingoApp: Application() {
    lateinit var controller: LearningController; private set
    internal fun useControllerForTests(value: LearningController) { check(BuildConfig.DEBUG); controller.stop(); controller=value }
    override fun onCreate() {
        super.onCreate()
        val settings=Settings(this); val memory=Memory(this); memory.recover()
        controller=LearningController(settings,memory,GoogleGateway(this))
    }
}
