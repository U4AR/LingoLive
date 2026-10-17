# Conversation memory (web 1.9)

Live: https://lingolive-358650584819.us-central1.run.app, revision
`lingolive-00023-vef`, 100% traffic; verification tag removed. Runtime source
`050fd58196b186b7d45a955a63e168b749c05852`. Public assets, unauthenticated
HTTP/WebSocket rejection and unchanged resource/quota guards verified.
112 backend / 91 browser / eight plan-core / sixteen place-core checks pass.
Four real-Gemini typed cases passed; HTTP mean 2.065 s, a tiny functional
sample, not a new latency guarantee or physical-microphone benchmark.
The task-plan request did not change the video transcript or generate media.

The main screen shows heard speech, its translation and three possible replies.
During a live exchange, replies have pronunciation, playback and copy controls.
Afterwards, open Saved to review words in a meaning bubble, explanations and
practice replies. Review uses already saved data and makes no extra model call.
Typed input and the same saved history remain available. The gear opens learning
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

## Plan before leaving (web 1.9)

Known-language text gets a dedicated meaning-preserving expression prompt when
local langdetect has at least 12 letters and confidence >=0.95; otherwise the
model routes it. Explicit Help me say this always selects that prompt. Source
language flags remain honest. Neither local hints nor the model identify speakers.
The detector runs locally with fixed seed and makes no API request. Expression
source analysis still uses only original speech. Expression replies allow up to
ten word rows to cover compound intentions; ordinary next replies retain six.
The shared 4,096 output-token allowance is unchanged.


An explicit task plan is separate from conversation goals, remembered habits and
GPS place memory. Open **My plan → Before you go** and save a short intention,
for example: “Reach the railway station by cab; probably stop for tea on the way.”
No AI call or GPS is required to save it. Optional ordered steps can be entered
one per line (up to six); a trailing `?` or `(optional)` marks a tentative stop,
and each displayed step has an Optional checkbox. The plan lasts for one day
from saving and survives new conversations, scene expiry and page reload for
this learner on this browser. It is excluded from AI context while paused,
expired or complete. The text stays available for editing until cleared.

Both existing parallel calls receive intent (max600 characters), steps (max6,
100 characters each), pending/done/skipped states and the current step. Current
words and a conversation-specific explicit goal take precedence over the broader
plan. A possible tea stop remains tentative, and a future destination is never
inferred to be the current GPS position. Saved-place proximity guards do not
suppress a deliberately entered future plan.

**Done, next step**, **Skip step** and **Previous step** change progress only on
user action; neither model output nor location marks a step complete or books a
cab. A narrative-only plan already works on the first request. The existing source
call may propose a draft step list for it; the learner must choose **Use suggested
steps** before it replaces the empty list. A plan ID/revision ticket rejects late
suggestions after editing, pausing, clearing or profile switching. No separate
organizing model request is made. A single active plan per learner bounds storage.

Clearing/pausing the plan withholds its explicit context. Plan-scoped old summaries
and turns are excluded when the active plan changes; temporary inferred intent is
cleared on that transition. Copied task-plan payloads are excluded from saved
lesson-context snapshots. Original saved conversations remain available until
separately deleted. Plans are user intentions, not permanent facts about activities
or visited locations, and prompts prohibit copying the plan into durable memory.

## Help the learner express their own words

Previously, a phrase containing only the known language produced no target-language
replies. In web 1.9, it can produce **express** suggestions: three natural ways to
say the current intent in the learning language, with meanings and pronunciation.
For example, English “Could we stop for tea first?” becomes a Kannada request,
rather than treating it as the other participant's question and answering it.
Negation, questions and tentative language should be preserved. **Help me say this**
explicitly requests this behavior for any selected phrase; marking typed input as
one's own words uses it too. The backend forces expression when detected source language matches the known language, even if a model mislabels the reply mode. Language detection is still an estimate,
not verified speaker identity. Other participants' facts are not learned merely
because a known-language phrase was rendered in the target language.

`contains_learning_language` continues to describe the original utterance honestly.
For English source without Kannada, it remains false and source `words=[]`; only
the three generated target phrases carry Kannada word definitions/readings.
`reply_mode=express` permits those target phrases to be saved/reviewed. For heard
learning-language speech, `reply_mode=respond` offers contextual next replies.
Live mode prioritizes speaking; stored target words become tappable in Saved.
Both modes use the existing two calls and unchanged combined output cap.

## Return-only place memory (web 1.8)

The earlier version remembered place names without geographic gating. Saved places
are now a separate opt-in store in the local learner profile. The AI proposes a
label and a useful note, never coordinates or an executable write. The browser
independently checks consent, a fresh accurate stationary location, capacity,
rate, grounding, speaker evidence and the current request's visit/epoch ticket.
The existing source-understanding call performs extraction; no extra paid call.

Hard limits: **five places, three notes each, two place notes in context**. Automatic
writes are limited to two per rolling day, at least 30 minutes apart, and one per
stationary stay. A full place/store rejects a new write instead of growing or
silently evicting another place. Manual additions also obey the capacity/location
checks. A place expires 90 days after its last note addition/edit.

Saved anchors are latitude/longitude rounded to three decimals (roughly 100-metre
cells), kept only in LocalStorage with a label, notes and a few visit-state fields.
They are not route histories. Fine current coordinates stay in RAM. The browser
requires accuracy at most 75 m, speed at most 2.5 m/s when provided, a fix no older
than 90 seconds and at least two distinct position samples spanning 60 seconds
of staying nearby. It requests foreground updates every 30 seconds while opted in.
Moving more than 60 m plus reported uncertainty resets dwell. Missing/stale/poor
GPS, movement, permission denial, location off or a different learner suppresses
recall. Sensor use stops on hide/unload/profile change and starts off on reload.

A match requires `distance(current fix, rounded anchor) + reported accuracy + 80 m
rounding allowance <= 250 m`. The 80 m allowance bounds three-decimal rounding
at the supported latitudes. This is a broad-area check, not proof of an exact
shop, indoor position, home or work. Adjacent venues inside that area cannot be
reliably distinguished; the learner must correct misleading notes. No reverse
geocoding or paid Maps API is used.

The first save does not immediately replay itself. A later visit requires an
observed departure and stable return, or a fresh stable match after at least
30 minutes without observations. The latter accommodates closing the app between
visits and cannot prove the user physically left. Saved visit state contains only
a last-seen timestamp and return/departure flags, not a sequence of locations.

Only the matched place's label and at most two note texts/statuses enter both
existing AI branches as `place_context`. Saved anchors never enter the prompt or
API. Separate approximate-location sharing remains an independent opt-in: it can
send a current two-decimal position for temporary setting inference. Enabling
saved places does not turn that sharing on. New place-specific facts stay out of
general memory; old unlinked `kind=place` notes are preserved for editing but
excluded from automatic general retrieval. Derived summaries/history/vocabulary
from a recalled place are excluded when the request is outside that place;
temporary inferred intent is cleared on a place change. Explicit learner-entered
goals/notes and newly spoken words retain their separate current-context meaning.

The AI can propose at most one note from an exact current-text quote when the
learner is explicitly confirmed, or estimated with high confidence. Proposals
are possible until confirmed in Settings; future destinations, other people's
places, sensitive traits and raw sensor inference are prohibited. A semantic
mistake remains possible, hence visible edit/confirm/forget controls. Unknown or
moving position never authorizes a save. Forget, pause or switching learners
invalidates in-flight tickets, preventing late writes from restoring forgotten data.
`Forget all saved places` clears anchors/notes and disables place location. The
broader `Forget personal memory & pause` also clears saved places. Original
transcripts/lessons remain in Saved until separately deleted. Place context and
current coordinates are omitted from saved lesson-request snapshots.

## Memory that builds across conversations

The earlier app had scene history and manual notes; web 1.7 adds **durable personal
memory** for activities, broad places and preferences. This is personalized context
retrieval, **not model weight fine-tuning**. It stays in the active learner's local
profile. New conversation and scene expiry retain it; a new profile starts empty.

The existing source-understanding call can propose at most two short memories.
Each must cite an exact substring of the current utterance. Speaker estimates must
be medium/high and point to the learner; otherwise nothing is learned. Proposals
from inferred speech remain **possible**, with a count of distinct observations
and scenes. Repetition improves retrieval relevance but never confirms a fact.
Other people's statements, AI suggestions, GPS points and sound are not durable
learner facts. Prompts exclude sensitive personal traits, precise addresses and
credentials; local checks also reject recognizable credentials/contact details and
coordinates. This is not a guarantee of semantic extraction accuracy.

Settings → **What LingoLive remembers** shows the text, source evidence, date and
status. Edit/confirm an item, add a useful broad named place or preference, forget
an item or forget all and pause learning. A typed phrase can be explicitly marked
as the learner's own words before submission; the checkbox resets after each
phrase. “These are my words” also confirms an already understood utterance without
another AI call. Speaker attribution alone is still an estimate unless confirmed.

At most 60 items are retained. Up to five short items (160 characters each) go to
both existing parallel branches. Retrieval ranks textual/setting relevance,
confirmation, recency and distinct scenes; it does not require an extra embedding
or model call. When the language differs, a bounded recent fallback lets Gemini
judge relevance. A current explicit setting limits unrelated memories; goals and
current statements override old routines. A possible commute is context for a
clarifying suggestion, not proof of today's destination. Newly extracted memory
helps the next turn; the reply branch does not wait for extraction.

One-off plans expire after one day, possible routines after 30 days, and confirmed
routines after 180 days since their update. Expired items are excluded when read.
Forgetting a topic blocks its automatic re-learning while retained in a bounded
120-topic suppression list. Clear-all empties that list, removes items and pauses
learning until re-enabled. An epoch guard prevents an in-flight response from
undoing a forget, correction or pause. There is no re-processing of old history.

Forgetting personal memory does **not** delete the original saved conversation or
manual notes. Those have separate controls. Recent conversation can still contain
what was said; start a new conversation to reset it. Copied personal-memory payloads
are excluded from saved lesson-context snapshots, so deleting a memory does not
leave an additional copy of that payload in every lesson. Browser site-data
clearing removes all local data. Storage requires a browser permitting persistence.

## Storage and lifetime

| Memory | Where / lifetime |
| --- | --- |
| Activities, broad places, preferences | LocalStorage per learner, 60 items; one-off 1 day / possible routine 30 days / confirmed routine 180 days |
| Learner name and editable notes (800 characters) | LocalStorage, separate per local profile |
| Transcripts, lessons and vocabulary | IndexedDB, separate per profile; delete in Saved |
| Explicit goal and inferred intent | Local conversation state; a scene expires after 90 minutes of inactivity |
| Earlier turns | At most eight, 400 characters each; older than 90 minutes excluded |
| Scene summary | At most 600 characters; temporary model inference |
| Saved place anchors and notes | LocalStorage, max 5 places / 3 notes; rounded 3-decimal area, expires after 90 days; separate opt-in |
| Optional approximate location | RAM only, two decimal coordinates, accuracy at least 1 km; expires after five minutes |
| Optional recent sound | RAM only, at most four seconds of mono 16 kHz PCM WAV; never saved in history |

New conversation resets scene history and goals sent to Google while retaining
saved lessons and durable personal memory. Switching profiles stops capture and sensor sharing. Late speech
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
suggestions, learner notes and up to five general personal memories and two matched-place notes. There is no third summarization or classification
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
