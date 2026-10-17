package com.u4ar.lingolive

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class CoreTest {
    private fun example()=JSONObject(javaClass.getResource("/example.json")!!.readText())
    @Test fun sourceAndAllReplyWordsHaveDefinitionsAndKeepExactCharacters() {
        val data=example();val lesson=Lesson.parse(data.getJSONObject("lesson"),data.getString("text"))
        assertEquals(data.getString("text"),WordText.build(lesson.words,false).text)
        assertEquals(3,lesson.replies.size)
        for(words in listOf(lesson.words)+lesson.replies.map { it.words }) {
            val display=WordText.build(words,false)
            assertEquals(words.count { it.isWord },display.ranges.size)
            for(range in display.ranges) { assertEquals(range.word.text,display.text.substring(range.start,range.end));assertTrue(range.word.meaning.isNotBlank()) }
        }
    }
    @Test fun pronunciationKeepsEveryWordClickableWithNaturalSpacesAndPunctuation() {
        val data=example();val lesson=Lesson.parse(data.getJSONObject("lesson"),data.getString("text"));val shown=WordText.build(lesson.words,true)
        assertEquals("kōhī wa ikaga desu ka？",shown.text)
        assertEquals(5,shown.ranges.size)
        assertEquals(listOf("kōhī","wa","ikaga","desu","ka"),shown.ranges.map { shown.text.substring(it.start,it.end) })
    }
    @Test fun unicodeAndRightToLeftOffsetsReferToTheSameWord() {
        val words=listOf(Word("🌿 ","🌿 ","","",false),Word("مرحبا","marhaban","hello","greeting",true),Word(" "," ","","",false),Word("世界","sekai","world","",true),Word("!","!","","",false))
        val original=WordText.build(words,false);assertEquals("🌿 مرحبا 世界!",original.text)
        assertEquals("مرحبا",original.text.substring(original.ranges.first().start,original.ranges.first().end))
        assertEquals(3,original.ranges.first().start)
        val reading=WordText.build(words,true);assertEquals("🌿 marhaban sekai!",reading.text)
    }
    @Test fun refusesRewrittenSourceAndUnexplainedWords() {
        val data=example()
        try { Lesson.parse(data.getJSONObject("lesson"),"different source");fail() } catch(_:IllegalArgumentException){}
        val word=data.getJSONObject("lesson").getJSONArray("words").getJSONObject(0).put("is_word",false)
        try { Word.parse(word);fail() } catch(_:IllegalArgumentException){}
        word.put("is_word",true).put("meaning","")
        try { Word.parse(word);fail() } catch(_:IllegalArgumentException){}
    }
    @Test fun missingRepliesAreRejectedInsteadOfShowingPartialTeaching() {
        val data=example();data.getJSONObject("lesson").getJSONArray("replies").remove(2)
        try { Lesson.parse(data.getJSONObject("lesson"),data.getString("text"));fail() } catch(_:IllegalArgumentException){}
    }
    @Test fun languageAliasesAndRegionsMatchButDistinctLanguagesDoNot() {
        assertTrue(LanguageCodes.matches("en-IN","en-US"));assertTrue(LanguageCodes.matches("cmn-Hans-CN","zh"));assertTrue(LanguageCodes.matches("iw-IL","he"));assertTrue(LanguageCodes.matches("tl","fil-PH"))
        assertFalse(LanguageCodes.matches("ja-JP","zh"))
        try { Profile(Language("en-IN","English"),Language("en-US","English")).validate();fail() } catch(_:IllegalArgumentException){}
    }
    @Test fun onlyLearningLanguageEvidenceTriggersAutomaticTeaching() {
        assertFalse(LanguageCodes.shouldTeach(listOf("en" to .95f,"es" to .05f),"ja-JP"))
        assertTrue(LanguageCodes.shouldTeach(listOf("en" to .6f,"ja" to .4f),"ja-JP"))
        assertFalse(LanguageCodes.shouldTeach(listOf("und" to .9f,"ja" to .1f),"ja-JP"))
    }
    @Test fun interimIsNeverCommittedAndFinalTextDoesNotUseAgentOutput() {
        val partial=LiveProtocol.events(JSONObject("""{"serverContent":{"interimInputTranscription":{"text":"コーヒー"},"modelTurn":{"parts":[{"text":"not a transcript"}]}}}"""))
        assertEquals(listOf(LiveEvent.Interim("コーヒー")),partial)
        val final=LiveProtocol.events(JSONObject("""{"serverContent":{"inputTranscription":{"text":"コーヒーはいかがですか？"}}}"""))
        assertEquals(listOf(LiveEvent.Final("コーヒーはいかがですか？")),final)
        assertEquals(2,(final+final).filterIsInstance<LiveEvent.Final>().size)
    }
    @Test fun setupUsesDedicatedTranscriberAutomaticLanguagesAndLiteralMode() {
        val setup=JSONObject(LiveProtocol.setup("gemini-3.5-transcribe-live")).getJSONObject("setup")
        assertEquals("models/gemini-3.5-transcribe-live",setup.getString("model"))
        assertEquals(0,setup.getJSONObject("inputAudioTranscription").getJSONArray("languageCodes").length())
        assertEquals("VERBATIM",setup.getJSONObject("inputAudioTranscription").getString("mode"))
    }
    @Test fun hostedOriginRequiresHttpsAndDoesNotAcceptEmbeddedCredentials() {
        Connection.validateServer("https://example.run.app")
        for(value in listOf("http://example.com","https://name:secret@example.com","https://example.com/v1","https://example.com?key=value","file:///tmp/test")) {
            try { Connection.validateServer(value);fail("Invalid origin accepted") } catch(_:IllegalArgumentException){}
        }
    }
}
