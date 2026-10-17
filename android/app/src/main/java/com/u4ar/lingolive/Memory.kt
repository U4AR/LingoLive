package com.u4ar.lingolive

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONObject
import java.util.UUID

data class Utterance(val id: String, val text: String, val profile: Profile, val created: Long,
    val detected: String, val state: String, val error: String, val lesson: Lesson?)
data class RememberedWord(val text: String, val reading: String, val meaning: String, val note: String, val language: String, val known: String, val seen: Int)
class Memory(context: Context) : SQLiteOpenHelper(context, "learning.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE utterances(id TEXT PRIMARY KEY,text TEXT NOT NULL,known_code TEXT NOT NULL,known_name TEXT NOT NULL,learning_code TEXT NOT NULL,learning_name TEXT NOT NULL,created INTEGER NOT NULL,detected TEXT NOT NULL DEFAULT 'und',state TEXT NOT NULL DEFAULT 'Detecting',error TEXT NOT NULL DEFAULT '',lesson TEXT)")
        db.execSQL("CREATE TABLE words(utterance_id TEXT NOT NULL,word TEXT NOT NULL,reading TEXT NOT NULL,meaning TEXT NOT NULL,note TEXT NOT NULL,language TEXT NOT NULL,known TEXT NOT NULL,PRIMARY KEY(utterance_id,word,meaning),FOREIGN KEY(utterance_id) REFERENCES utterances(id) ON DELETE CASCADE)")
        db.execSQL("CREATE INDEX by_created ON utterances(created)")
    }
    override fun onConfigure(db: SQLiteDatabase) { db.setForeignKeyConstraintsEnabled(true) }
    override fun onUpgrade(db: SQLiteDatabase, old: Int, next: Int) {}
    @Synchronized fun add(text: String, profile: Profile): String {
        require(text.isNotBlank() && text.length <= 60000)
        val id = UUID.randomUUID().toString()
        writableDatabase.insertOrThrow("utterances", null, ContentValues().apply {
            put("id", id); put("text", text); put("known_code", profile.known.code); put("known_name", profile.known.name)
            put("learning_code", profile.learning.code); put("learning_name", profile.learning.name); put("created", System.currentTimeMillis())
        })
        return id
    }
    @Synchronized fun state(id: String, state: String, detected: String? = null, error: String = "") {
        writableDatabase.update("utterances", ContentValues().apply { put("state", state); put("error", error); if (detected != null) put("detected", detected) }, "id=?", arrayOf(id))
    }
    @Synchronized fun save(id: String, lesson: Lesson) {
        val utterance = find(id) ?: return
        require(lesson.source == utterance.text)
        val db = writableDatabase; db.beginTransaction()
        try {
            db.update("utterances", ContentValues().apply { put("lesson", lesson.json); put("state", if (lesson.containsLearning) "Learned" else "Transcript"); put("detected", lesson.detectedLanguage); put("error", "") }, "id=?", arrayOf(id))
            db.delete("words", "utterance_id=?", arrayOf(id))
            if (lesson.containsLearning) for (word in lesson.words + lesson.replies.flatMap { it.words }) {
                if (!word.isWord) continue
                db.insertWithOnConflict("words", null, ContentValues().apply {
                    put("utterance_id", id); put("word", word.text); put("reading", word.reading); put("meaning", word.meaning); put("note", word.note)
                    put("language", utterance.profile.learning.code); put("known", utterance.profile.known.code)
                }, SQLiteDatabase.CONFLICT_IGNORE)
            }
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }
    private val columns = "id,text,known_code,known_name,learning_code,learning_name,created,detected,state,error,lesson"
    private fun row(c: android.database.Cursor): Utterance {
        val text = c.getString(1)
        return Utterance(c.getString(0), text, Profile(Language(c.getString(2), c.getString(3)), Language(c.getString(4), c.getString(5))),
            c.getLong(6), c.getString(7), c.getString(8), c.getString(9), if (c.isNull(10)) null else Lesson.parse(JSONObject(c.getString(10)), text))
    }
    @Synchronized fun find(id: String): Utterance? = readableDatabase.rawQuery("SELECT $columns FROM utterances WHERE id=?", arrayOf(id)).use { if (it.moveToFirst()) row(it) else null }
    @Synchronized fun recent(query: String = "", limit: Int = 100): List<Utterance> = readableDatabase.rawQuery("SELECT $columns FROM utterances WHERE instr(lower(text),lower(?))>0 OR instr(lower(coalesce(lesson,'')),lower(?))>0 ORDER BY created DESC,rowid DESC LIMIT ?", arrayOf(query, query, limit.coerceIn(1,500).toString())).use { c -> buildList { while (c.moveToNext()) add(row(c)) } }
    @Synchronized fun words(query: String = ""): List<RememberedWord> = readableDatabase.rawQuery("SELECT word,reading,meaning,note,language,known,count(DISTINCT utterance_id) FROM words WHERE instr(lower(word||reading||meaning),lower(?))>0 GROUP BY word,meaning,language,known ORDER BY count(DISTINCT utterance_id) DESC,max(rowid) DESC LIMIT 500", arrayOf(query)).use { c -> buildList { while (c.moveToNext()) add(RememberedWord(c.getString(0),c.getString(1),c.getString(2),c.getString(3),c.getString(4),c.getString(5),c.getInt(6))) } }
    @Synchronized fun delete(id: String) { writableDatabase.delete("utterances", "id=?", arrayOf(id)) }
    @Synchronized fun clear() { writableDatabase.delete("utterances", null, null) }
    @Synchronized fun recover() { writableDatabase.execSQL("UPDATE utterances SET state='Retry lesson',error='Lesson interrupted. Tap to retry.' WHERE state IN ('Queued','Learning','Detecting')") }
}
