package com.u4ar.lingolive

import android.Manifest
import android.text.Spanned
import android.text.style.ClickableSpan
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.lifecycle.Lifecycle
import okhttp3.*
import okhttp3.mockwebserver.*
import org.json.JSONObject
import org.json.JSONArray
import org.junit.*
import org.junit.Assert.*
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.CopyOnWriteArrayList
import java.io.IOException
import java.net.Proxy

@RunWith(AndroidJUnit4::class)
class AppTest {
    private val instrumentation get()=InstrumentationRegistry.getInstrumentation()
    private val context get()=instrumentation.targetContext
    private val app get()=context.applicationContext as LingoApp
    private lateinit var original:LearningController
    private val profile=Profile(Language("en-US","English"),Language("ja-JP","Japanese"))
    private val key="test-only-device-key-not-real"
    private fun example()=context.assets.open("example.json").bufferedReader().use { JSONObject(it.readText()) }
    private fun lesson():Lesson { val e=example();return Lesson.parse(e.getJSONObject("lesson"),e.getString("text")) }
    private fun descendants(v:View):List<View> = listOf(v)+if(v is ViewGroup)(0 until v.childCount).flatMap { descendants(v.getChildAt(it)) } else emptyList()
    private fun views(a:MainActivity)=descendants(a.findViewById(android.R.id.content))
    private fun await(condition:()->Boolean) { val end=System.currentTimeMillis()+45000;while(System.currentTimeMillis()<end){if(condition())return;Thread.sleep(100)};fail("Expected app state was not reached") }
    private fun awaitUi(s:ActivityScenario<MainActivity>,condition:(MainActivity)->Boolean) { await { var done=false;s.onActivity { done=condition(it) };done } }
    @Before fun prepare() {
        original=app.controller;original.stop();original.memory.clear();original.settings.clearCredentials();original.settings.saveProfile(profile);original.settings.setPronunciation(false)
    }
    @After fun finish() { app.controller.stop();app.useControllerForTests(original);original.settings.clearCredentials() }

    @Test fun exampleWorksWithoutAKeyHasTappableWordsAndDoesNotBecomeFakeLearningHistory() {
        ActivityScenario.launch(MainActivity::class.java).use { s ->
            s.onActivity { a->views(a).filterIsInstance<Button>().single { it.text=="Try an example" }.performClick() }
            awaitUi(s) { a->views(a).filterIsInstance<TextView>().any { it.text.toString().contains("not a recording") } }
            s.onActivity { a->
                assertTrue(views(a).filterIsInstance<TextView>().any { it.text.toString()=="Would you like some coffee?" })
                views(a).filterIsInstance<Button>().single { it.text=="Pronunciation" }.performClick()
                val spoken=views(a).filterIsInstance<TextView>().single { it.text.toString()=="kōhī wa ikaga desu ka？" }
                val spans=spoken.text as Spanned;assertEquals(5,spans.getSpans(0,spans.length,ClickableSpan::class.java).size)
                spans.getSpans(0,spans.length,ClickableSpan::class.java).first().onClick(spoken)
            }
            val dialog=node("coffee");assertNotNull(dialog);node("Got it").performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK)
            assertTrue(original.memory.recent().isEmpty());assertTrue(original.memory.words().isEmpty())
            screenshot("example.png")
        }
    }
    @Test fun credentialsAreEncryptedAndLanguagesPersistWhileNoKeyIsDisplayed() {
        val settings=original.settings;settings.saveConnection(Connection(false,key,"",""));assertEquals(key,settings.connection().apiKey)
        val xml=File(context.applicationInfo.dataDir,"shared_prefs/settings.xml").readText()
        assertFalse(xml.contains(key));assertTrue(xml.contains("vault"))
        settings.saveProfile(Profile(Language("hi-IN","Hindi"),Language("ja-JP","Japanese")))
        ActivityScenario.launch(MainActivity::class.java).use { s ->
            s.onActivity { a->assertTrue(views(a).filterIsInstance<Button>().any { it.contentDescription=="Known language: Hindi" });views(a).filterIsInstance<Button>().single { it.contentDescription=="Languages and connection settings" }.performClick() }
            s.recreate()
            awaitUi(s) { a->views(a).filterIsInstance<TextView>().any { it.text.toString()=="Make it yours." } }
            s.onActivity { a->assertFalse(views(a).filterIsInstance<TextView>().any { it.text.contains(key) });assertTrue(views(a).filterIsInstance<TextView>().any { it.text.toString()=="I know: Hindi" }) }
        }
        settings.clearCredentials();assertFalse(settings.connection().configured)
    }
    @Test fun memoryRetainsExactLessonsRepliesAndWordsWithoutDuplicatingOnRetryAndDeletesLinks() {
        val memory=original.memory;val lesson=lesson();val id=memory.add(lesson.source,profile)
        memory.save(id,lesson);val first=memory.words();assertTrue(first.isNotEmpty());assertTrue(first.any { it.text=="ミルク" })
        memory.save(id,lesson);assertEquals(first,memory.words())
        Memory(context).use { reopened->assertEquals(lesson.json,reopened.find(id)!!.lesson!!.json);assertEquals(3,reopened.find(id)!!.lesson!!.replies.size) }
        val second=memory.add("Hello, this stays as a transcript.",profile);memory.state(second,"Transcript","en")
        assertEquals(2,memory.recent().size);memory.delete(id);assertTrue(memory.words().isEmpty());assertEquals(second,memory.recent().single().id)
    }
    @Test fun bundledGoogleLanguageIdentifierRecognizesJapaneseAndDoesNotTeachEnglishAsJapanese() {
        val detector=GoogleDetector();val latch=CountDownLatch(2);var japanese:List<Pair<String,Float>> = emptyList();var english:List<Pair<String,Float>> = emptyList()
        detector.detect("コーヒーはいかがですか？今日はいい天気ですね。") { japanese=it;latch.countDown() }
        detector.detect("Would you like a cup of coffee? We could sit by the window and talk.") { english=it;latch.countDown() }
        assertTrue(latch.await(40,TimeUnit.SECONDS));assertTrue(LanguageCodes.shouldTeach(japanese,"ja-JP"));assertFalse(LanguageCodes.shouldTeach(english,"ja-JP"))
    }
    @Test fun websocketThroughLanguageDetectionAndFlashToVisibleLessonAndLocalMemory() {
        val frames=AtomicInteger();val requests=AtomicInteger();val data=example();val exampleText=data.getString("text");val fixture=data.getJSONObject("lesson")
        val mic=object:Microphone { var stopped=false;override fun start(frame:(ByteArray)->Unit,level:(Float)->Unit,failure:()->Unit) { frame(ByteArray(3200));level(.2f) };override fun stop(){stopped=true} }
        MockWebServer().use { server->
            server.dispatcher=object:okhttp3.mockwebserver.Dispatcher() {
                override fun dispatch(request:RecordedRequest):MockResponse {
                    if(request.path=="/listen")return MockResponse().withWebSocketUpgrade(object:WebSocketListener() {
                        override fun onClosing(socket:WebSocket,code:Int,reason:String) { socket.close(1000,"Closing") }
                        override fun onMessage(socket:WebSocket,text:String) {
                            val body=JSONObject(text)
                            if(body.has("setup")) { assertEquals("models/gemini-3.5-transcribe-live",body.getJSONObject("setup").getString("model"));socket.send("{\"setupComplete\":{}}") }
                            else if(body.getJSONObject("realtimeInput").has("audio")) {
                                frames.incrementAndGet();assertEquals("audio/pcm;rate=16000",body.getJSONObject("realtimeInput").getJSONObject("audio").getString("mimeType"))
                                socket.send(JSONObject().put("serverContent",JSONObject().put("interimInputTranscription",JSONObject().put("text","コーヒー"))).toString())
                                socket.send(JSONObject().put("serverContent",JSONObject().put("inputTranscription",JSONObject().put("text",exampleText))).toString())
                            } else if(body.getJSONObject("realtimeInput").optBoolean("audioStreamEnd")) {
                                socket.send(JSONObject().put("serverContent",JSONObject().put("inputTranscription",JSONObject().put("text","I already speak English and understand this sentence well."))).toString())
                            }
                        }
                    })
                    if(request.path=="/v1beta/models/gemini-3.6-flash:generateContent") {
                        requests.incrementAndGet();assertEquals(key,request.getHeader("x-goog-api-key"));val body=JSONObject(request.body.readUtf8())
                        assertTrue(body.getJSONObject("generationConfig").has("responseJsonSchema"))
                        val input=JSONObject(body.getJSONArray("contents").getJSONObject(0).getJSONArray("parts").getJSONObject(0).getString("text"));assertEquals(exampleText,input.getString("text"))
                        return response(fixture)
                    }
                    return MockResponse().setResponseCode(404)
                }
            };server.start()
            // In-process fixture traffic must not use the cloud emulator's egress proxy.
            val localClient=OkHttpClient.Builder().proxy(Proxy.NO_PROXY).build()
            val settings=original.settings;settings.saveConnection(Connection(false,key,"",""))
            val c=LearningController(settings,original.memory,GoogleGateway(context,client=localClient,testOrigin=server.url("/").toString().trimEnd('/')),GoogleDetector(),{mic},
                { connection,microphone,event,level,status->LiveTranscriber(connection,microphone,event,level,status,client=localClient,testUrl=server.url("/listen").toString()) })
            app.useControllerForTests(c)
            instrumentation.uiAutomation.grantRuntimePermission(context.packageName,Manifest.permission.RECORD_AUDIO)
            ActivityScenario.launch(MainActivity::class.java).use { s ->
                s.onActivity { a->views(a).filterIsInstance<Button>().single { it.contentDescription=="Start or stop live transcription" }.performClick() }
                try { awaitUi(s) { a->views(a).filterIsInstance<TextView>().any { it.text.toString()=="Would you like some coffee?" } } }
                catch(error:AssertionError) { fail("Pipeline frames=${frames.get()} lesson requests=${requests.get()} states=${c.memory.recent().map { it.state + ':' + it.error }}; status=${c.status}") }
                assertEquals(1,frames.get());assertEquals(1,requests.get());assertEquals(1,c.memory.recent().size);assertEquals("Learned",c.memory.recent().single().state)
                assertEquals(exampleText,c.memory.recent().single().text);assertTrue(c.memory.words().any { it.text=="コーヒー" })
                s.onActivity { a->
                    val voice=views(a).filterIsInstance<Button>().single { it.contentDescription=="Start or stop live transcription" };assertTrue(voice.isShown);assertFalse(voice.parent is android.widget.ScrollView)
                    views(a).filterIsInstance<Button>().single { it.text=="Pronunciation" }.performClick()
                    val reply=views(a).filterIsInstance<TextView>().first { it.text.toString()=="hai、onegaishimasu。" }
                    val spans=reply.text as Spanned;assertEquals(2,spans.getSpans(0,spans.length,ClickableSpan::class.java).size)
                }
                screenshot("live-lesson.png")
                s.moveToState(Lifecycle.State.CREATED);assertTrue(mic.stopped);assertFalse(c.listening)
                await { c.memory.recent().size==2 && c.memory.recent().first().state=="Transcript" }
                assertEquals(1,requests.get())
            }
        }
    }
    @Test fun failedLessonLeavesTranscriptAndCanBeRetriedWithoutLosingLocalMemory() {
        val networkErrors=CopyOnWriteArrayList<String>()
        val client=OkHttpClient.Builder().proxy(Proxy.NO_PROXY).eventListener(object:EventListener() {
            override fun callFailed(call:Call,ioe:IOException) { networkErrors.add(call.request().url.host+": "+ioe.toString()) }
        }).build()
        MockWebServer().use { server->
            server.enqueue(MockResponse().setResponseCode(429).addHeader("Retry-After","15"));server.enqueue(response(example().getJSONObject("lesson")));server.start()
            original.settings.saveConnection(Connection(false,key,"",""))
            val controller=LearningController(original.settings,original.memory,GoogleGateway(context,client=client,testOrigin=server.url("/").toString().trimEnd('/')),object:Detector { override fun detect(text:String,done:(List<Pair<String,Float>>)->Unit){done(listOf("ja" to 1f))} })
            val id=controller.accept(example().getString("text"));await { controller.memory.find(id)?.state=="Retry lesson" && controller.queued()==0 }
            assertTrue(controller.memory.find(id)!!.error+" / "+networkErrors,controller.memory.find(id)!!.error.contains("rate limit"));assertEquals(example().getString("text"),controller.memory.find(id)!!.text)
            controller.learn(id);await { controller.memory.find(id)?.state=="Learned" };assertEquals(1,controller.memory.recent().size);assertTrue(controller.memory.words().isNotEmpty())
            controller.stop()
        }
    }
    @Test fun delayedLanguageIdentificationDoesNotRepeatAnExplicitLessonOrOverwriteItsSavedState() {
        var detect:((List<Pair<String,Float>>)->Unit)?=null;val calls=AtomicInteger()
        val detector=object:Detector { override fun detect(text:String,done:(List<Pair<String,Float>>)->Unit){detect=done} }
        val teacher=object:Teacher { override fun teach(text:String,profile:Profile,connection:Connection):Lesson { calls.incrementAndGet();return lesson() } }
        original.settings.saveConnection(Connection(false,key,"",""))
        val c=LearningController(original.settings,original.memory,teacher,detector)
        val id=c.accept(example().getString("text"),autoTeach=false);c.learn(id)
        await { c.memory.find(id)?.state=="Learned" && c.queued()==0 };detect!!(listOf("ja" to 1f))
        assertEquals("Learned",c.memory.find(id)!!.state);assertEquals(1,calls.get());assertEquals(0,c.queued())
    }
    private fun response(value:JSONObject)=MockResponse().addHeader("Content-Type","application/json").setBody(JSONObject().put("candidates",JSONArray().put(JSONObject().put("finishReason","STOP").put("content",JSONObject().put("parts",JSONArray().put(JSONObject().put("text",value.toString())))))).toString())
    private fun activeRoot():android.view.accessibility.AccessibilityNodeInfo? {
        val root=instrumentation.uiAutomation.rootInActiveWindow ?: return null
        if(root.packageName?.toString()=="android" && listOf("Process system","System UI","Network Stack","NetworkStack","Tethering","com.android.networkstack").any { root.findAccessibilityNodeInfosByText(it).isNotEmpty() }) {
            root.findAccessibilityNodeInfosByText("Wait").firstOrNull()?.performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK);Thread.sleep(500);return null
        }
        return root
    }
    private fun node(text:String):android.view.accessibility.AccessibilityNodeInfo { var result:android.view.accessibility.AccessibilityNodeInfo?=null;await { result=activeRoot()?.findAccessibilityNodeInfosByText(text)?.firstOrNull();result!=null };return result!! }
    private fun screenshot(name:String) {
        instrumentation.waitForIdleSync();await { activeRoot()?.packageName?.toString()==context.packageName }
        val bitmap=instrumentation.uiAutomation.takeScreenshot();File(context.cacheDir,name).outputStream().use { bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it) };bitmap.recycle()
    }
}
