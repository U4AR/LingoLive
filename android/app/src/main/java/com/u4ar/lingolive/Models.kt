package com.u4ar.lingolive

import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale

data class Language(val code: String, val name: String)
data class Profile(val known: Language, val learning: Language) {
    fun validate() { require(!LanguageCodes.matches(known.code, learning.code)) { "Choose different languages to know and learn." } }
    fun json() = JSONObject().put("known_code", known.code).put("known_name", known.name).put("learning_code", learning.code).put("learning_name", learning.name)
}
object LanguageCodes {
    fun base(code: String): String = when (val base = code.lowercase(Locale.ROOT).replace('_', '-').substringBefore('-')) {
        "cmn", "zho" -> "zh"; "iw" -> "he"; "in" -> "id"; "tl" -> "fil"; "no" -> "nb"; else -> base
    }
    fun matches(a: String, b: String) = base(a) == base(b)
    fun shouldTeach(candidates: List<Pair<String, Float>>, target: String) = candidates.any { matches(it.first, target) && it.second >= .35f }
}
data class Word(val text: String, val reading: String, val meaning: String, val note: String, val isWord: Boolean) {
    companion object {
        fun parse(value: JSONObject): Word {
            val word = Word(value.getString("text"), value.getString("reading"), value.getString("meaning"), value.getString("note"), value.getBoolean("is_word"))
            require(word.text.isNotEmpty() && word.text.length <= 1000 && word.meaning.length <= 2000 && word.note.length <= 2000)
            require(!word.isWord || (word.meaning.isNotBlank() && word.reading.isNotBlank())) { "A word is missing its meaning or pronunciation. Please retry." }
            require(word.isWord || word.text.none { it.isLetterOrDigit() }) { "The lesson left a word unexplained. Please retry." }
            return word
        }
    }
}
data class Reply(val label: String, val translation: String, val words: List<Word>) { val text get() = words.joinToString("") { it.text } }
data class Lesson(val source: String, val translation: String, val explanation: String, val tip: String,
    val detectedLanguage: String, val containsLearning: Boolean, val words: List<Word>, val replies: List<Reply>, val json: String) {
    companion object {
        private fun words(array: JSONArray): List<Word> {
            require(array.length() <= 1200) { "This lesson is too long. Try a shorter phrase." }
            return (0 until array.length()).map { Word.parse(array.getJSONObject(it)) }
        }
        fun parse(value: JSONObject, source: String): Lesson {
            require(value.toString().length <= 500000 && source.length <= 60000)
            val contains = value.getBoolean("contains_learning_language")
            val words = words(value.getJSONArray("words"))
            val replies = value.getJSONArray("replies")
            require(replies.length() <= 3)
            val items = (0 until replies.length()).map { index ->
                val reply = replies.getJSONObject(index)
                Reply(reply.getString("label"), reply.getString("translation"), words(reply.getJSONArray("words"))).also {
                    require(it.words.any { word -> word.isWord } && it.label.isNotBlank() && it.translation.isNotBlank())
                }
            }
            require(!contains || (words.joinToString("") { it.text } == source && words.any { it.isWord } && items.size == 3)) {
                "The lesson changed or omitted words. Your transcript is saved; tap Retry lesson."
            }
            return Lesson(source, value.getString("translation"), value.getString("explanation"), value.getString("tip"),
                value.getString("detected_language"), contains, words, items, value.toString())
        }
    }
}
data class WordRange(val start: Int, val end: Int, val word: Word)
data class WordDisplay(val text: String, val ranges: List<WordRange>)
object WordText {
    fun build(words: List<Word>, pronunciation: Boolean): WordDisplay {
        val text = StringBuilder(); val ranges = mutableListOf<WordRange>(); var previousWord = false
        for (word in words) {
            val piece = if (pronunciation && word.isWord) word.reading.trim() else word.text
            if (pronunciation && previousWord && word.isWord && text.isNotEmpty() && !text.last().isWhitespace() && piece.firstOrNull()?.isLetterOrDigit() == true) text.append(' ')
            val start = text.length; text.append(piece)
            if (word.isWord) ranges.add(WordRange(start, text.length, word))
            previousWord = word.isWord
        }
        return WordDisplay(text.toString(), ranges)
    }
}
sealed class LiveEvent {
    data object Ready: LiveEvent()
    data class Interim(val text: String): LiveEvent()
    data class Final(val text: String): LiveEvent()
    data object Renew: LiveEvent()
    data class Error(val message: String): LiveEvent()
}
object LiveProtocol {
    fun setup(model: String) = JSONObject().put("setup", JSONObject().put("model", "models/$model")
        .put("generationConfig", JSONObject().put("responseModalities", JSONArray().put("TEXT")))
        .put("inputAudioTranscription", JSONObject().put("languageCodes", JSONArray()).put("mode", "VERBATIM"))).toString()
    fun events(value: JSONObject): List<LiveEvent> = buildList {
        if (value.has("setupComplete") || value.has("setup_complete")) add(LiveEvent.Ready)
        if (value.has("error")) add(LiveEvent.Error("Google transcription could not continue. Check your connection and model access."))
        if (value.has("goAway") || value.has("go_away")) add(LiveEvent.Renew)
        val content = value.optJSONObject("serverContent") ?: value.optJSONObject("server_content") ?: return@buildList
        val interim = content.optJSONObject("interimInputTranscription") ?: content.optJSONObject("interim_input_transcription")
        interim?.optString("text")?.takeIf { it.isNotBlank() }?.let { add(LiveEvent.Interim(it)) }
        val final = content.optJSONObject("inputTranscription") ?: content.optJSONObject("input_transcription")
        final?.optString("text")?.takeIf { it.isNotBlank() }?.let { add(LiveEvent.Final(it)) }
    }
}
