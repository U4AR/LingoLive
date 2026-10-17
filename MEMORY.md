# Conversation memory (web 1.4 source)

The main screen shows heard speech, its translation and three possible replies.
Tap a word for a small meaning bubble. Pronunciation, playback, copy, typed input,
saved history and optional explanation remain available. The gear opens learning
settings; no goal is required to start.

## What a lesson receives

The first-visit tutorial stores only `lingolive-tutorial-v1=done` in LocalStorage
when skipped or completed. It contains no credentials or learner facts and can
be replayed from settings. Its examples make no paid calls or sensor requests.

Each authenticated lesson request contains the current utterance, language pair,
up to eight earlier turns from the same conversation/pair/learner, a bounded
summary, the previous three suggestions and up to twelve previously seen words.
The explicit goal is optional. When it is empty, Flash is asked to infer the
immediate situation and likely learner intent. Suggestions are kept separate from
spoken history, and encountered vocabulary is never described as mastered.

Speaker labels are estimates from conversation context, not speaker identification
or reliable diarization. Medium/high model estimates are stored as `likely_user`
or `likely_other`; ambiguous speech stays unattributed. A distinctive exact match
to a previous suggested reply is another tentative learner cue. Common greetings
are excluded. **I said this**, under a reply's more menu, explicitly confirms a
turn without another model request. Confirmed goals override tentative intent.

## Storage and lifetime

| Memory | Where / lifetime |
| --- | --- |
| Learner name and editable notes (800 characters) | LocalStorage, separate per local profile |
| Transcripts, lessons and vocabulary | IndexedDB, separate per profile; delete in Saved |
| Explicit goal and inferred intent | Local conversation state; a scene expires after 90 minutes of inactivity |
| Earlier turns | At most eight, 400 characters each; older than 90 minutes excluded |
| Scene summary | At most 600 characters; temporary model inference |
| Optional approximate location | RAM only, two decimal coordinates, accuracy at least 1 km; expires after five minutes |
| Optional recent sound | RAM only, at most four seconds of mono 16 kHz PCM WAV; never saved in history |

New conversation resets scene history and goals sent to Google while retaining
saved lessons. Switching profiles stops capture and sensor sharing. Late speech
and model responses remain tied to the original learner/conversation. Deleting
an in-flight lesson prevents its response from recreating the deleted record.

Profiles isolate learning state; they are not separate authenticated accounts.
Anyone using the same browser can switch local profiles. Clearing browser site
data removes local memory. There is no cloud history, account sync or server-side
conversation database. Paid requests require a private-code session or an active personal-key session.

Location and recent sound start off and require opt-in. The browser rounds
location before transmission; the backend also rounds it and rejects stale data.
The optional sound is a separate Google multimodal `inlineData` part alongside
the transcription, not a base64 string inside the text prompt. No Maps API call
is made; Open map opens a normal Google Maps link. Setting inference must remain
broad and uncertain; prompts prohibit guessing private addresses or exact venues.

## Cost and verification

Personal keys live only in an expiring server-memory session, separate from
learner memory. Cookies contain a signed opaque session ID; key fields clear on
successful connection, method changes and closing the dialog. Keys are never
added to prompts, transcript records, IndexedDB, LocalStorage or service-worker
caches. They are sent over HTTPS to the host and require trusting that host.
Disconnect removes the key session, invalidates copied session cookies and stops
its active streams. Expiry and restarts require re-entering the key. An already
started lesson may finish after disconnect. Local profiles share this browser's
connection; they are not separate authentication accounts.

Personal-key requests always use the Gemini Developer API with that key, even
when host-code mode uses Vertex. There is no fallback to host credentials.
Host and personal-key users have separate shared rolling model allowances;
all personal-key sessions share their allowance, so reconnecting does not reset
it. Two concurrent lessons/two listeners and connection pacing remain shared
infrastructure guards. All AI can still be paused by the host. Personal keys
charge their own Google projects but still use the host's Cloud Run relay.

Context travels in the existing lesson call; there is no extra summarization or
speaker-classification call. Authentication, audio pacing, shared quotas, two
concurrent lessons and one Cloud Run instance remain in force. Longer context or
opt-in audio can increase model usage; RAM quotas reset on a service restart and
are not a hard billing cap.

Local tests verify transport, bounds, isolation and UI with explicit Google
fixtures. Web 1.4 uses a bounded reading format and one Gemini 3.8 Flash request
with low reasoning for all lesson work; it is not deployed or measured live yet.
Web 1.3 remains deployed as `lingolive-00005-lch`. A real hosted test used
synthesized audio, transcription, a blank goal, prior context and the optional
WAV input to produce a complete context lesson. Broad semantic accuracy,
speaker estimates, physical-phone capture and valid personal-key inference still
need user testing. See `validation/cloud-current-api-results.json`.
