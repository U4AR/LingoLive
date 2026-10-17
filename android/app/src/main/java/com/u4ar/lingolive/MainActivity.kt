package com.u4ar.lingolive

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.text.SpannableString
import android.text.TextPaint
import android.text.method.LinkMovementMethod
import android.text.method.PasswordTransformationMethod
import android.text.style.ClickableSpan
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.*
import org.json.JSONObject
import java.util.Locale

class MainActivity: Activity() {
    private val controller get() = (application as LingoApp).controller
    private val settings get() = controller.settings
    private val memory get() = controller.memory
    private val ink=Color.rgb(30,49,45)
    private val green=Color.rgb(32,90,81)
    private val muted=Color.rgb(102,118,112)
    private val paper=Color.rgb(247,248,244)
    private val tint=Color.rgb(231,239,229)
    private var screen="live"
    private var disposed=false
    private var revision=-1
    private var example=false
    private var detail: String?=null
    private var pronunciation=false
    private var wordList=false
    private var memoryTab="Lessons"
    private var tts: TextToSpeech?=null
    private var ttsReady=false
    private lateinit var content: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var footer: LinearLayout
    private lateinit var languageBar: LinearLayout
    private lateinit var known: Button
    private lateinit var learning: Button
    private lateinit var voice: Button
    private lateinit var caption: TextView
    private lateinit var state: TextView
    private lateinit var back: Button
    private lateinit var saved: Button
    private lateinit var setup: Button
    private val observer: ()->Unit = { if(!disposed) update() }

    internal fun dp(n: Int)=(n*resources.displayMetrics.density).toInt()
    private fun shape(color: Int, radius: Int=22, stroke: Int?=null) = GradientDrawable().apply { setColor(color); cornerRadius=dp(radius).toFloat(); if(stroke!=null)setStroke(dp(1),stroke) }
    private fun text(value:String,size:Float=16f,color:Int=ink,bold:Boolean=false)=TextView(this).apply {
        text=value; textSize=size; setTextColor(color); if(bold)setTypeface(typeface,Typeface.BOLD)
        setLineSpacing(dp(4).toFloat(),1f); setPadding(0,dp(5),0,dp(5)); textDirection=View.TEXT_DIRECTION_FIRST_STRONG
    }
    private fun button(value:String,filled:Boolean=false,action:()->Unit)=Button(this).apply {
        text=value; isAllCaps=false; textSize=14f; minHeight=dp(48); minimumWidth=0
        setTextColor(if(filled)Color.WHITE else green); background=shape(if(filled)green else Color.TRANSPARENT,16)
        setPadding(dp(14),dp(7),dp(14),dp(7)); setOnClickListener { action() }
    }
    private fun column(padding:Int=0)=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(padding),dp(padding),dp(padding),dp(padding)) }
    private fun row()=LinearLayout(this).apply { gravity=Gravity.CENTER_VERTICAL }
    private fun card(color:Int=Color.WHITE)=column(18).apply { background=shape(color) }
    private fun add(view:View,margin:Int=12) { content.addView(view,LinearLayout.LayoutParams(-1,-2).apply { bottomMargin=dp(margin) }) }
    private fun space(n:Int=8)=View(this).apply { layoutParams=LinearLayout.LayoutParams(1,dp(n)) }

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        pronunciation=settings.pronunciation(); screen=savedInstanceState?.getString("screen") ?: "live"
        example=savedInstanceState?.getBoolean("example") ?: false; detail=savedInstanceState?.getString("detail")
        val root=column().apply { setBackgroundColor(paper) }; setContentView(root)
        if(android.os.Build.VERSION.SDK_INT>=30) root.setOnApplyWindowInsetsListener { view,insets ->
            val bars=insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime()); view.setPadding(bars.left,bars.top,bars.right,bars.bottom);insets
        }
        val header=row().apply { setPadding(dp(20),dp(8),dp(12),dp(4)) }
        val brand=column(); brand.addView(text("LingoLive",25f,bold=true)); brand.addView(text("A little more fluent, every day.",11f,muted))
        header.addView(brand,LinearLayout.LayoutParams(0,-2,1f))
        back=button("‹ Back") { navigate("live") }; header.addView(back)
        saved=button("Saved") { navigate("memory") }.apply { contentDescription="Saved lessons and words" };header.addView(saved)
        setup=button("⚙") { navigate("settings") }.apply { textSize=24f;contentDescription="Languages and connection settings" };header.addView(setup)
        root.addView(header)
        languageBar=row().apply { setPadding(dp(20),dp(4),dp(20),dp(10)) }
        known=button("") { chooseLanguage(true) }.apply { background=shape(tint,16) }
        learning=button("") { chooseLanguage(false) }.apply { background=shape(tint,16) }
        languageBar.addView(known,LinearLayout.LayoutParams(0,dp(58),1f)); languageBar.addView(text(" → ",18f,muted))
        languageBar.addView(learning,LinearLayout.LayoutParams(0,dp(58),1f));root.addView(languageBar)
        content=column(20);scroll=ScrollView(this).apply { isFillViewport=true;addView(content);clipToPadding=false }
        root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))
        footer=column().apply { setPadding(dp(20),dp(4),dp(20),dp(14)) }
        caption=text("",18f,muted).apply { maxLines=3; visibility=View.GONE; contentDescription="Live interim transcript" };footer.addView(caption)
        state=text("",12f,muted).apply { maxLines=3;accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE };footer.addView(state)
        voice=button("Start listening",true) { toggleListening() }.apply { textSize=19f;minHeight=dp(66);contentDescription="Start or stop live transcription" };footer.addView(voice,LinearLayout.LayoutParams(-1,dp(66)))
        footer.addView(text("While this screen is open · audio is processed by Google",10f,muted).apply { gravity=Gravity.CENTER })
        root.addView(footer)
        tts=TextToSpeech(this) { result -> ttsReady=result==TextToSpeech.SUCCESS }
        if(android.os.Build.VERSION.SDK_INT>=33) onBackInvokedDispatcher.registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT) { if(screen=="live")finish() else navigate("live") }
        controller.observe(observer); render(); update()
    }
    override fun onSaveInstanceState(out:Bundle) { out.putString("screen",screen);out.putBoolean("example",example);out.putString("detail",detail);super.onSaveInstanceState(out) }
    @Deprecated("For Android versions before predictive back") override fun onBackPressed() { if(screen=="live")super.onBackPressed() else navigate("live") }
    override fun onStop() { controller.stop();tts?.stop();super.onStop() }
    override fun onDestroy() { disposed=true;controller.remove(observer);tts?.shutdown();super.onDestroy() }
    private fun navigate(to:String) { controller.stop();screen=to;example=false;wordList=false;render();scroll.scrollTo(0,0) }
    private fun update() {
        if(!::voice.isInitialized)return
        voice.text=if(controller.listening)"■  Stop listening" else "Start listening"
        voice.background=shape(if(controller.listening)Color.rgb(144,65,53) else green,20)
        state.text=controller.status+(if(controller.queued()>0)" · ${controller.queued()} lesson(s) queued" else "")
        caption.visibility=if(controller.interim.isNotBlank() && screen=="live")View.VISIBLE else View.GONE
        caption.text=controller.interim
        if(screen=="live" && revision!=controller.revision) { revision=controller.revision;example=false;val y=scroll.scrollY;renderBody();scroll.post { scroll.scrollTo(0,y) } }
    }
    private fun render() {
        back.visibility=if(screen=="live")View.GONE else View.VISIBLE
        saved.visibility=if(screen=="live")View.VISIBLE else View.GONE
        setup.visibility=if(screen=="live")View.VISIBLE else View.GONE
        languageBar.visibility=if(screen=="live")View.VISIBLE else View.GONE
        footer.visibility=if(screen=="live")View.VISIBLE else View.GONE
        val profile=settings.profile(); known.text="I know\n${profile.known.name}";learning.text="I'm learning\n${profile.learning.name}"
        known.contentDescription="Known language: ${profile.known.name}";learning.contentDescription="Learning language: ${profile.learning.name}"
        revision=controller.revision;renderBody()
    }
    private fun renderBody() {
        content.removeAllViews()
        when(screen) {
            "settings" -> renderSettings()
            "memory" -> renderMemory()
            "detail" -> memory.find(detail ?: "")?.let { renderUtterance(it);add(button("Delete this entry") { delete(it.id) }) } ?: add(text("This entry was deleted."))
            else -> renderLive()
        }
    }
    private fun toggleListening() {
        if(controller.listening) { controller.stop();return }
        if(!settings.connection().configured) { navigate("settings");Toast.makeText(this,"Add your Google key or hosted connection first.",Toast.LENGTH_LONG).show();return }
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED) { requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO),10);return }
        startListening()
    }
    private fun startListening() {
        example=false;try { controller.start() } catch(error:Exception) { Toast.makeText(this,error.message ?: "Check Settings.",Toast.LENGTH_LONG).show() }
    }
    override fun onRequestPermissionsResult(code:Int,permissions:Array<out String>,results:IntArray) {
        super.onRequestPermissionsResult(code,permissions,results)
        if(code==10 && results.firstOrNull()==PackageManager.PERMISSION_GRANTED)startListening()
        else if(code==10) { state.text="Microphone access is needed for listening. You can still paste a phrase." }
    }
    private fun renderLive() {
        if(example) { renderExample();return }
        val recent=memory.recent(limit=8)
        val selected=controller.selected?.let { memory.find(it) } ?: recent.firstOrNull()
        if(selected==null) {
            val intro=card(tint)
            intro.addView(text("Understand.\nThen join in.",34f,green,true))
            intro.addView(text("Hear the conversation. Unpack every word. Find something natural to say.",17f))
            intro.addView(space());intro.addView(button("Try an example") { example=true;renderBody();scroll.scrollTo(0,0) }.apply { background=shape(Color.WHITE,16);contentDescription="Try the Japanese example without recording or an API key" })
            add(intro)
            add(text("Your words, understood.",21f,bold=true))
            add(text("Choose a language you know and one you're learning. Listening transcribes every language; learning-language phrases become short lessons automatically.",16f,muted))
        } else renderUtterance(selected)
        add(button("＋  Type or paste a phrase") { compose() })
        if(recent.isNotEmpty()) {
            add(text("Recent conversation",18f,bold=true))
            for(item in recent) {
                val itemCard=card().apply { isClickable=true;setOnClickListener { controller.select(item.id) } }
                itemCard.addView(text("${item.detected.uppercase(Locale.ROOT)} · ${item.state}",11f,green,true))
                itemCard.addView(text(item.text,16f).apply { maxLines=3;ellipsize=android.text.TextUtils.TruncateAt.END })
                itemCard.contentDescription="Open transcript: ${item.text.take(80)}";add(itemCard,8)
            }
        }
    }
    private fun modePicker():View {
        val mode=row()
        for((name,value) in listOf("Original" to false,"Pronunciation" to true)) {
            mode.addView(button(name,pronunciation==value) { pronunciation=value;settings.setPronunciation(value);renderBody() },LinearLayout.LayoutParams(0,-2,1f))
        }
        return mode
    }
    private fun renderUtterance(item:Utterance) {
        if(item.lesson?.containsLearning==true) {
            renderLesson(item.lesson,item.profile)
        } else {
            val heard=card(tint);heard.addView(text("JUST HEARD · ${item.detected.uppercase(Locale.ROOT)}",11f,green,true));heard.addView(text(item.text,25f))
            heard.addView(text(item.state,13f,muted))
            if(item.error.isNotBlank())heard.addView(text(item.error,14f))
            if(item.lesson!=null)heard.addView(text(item.lesson.explanation,16f))
            if(item.state !in listOf("Queued","Learning","Detecting"))heard.addView(button(if(item.state=="Retry lesson")"Retry lesson" else "Teach this phrase",true) { controller.learn(item.id) })
            if(item.state=="Language uncertain")heard.addView(text("Short or mixed phrases can be hard to identify. Tap Teach this phrase if this is your learning language.",13f,muted))
            heard.addView(button("Edit into a new phrase") { compose(item.text) });add(heard)
        }
    }
    private fun renderLesson(lesson:Lesson,profile:Profile,exampleLabel:Boolean=false) {
        if(exampleLabel)add(text("EXAMPLE · English → Japanese · not a recording",11f,green,true))
        add(modePicker(),8)
        val heard=card(tint);heard.addView(text("WHAT YOU HEARD",11f,green,true));heard.addView(wordText(lesson.words,profile,25f))
        heard.addView(text("Tap any word for its meaning.",11f,muted));heard.addView(space(6))
        heard.addView(text("Meaning in ${profile.known.name}",12f,green,true));heard.addView(text(lesson.translation,18f));add(heard)
        val explanation=card();explanation.addView(text("What's being said",20f,bold=true));explanation.addView(text(lesson.explanation,16f))
        if(lesson.tip.isNotBlank())explanation.addView(text(lesson.tip,14f,muted))
        explanation.addView(button(if(wordList)"Hide word meanings" else "Word by word") { wordList=!wordList;renderBody() })
        if(wordList)for(word in lesson.words.filter { it.isWord })explanation.addView(text("${word.text} · ${word.reading}\n${word.meaning}"+(if(word.note.isBlank())"" else "\n${word.note}"),15f))
        add(explanation)
        add(text("You could say…",23f,bold=true),4)
        for(reply in lesson.replies) {
            val card=card();card.addView(text(reply.label.uppercase(Locale.ROOT),11f,green,true));card.addView(wordText(reply.words,profile,22f));card.addView(text(reply.translation,15f,muted))
            val actions=row();actions.addView(button("Hear it") { speak(reply.text,profile.learning.code) });actions.addView(button("Copy original") { (getSystemService(CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Reply",reply.text));Toast.makeText(this,"Reply copied",Toast.LENGTH_SHORT).show() });card.addView(actions);add(card)
        }
        add(text(if(exampleLabel)"This example isn't saved to your learning history." else "Saved automatically on this phone · words and replies included",11f,muted))
    }
    private fun wordText(words:List<Word>,profile:Profile,size:Float):TextView {
        val display=WordText.build(words,pronunciation);val spans=SpannableString(display.text)
        for(range in display.ranges)spans.setSpan(object:ClickableSpan() {
            override fun onClick(widget:View) { wordDialog(range.word,profile) }
            override fun updateDrawState(ds:TextPaint) { ds.color=green;ds.isUnderlineText=true }
        },range.start,range.end,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        return text("",size).apply { text=spans;movementMethod=LinkMovementMethod.getInstance();highlightColor=Color.rgb(203,224,195);setPadding(0,dp(10),0,dp(10));contentDescription=display.text+". Tap a word for its meaning." }
    }
    internal fun wordDialog(word:Word,profile:Profile) {
        val body=column(22);body.addView(text(word.text,30f,green,true));body.addView(text(word.reading,19f,muted));body.addView(text("In ${profile.known.name}",12f,green,true));body.addView(text(word.meaning,21f));if(word.note.isNotBlank())body.addView(text(word.note,16f))
        AlertDialog.Builder(this).setView(body).setPositiveButton("Got it",null).setNeutralButton("Hear word") { _,_->speak(word.text,profile.learning.code) }.show()
    }
    private fun renderExample() {
        val value=assets.open("example.json").bufferedReader().use { JSONObject(it.readText()) }
        val profile=Profile(Language("en-US","English"),Language("ja-JP","Japanese"))
        renderLesson(Lesson.parse(value.getJSONObject("lesson"),value.getString("text")),profile,true)
        add(button("Back to my conversation") { example=false;renderBody() })
    }
    private fun speak(value:String,code:String) {
        controller.stop("Listening paused for pronunciation. Tap Start listening to continue.")
        if(!ttsReady) { Toast.makeText(this,"Your phone's speech voice is not ready.",Toast.LENGTH_LONG).show();return }
        if(tts!!.setLanguage(Locale.forLanguageTag(code))<TextToSpeech.LANG_AVAILABLE) { Toast.makeText(this,"Install this language in your phone's text-to-speech settings.",Toast.LENGTH_LONG).show();return }
        tts!!.setSpeechRate(.85f);tts!!.speak(value,TextToSpeech.QUEUE_FLUSH,null,"lingolive-pronunciation")
    }
    private fun compose(value:String="") {
        controller.stop();val input=EditText(this).apply { hint="Paste what you heard";setText(value);minLines=3;maxLines=8;filters=arrayOf(android.text.InputFilter.LengthFilter(3000));setPadding(dp(20),dp(12),dp(20),dp(12)) }
        val dialog=AlertDialog.Builder(this).setTitle("Learn a phrase").setView(input).setNegativeButton("Cancel",null).setPositiveButton("Learn",null).create()
        dialog.setOnShowListener { dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val text=input.text.toString();if(text.isBlank()) { input.error="Enter a phrase.";return@setOnClickListener }
            screen="live";example=false;val id=controller.accept(text,autoTeach=false);controller.learn(id);dialog.dismiss();render()
        } };dialog.show()
    }
    private fun chooseLanguage(isKnown:Boolean) {
        controller.stop();val layout=column(12);val input=EditText(this).apply { hint="Search languages";setSingleLine(true) };layout.addView(input)
        val list=ListView(this);layout.addView(list,LinearLayout.LayoutParams(-1,dp(350)))
        var values=settings.languages
        fun filter(query:String) { values=settings.languages.filter { it.name.contains(query,true)||it.code.contains(query,true) };list.adapter=ArrayAdapter(this,android.R.layout.simple_list_item_1,values.map { "${it.name} · ${it.code}" }) }
        filter("");input.addTextChangedListener(object:android.text.TextWatcher { override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int){};override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int){filter(s.toString())};override fun afterTextChanged(s:android.text.Editable?){} })
        val dialog=AlertDialog.Builder(this).setTitle(if(isKnown)"Language I know" else "Language I'm learning").setView(layout).setNegativeButton("Cancel",null).create()
        list.setOnItemClickListener { _,_,index,_->
            val old=settings.profile();val next=if(isKnown)old.copy(known=values[index]) else old.copy(learning=values[index])
            try { settings.saveProfile(next);dialog.dismiss();render() } catch(e:IllegalArgumentException){input.error=e.message}
        };dialog.show()
    }
    private fun renderMemory() {
        add(text("Your learning, kept.",29f,bold=true),2);add(text("Lessons, words and transcripts are stored only on this phone.",14f,muted))
        val tabs=row();for(name in listOf("Lessons","Words","All speech"))tabs.addView(button(name,memoryTab==name) { memoryTab=name;renderBody() },LinearLayout.LayoutParams(0,-2,1f));add(tabs)
        val input=EditText(this).apply { hint="Search your memory";setSingleLine(true);contentDescription="Search saved learning" };add(input)
        val items=column();add(items)
        fun fill(query:String) {
            items.removeAllViews()
            if(memoryTab=="Words") {
                val words=memory.words(query)
                if(words.isEmpty())items.addView(text("Word meanings will appear here after your first lesson.",16f,muted))
                for(word in words) {
                    val tile=card();tile.addView(text("${word.text} · ${word.reading}",21f,green,true));tile.addView(text(word.meaning,16f));tile.addView(text("${word.language} → ${word.known} · ${word.seen} lesson(s)",11f,muted));items.addView(tile,LinearLayout.LayoutParams(-1,-2).apply { bottomMargin=dp(10) })
                }
            } else {
                val entries=memory.recent(query,500).filter { memoryTab=="All speech" || it.lesson?.containsLearning==true }
                if(entries.isEmpty())items.addView(text(if(memoryTab=="Lessons")"Your first lesson will live here. Try a phrase in the language you're learning." else "Your completed speech transcripts will appear here.",16f,muted))
                for(item in entries) {
                    val tile=card();tile.addView(text("${item.profile.learning.name} · ${java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.MEDIUM,java.text.DateFormat.SHORT).format(java.util.Date(item.created))}",11f,muted));tile.addView(text(item.text,20f,green,true).apply { maxLines=3 });tile.addView(text(item.lesson?.translation ?: item.state,15f));tile.setOnClickListener { detail=item.id;screen="detail";render();scroll.scrollTo(0,0) };tile.isClickable=true;tile.contentDescription="Open saved phrase: ${item.text.take(80)}";items.addView(tile,LinearLayout.LayoutParams(-1,-2).apply { bottomMargin=dp(10) })
                }
            }
        }
        fill("");input.addTextChangedListener(object:android.text.TextWatcher { override fun beforeTextChanged(s:CharSequence?,a:Int,b:Int,c:Int){};override fun onTextChanged(s:CharSequence?,a:Int,b:Int,c:Int){fill(s.toString())};override fun afterTextChanged(s:android.text.Editable?){} })
    }
    private fun delete(id:String) { AlertDialog.Builder(this).setTitle("Delete this entry?").setMessage("Its transcript, lesson and saved word links will be removed from this phone.").setNegativeButton("Keep",null).setPositiveButton("Delete") { _,_->memory.delete(id);navigate("memory") }.show() }
    private fun renderSettings() {
        add(text("Make it yours.",29f,bold=true));add(text("Your languages",19f,bold=true),0)
        add(button("I know: ${settings.profile().known.name}") { chooseLanguage(true) },0);add(button("I'm learning: ${settings.profile().learning.name}") { chooseLanguage(false) })
        val current=settings.connection();val connection=card();connection.addView(text("Connection",21f,bold=true));connection.addView(text("Set this up on your phone. No API key is built into the app.",14f,muted))
        val mode=Spinner(this).apply { adapter=ArrayAdapter(this@MainActivity,android.R.layout.simple_spinner_dropdown_item,listOf("My Google API key","Hosted on Google Cloud"));setSelection(if(current.hosted)1 else 0);contentDescription="Connection mode" };connection.addView(mode)
        fun field(hint:String,password:Boolean=false)=EditText(this).apply { this.hint=hint;setSingleLine(true);setPadding(dp(8),dp(12),dp(8),dp(12));if(password){inputType=android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD;transformationMethod=PasswordTransformationMethod.getInstance()};contentDescription=hint }
        val device=column();val key=field(if(current.apiKey.isBlank())"Google API key" else "Google API key saved · enter to replace",true);device.addView(key)
        device.addView(text("Use a Google AI Studio key with access to Gemini Transcribe Live and Flash.",13f,muted));connection.addView(device)
        val hosted=column();val url=field("Cloud Run HTTPS URL").apply { setText(current.serverUrl) };val access=field(if(current.accessToken.isBlank())"Backend access token" else "Backend token saved · enter to replace",true);hosted.addView(url);hosted.addView(access);hosted.addView(text("Your server holds the Google key. Enter the private access token supplied by its owner.",13f,muted));connection.addView(hosted)
        val advanced=column().apply { visibility=View.GONE };val flash=field("Flash model ID").apply { setText(current.flashModel) };val transcribe=field("Transcribe Live model ID").apply { setText(current.transcribeModel) };advanced.addView(flash);advanced.addView(transcribe)
        val modelSettings=button("Model settings") { advanced.visibility=if(advanced.visibility==View.VISIBLE)View.GONE else View.VISIBLE }
        connection.addView(modelSettings);connection.addView(advanced)
        val error=text("",14f,Color.rgb(154,62,47));connection.addView(error)
        fun showMode() { device.visibility=if(mode.selectedItemPosition==0)View.VISIBLE else View.GONE;hosted.visibility=if(mode.selectedItemPosition==1)View.VISIBLE else View.GONE;modelSettings.visibility=if(mode.selectedItemPosition==0)View.VISIBLE else View.GONE;if(mode.selectedItemPosition==1)advanced.visibility=View.GONE }
        mode.onItemSelectedListener=object:AdapterView.OnItemSelectedListener { override fun onItemSelected(parent:AdapterView<*>?,view:View?,position:Int,id:Long){showMode()};override fun onNothingSelected(parent:AdapterView<*>?){} };showMode()
        connection.addView(button("Save connection",true) {
            try {
                val next=Connection(mode.selectedItemPosition==1,key.text.toString().trim().ifBlank { current.apiKey },url.text.toString().trim(),access.text.toString().trim().ifBlank { current.accessToken },flash.text.toString().trim(),transcribe.text.toString().trim())
                settings.saveConnection(next);navigate("live");Toast.makeText(this,if(next.configured)"Connection saved" else "Saved. Add a key when you're ready.",Toast.LENGTH_SHORT).show()
            } catch(e:Exception){error.text=e.message ?: "Check the connection settings."}
        });connection.addView(button("Remove saved credentials") { settings.clearCredentials();renderBody();Toast.makeText(this,"Credentials removed",Toast.LENGTH_SHORT).show() });add(connection)
        val privacy=card(tint);privacy.addView(text("You control the memory.",20f,green,true));privacy.addView(text("Microphone audio is streamed to Google while listening is active. The app doesn't save audio recordings. Final transcripts, lessons and word meanings stay in app-private storage on this phone. The hosted service forwards requests without a learning-history database.",14f));privacy.addView(text("The Google key and backend token are encrypted using Android Keystore. Cloud requests require internet and may incur usage charges on the configured Google account.",13f,muted));add(privacy)
        add(button("Delete all local learning") { AlertDialog.Builder(this).setTitle("Delete all local learning?").setMessage("All transcripts, lessons and saved words on this phone will be deleted. This cannot be undone.").setNegativeButton("Keep",null).setPositiveButton("Delete all") { _,_->memory.clear();controller.select(null);Toast.makeText(this,"Local learning deleted",Toast.LENGTH_SHORT).show() }.show() })
    }
}
