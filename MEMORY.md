# Conversation memory (web 1.5 source)

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
started lesson may finish or be cancelled after disconnect. Warm HTTP connections
are reused, then closed on key removal/expiry and application shutdown. Local profiles share this browser's
connection; they are not separate authentication accounts.

Personal-key requests always use the Gemini Developer API with that key, even
when host-code mode uses Vertex. There is no fallback to host credentials.
Host and personal-key users have separate shared rolling model allowances;
all personal-key sessions share their allowance, so reconnecting does not reset
it. Two concurrent lessons/two listeners and connection pacing remain shared
infrastructure guards. All AI can still be paused by the host. Personal keys
charge their own Google projects but still use the host's Cloud Run relay.

Each lesson runs two Gemini 3.1 Flash-Lite requests in parallel: source understanding
and replies. Both receive the same incoming goal, history, summary, previous
suggestions and learner notes. There is no third summarization or classification
call. The reply branch does not wait for the source branch's newly inferred scene;
that inference enters the next turn's context. Optional recent sound goes only to
the source branch. Reply generation uses the transcript and existing context.

Two requests consume two units of the unchanged model-call allowances:
24/minute, 360/hour and 400/day. Thus parallel mode permits at most 12 lessons/minute,
180/hour and 200/day per allowance group. The combined output cap is still 4,096
tokens per lesson, split between branches. A failure cancels its sibling; there
is no automatic retry or third paid call. Two simultaneous lessons remain allowed.
Authentication and quotas run before model calls. Longer context or opt-in audio
can increase usage; counters reset on restart and are not a hard billing cap.

Compact nonempty word triples are expanded into the original saved/public lesson
format. Missing definitions/readings and changed, reordered or missing letters
fail validation. Exact spacing and punctuation are restored from the source;
Latin readings reuse original text. Replies are short, meanings are brief and the
explanation is concise. Optional per-word notes and a separate tip are empty.

Local tests verify transport, bounds, isolation and UI with explicit Google
fixtures. Broad semantic accuracy, speaker estimates, physical-phone capture and
valid personal-key inference still need user testing. Current deployment and
real Google evidence: `validation/cloud-current-*.json`; measured speed and
limitations: `docs/LATENCY.md`.
