# Web 1.7 — Durable personal memory

- **99 backend tests and 75 Chromium checks pass**, plus the core/context and
  personal-memory JavaScript suites. Twelve new browser checks cover automatic
  provisional memory, cross-conversation retrieval with no goal/history, editing,
  confirmation, reload, broad places, learner isolation, in-flight forgetting,
  pause/re-enable and keeping copied memory out of saved request snapshots.
- Real Gemini on the staged revision learned a grounded weekday commute from an
  explicitly learner-authored typed statement. It appeared as Possible, was
  confirmed in the UI without another generation, then guided Kannada replies in
  a new conversation with a blank goal and no previous turns. Both existing
  branches still share the context: **no third AI call**.
- The two functional requests took **2.040 s and 7.604 s**. A small interleaved
  repeat check took **1.989 / 2.029 s with memory** (mean 2.009 s) and
  **1.933 / 1.567 s without memory** (mean 1.750 s). All six requests succeeded.
  These are small warm-path functional samples, not a new ten-request benchmark,
  evidence of causality or a promise of sub-two-second mobile speech responses.
  The slow result is retained; older latency evidence below predates this prompt.
- Cloud metadata/health, eleven exact shell assets, authentication, revision
  routing and unchanged model/resource budgets are recorded in
  `cloud-current-deployment.json` and `cloud-v1.7-staged-deployment.json`.
- `cloud-v1.7-api-results.json` and `cloud-v1.7-memory-timings.json` contain real
  Google results. `web-personal-memory-results.json` uses explicit local Google
  fixtures. No new audio/video was generated; physical-device/noisy capture was
  not retested on this version. The realistic Kannada demo awaits script approval.
- Memory adapts prompts and retrieval, not model weights. Local profiles are
  separate browser data stores, not private authentication accounts or cloud sync.
  Approximate sensor coordinates/audio remain temporary and are not durable facts.

## Earlier web 1.6 evidence (historical)

### Web 1.6 — Reply now. Learn later.

- **93 backend tests and 63 Chromium checks pass**, plus JavaScript core/context
  checks. The six new browser checks verify no word-teaching controls in live
  Conversation, three replies with translation/pronunciation/copy, unchanged heard
  text, a separate Saved review, independent reading choices, no extra model
  request on review, offline reload/deletion and the labelled Kannada example.
  Settings are reachable from a saved review. Existing auth, profile/sensor memory,
  context, personal-key, microphone/flush and tutorial coverage is retained.
- The three-step tutorial introduces conversation replies before later learning.
  The prepared Kannada review is public, labelled and never inserted into history.
  Complete lesson data is still generated with the existing two parallel calls;
  changing when teaching is shown adds no inference request or new service.
- **Real staged Kannada check passed** on `lingolive-00012-xot`: the source
  “ಎಲ್ಲಿಗೆ ಹೋಗಬೇಕು?” stayed exact; all required definitions/readings and three
  replies were complete; replies reflected the explicit Indiranagar metro goal.
  The live view contained zero word buttons/teaching explanations. Saved word
  review worked without another model request. One HTTP sample took **2.241 s**;
  this is not a new average or an under-two-second guarantee.
- The tested revision was promoted to **100% public traffic**. Ten public assets,
  including the Kannada example, health 1.6, model settings, usage/resource guards,
  unauthorized HTTP rejection and tag removal were verified. Source runtime commit
  is `0bad942c6d13cef4c1b239a8a16a6ada168df7ca`.
- The real speech stream was previously verified on web 1.5; no new live Google
  speech test, physical-microphone test, valid personal-key inference or fresh
  multilingual latency benchmark is claimed for this UI update. The original
  inference pipeline, auth and cost limits remain unchanged.
- **New media is pending transcript approval.** The v2 script uses Bengaluru and
  Kannada for immigrants/interstate newcomers: useful replies during a commute
  or tea order, word learning afterwards at home. No v2 audio/voices, footage or
  video were generated. The old 2:53 video remains an archived 1.5 sample.

Evidence: `cloud-current-deployment.json`, `cloud-current-api-results.json`,
`cloud-v1.6-api-results.json`, `web-reply-flow-results.json`, all previous browser
result files, and `web-replies-*-cloud.png` in `validation/`. The prior 1.5 runtime
and API reports are archived as `cloud-v1.5-deployment.json` / `cloud-v1.5-api-results.json`.

---

# Historical web 1.5 evidence — October 17, 2026

- **93 backend tests pass** (previous 80 plus 13 parallel/format/usage checks).
  Tests prove both branches overlap, exact Unicode/spacing survives compact word
  expansion, missing/reordered/undefined words fail, all three replies are complete,
  optional audio goes only to the source branch, and context is passed to both.
  They cover both provider credentials, minimal Lite thinking, connection reuse
  and shutdown, cancellation without retry, combined token caps, weighted rate/hour
  accounting and independent host/personal allowances. Google is mocked locally.
- **57 real Chromium checks pass**, plus pure JavaScript core/context checks:
  13 baseline, 5 optional Google auth, 8 context, 12 learner memory/sensors,
  4 minimal UI, 8 personal-key and 7 tutorial checks. Google/audio/location use
  explicit fixtures. A sign-out assertion now waits for completion before checking
  access; it previously raced the asynchronous disconnect operation.
- **Live:** `lingolive-00010-naj`, 100% traffic, Gemini 3.1 Flash-Lite minimal
  thinking, two parallel generation calls per lesson. A staged real Google speech,
  context/audio, exact-source/readings/meanings, cookie and invalid-key/no-host-
  fallback check passed. After promotion the primary URL's health and all nine
  web assets matched the tested source; the temporary verification tag was removed.
- **Ten complete hosted lessons succeeded, zero failures, mean 1.79 seconds**.
  Six short Japanese/Hindi/Spanish calls averaged 1.75 seconds. Two simultaneous
  sessions completed in 1.65 and 1.71 seconds. The separate staged functional
  context/audio lesson took 2.34 seconds; including it gives 1.84 seconds for 11.
  This meets the two-second lesson average in this small warm-path sample.
- **Entire speech pipeline remains longer:** the synthesized 2.128-second WAV
  reached a complete contextual lesson 3.54 seconds after the last audio frame,
  including 1.11 seconds of test-client handoff. Physical phone, cold starts,
  broad semantic accuracy and valid personal-key inference remain unverified.
- The same-model comparison found merely splitting the full Gemini 3.8 response
  did not improve reliability of latency (6.71 seconds single vs 9.55 parallel,
  three prepared cases each). Compact 3.8 parallel took 3.61 seconds. The final
  design combines parallel calls, compact fields, shorter replies, HTTP reuse and
  the faster Lite model. Failed/slow experiments are retained, not discarded.
- Existing raw call caps remain 24/minute, 360/hour, 400/day. Two units per
  parallel lesson mean 12/180/200 lessons; total output cap remains 4,096 tokens.
  Existing minimum-zero/maximum-one instance, 512 MiB/one CPU, authenticated AI,
  separate key billing, emergency pause, audio and concurrency guards remain.
  No automatic retries or always-warm instance were added.
- Operator deployment used the normal persistent Cloud SDK login and refreshed
  credentials; no copied hourly token was requested. SDK secrets remain outside Git.

Current runtime source: `a0a91d9e9cd8b236edf31f2286c864c6b4e4f509`.
Current evidence: `validation/cloud-current-*.json`, `cloud-parallel-latency-results.json`,
`web-backend-tests.txt`, and `web-*-results.json`. Compare timings and caveats in
[docs/LATENCY.md](docs/LATENCY.md). The old 1.4 measurement is retained in
`cloud-latency-results.json`. Production lesson/saved format and Android binary
remain compatible; the browser's artificial 2.5-second queue wait was removed.

---

# Historical web 1.4 evidence — October 17, 2026

- **80 backend tests pass**, including six tests for the bounded Gemini 3.8
  response: both providers make exactly one call for a complete lesson, all
  readings/meanings are retained, malformed/missing/source-changing words
  fail validation, exact punctuation is retained, and truncated output
  makes no automatic second paid call. Both provider requests use `thinkingLevel:
  low` and the existing 4,096-token cap.
- **57 real Chromium checks pass**: 13 baseline, 5 optional Google auth, 8
  conversation context, 12 learner memory/sensors, 4 minimal UI, 8 personal-key
  flows and 7 first-use tutorial checks. Tests use mocked Google responses and
  synthetic microphone/location fixtures. The tutorial tests cover language
  validation/persistence, interactive meaning/transliteration, skip/completion,
  reload, replay, Escape, collapsed history, mobile fit, and zero paid/sensor calls.
- Pure JS source/word/PCM/context checks pass. Screenshots show the actual new UI.
- Google documents `gemini-3.8-flash` as stable and supports **low**, medium and
  high reasoning. Minimal is explicitly unsupported. Checked official pages:
  https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash and
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash.
- **Deployed and live-inference verified:** revision `lingolive-00008-cos`
  serves web 1.4 with 100% traffic. A staged check verified real Transcribe Live,
  the same optional-audio/context lesson through Gemini 3.8, all source/reply
  readings and meanings, private-code auth, personal-key sessions, invalid-key
  no-fallback behavior, cookie revocation and the unchanged cost guards. Public
  health and nine HTML/script/style assets were rechecked after promotion.
- The hosted optional-audio/context lesson took **14.2 seconds** in one sample;
  a separate Japanese text preflight took **5.37 seconds**. These differ in
  context, language direction and audio input; they are not a benchmark or proof
  of a general speedup. Physical-phone capture and valid personal-key inference
  remain unverified.
- **Latest live latency sample:** ten successful calls, zero model/validation
  failures on revision `lingolive-00008-cos`. Two sequential samples per language:
  Japanese median 6.55 s (5.36–7.74), Hindi 11.63 s (8.58–14.67), Spanish 8.54 s
  (6.90–10.18). Two simultaneous sessions completed in 4.69 s and 8.36 s.
  A 2.128-second synthesized utterance reached a complete lesson 8.40 s after
  the last audio frame (11.33 s including socket setup and speaking). The same
  transcript/context took 6.96 s without an audio attachment and 19.18 s with it.
  No cold-start or physical-phone latency claim. See `docs/LATENCY.md` and
  `validation/cloud-latency-results.json`; small samples do not establish percentiles.
- **Persistent operator login verified:** Cloud SDK saved a refresh credential,
  successfully completed a refresh exchange, and deployed without a manually
  copied access token. Private SDK configuration is outside this repository.
  The Cloud Run runtime continues to use its own dedicated service account.

The first 1.4 publication failed a live lesson check and was rolled back while
fixing model output. The corrected revision was verified through a temporary
revision tag before promotion; that tag was removed afterward. Evidence is
`validation/cloud-current-*.json`, `cloud-3.8-preflight.json` and
`cloud-auth-status.json`. Previous v1.3 records are archived as
`cloud-v1.3-deployment.json` and `cloud-v1.3-api-results.json`.

Live tests exposed unreliable readings and omitted meanings with abbreviated
word fields. The final request uses explicit `text/reading/meaning/note/is_word`
fields, all required, with bounded readings and brief notes. Words already using
Latin script reuse their original text as their reading. Non-Latin readings must
remain present, short and defined. Strict source/definition validation and the
4,096-token cap remain. No automatic second paid model call is made.
Transcription is a separate live service; all lesson work is one Flash request.
The UI pronunciation toggle, word bubbles and tutorial need no extra model call.
Authentication, key isolation, memory, optional signals and cost guards remain.

---

# Web 1.3 deployment evidence — October 17, 2026

The source now supports either the host access code or a learner's Google AI
Studio key, including transcription and replies. Personal-key calls use their
own Gemini provider and never fall back to host Vertex/API credentials.

- **74 backend tests pass**, including 12 new personal-key/transport checks:
  session auth/origin/credential bounds, no credential echo in validation errors,
  isolated clients/providers, no-host setup, failed-key no-fallback behavior,
  separate host/personal quotas across re-login, real relay PCM path and model
  selection, logout/copy-cookie revocation and active stream closure, expiry,
  tampering/restart/replacement, emergency pause and disabled-key mode. Google
  HTTP/WebSocket transport credentials are checked using explicit mocks.
- **50 browser checks**: 13 baseline, 5 optional Google auth, 8 context, 12 learner
  memory/sensors, 4 simple UI and 8 personal-key flows. Google responses are
  fixtures; Chromium captures synthetic microphone audio. Key-mode tests cover
  selection, field clearing, HttpOnly sessions, key-free local storage/lessons,
  reload, actual AudioWorklet relay/transcription, switching to host code and
  disconnect without losing history.
- Pure JS source/word/PCM/context tests pass. UI evidence includes
  `web-personal-key.png`, `web-simple-mobile.png` and `web-word-bubble.png`.

**Deployed:** revision `lingolive-00005-lch` serves web 1.3 with 100% traffic.
The eight checked hosted HTML/JS/CSS assets match the committed source. Health
reports version 1.3, configured and personal keys available. Both connection
choices are exposed; Google sign-in remains disabled. Private-code cookies are
Secure/HttpOnly/SameSite; unauthenticated HTTP and WebSocket AI routes are blocked.

A **real hosted Google check** streamed the existing 2.128-second synthesized
reference WAV to Transcribe Live and received “John chapter 3 verse 16”. That
transcript, a blank goal, earlier user context, previous suggestion and the WAV
clip were sent through hosted Flash. The lesson preserved the exact source,
returned three replies and included context/speaker fields. No Google response
was mocked for this hosted check. It demonstrates the pipeline, not broad
speaker-identification or language-learning accuracy.

A personal-key session was created and an explicitly invalid test key failed
safely without producing a host lesson. Sign-out invalidated the copied key
cookie. **Valid personal-key inference and physical-phone capture remain
unverified.** The current container was built in Cloud Build; the Android APK
was unchanged. The runtime keeps the same one-instance, scale-to-zero, CPU/memory,
concurrency and model budgets; no Google API key is bound to the host service.
Evidence: `cloud-current-deployment.json`, `cloud-current-api-results.json` and
`cloud-deploy.txt` in `validation/`. No deployment/access secret is recorded.

Source is in the independent repository https://github.com/U4AR/LingoLive.
The user created the repository; GitHub reported it as private at upload time.
The complete local history was scanned for credential patterns and private files;
only explicit dummy test credentials were found and reviewed. The original
repository remains unchanged at `b059f0b2f65df02a0d1a5b03a8cabd1ae57e43cb`. No real credentials or
signing keys are bundled. See `MEMORY.md` for session/storage/cost limitations.

---

# LingoLive 1.0 — October 16, 2026

The non-debuggable universal Android APK builds successfully for Android 8/API 26+.
Its signature and 16 KB APK alignment were checked. The release includes the local
Google ML Kit language identifier, schema, teaching prompt and a labeled example;
it contains no configured Google key, backend token or hosted endpoint.

- **10 JVM checks passed**, with zero errors/failures/skips: exact source/reply
  coverage, every lexical word's definition, transliteration spacing, Unicode/RTL
  clickable ranges, missing replies, language aliases/thresholds, interim/final
  protocol separation, dedicated automatic-language transcription setup, and HTTPS
  backend origin validation.
- **11 Python backend checks passed**: runtime setup status, authentication before
  model calls, request validation, exact word coverage, rate limits, authenticated
  WebSocket relay/PCM validation, server control of the transcription model, rolling
  limits, actual Google Flash HTTP request shape, thought filtering, safe upstream
  errors and rejection of truncated lessons. Upstream Google responses were mocked.
- **7 Android checks passed** on an Android 11/API 30 x86_64 software emulator in
  106.201 seconds: offline example and word dialog; real bundled Google language
  identification; encrypted/retained credentials and language settings; local
  lesson/reply/vocabulary persistence, idempotent saves and deletion; retry after
  HTTP 429; a regression for delayed language identification after an explicit
  lesson; and the full microphone-source → Transcribe WebSocket → local language
  detection → Flash HTTP → visible lesson → SQLite pipeline. The pipeline uses
  test PCM and explicit mock Google servers, not real speech recognition. It also
  verifies final text after background/stop, no automatic teaching of familiar
  English speech, tappable reply pronunciation and a fixed visible listening control.
- The actual local Uvicorn service returned HTTP 200 from `/health` with
  `configured:false` and HTTP 503 for protected requests without runtime secrets.
  Both shell deployment/key-generation helpers passed `bash -n`.

The first Android network tests exposed the cloud emulator's inherited proxy
routing localhost fixture traffic to its outbound proxy. Explicit no-proxy clients
are used only for the in-process mock servers. Production clients retain normal
proxy behavior and TLS verification. The tests also caught missing WebSocket close
acknowledgement; both the production listener and fixture now complete the handshake.
No app ANR or failed assertion was dismissed/disabled to obtain the final result.

Evidence is in `validation/jvm/`, `backend-tests.txt`, `android-tests.txt`,
`backend-health.json`, `apk-signature.txt`, `apk-permissions.txt`, `apk-badging.txt`,
`example.png` and `live-lesson.png`. The screenshots show the app itself and the
tested example/mock flow. Publication verifies signed-APK bytes and all uploaded
GitHub artifact hashes and records `build-verification.json`/`release-verification.json`.

The Google endpoint/model choices were checked against current official API docs.
**Live Google Transcribe/Flash inference, actual phone microphone input, accents,
physical-device latency and a deployed Cloud Run service are not verified.** Keys
are intentionally left for on-device/server setup later, as requested. The included
deployment script has not created paid Google Cloud resources. A successful local
health request or mocked pipeline is not a claim of live Google account access.

# LingoLive web 1.1 — October 17, 2026

The browser interface and Google relay are served from one FastAPI application.
The Android application source and existing APK were not changed for this addition.

- **19 backend checks passed**, including the original 11 Google/API regression
  checks plus eight web checks: complete public shell/assets without credentials,
  opaque HttpOnly sessions, sign-in/sign-out, invalid codes, cookie expiry/tampering,
  same-origin cookie writes and WebSockets, Secure cookies on cloud hosts, and
  bounded sign-in attempts. Android bearer authentication remains supported.
- **13 real Chromium browser checks passed**, with no JavaScript page errors:
  desktop layout and all 83 language choices; prepared example and tappable source/
  reply words in both scripts with no fake history; rejected access code and cookie
  properties; typed text through the real local backend to a complete lesson;
  IndexedDB and session persistence; offline reload/history/example without API or
  credential caching; retained transcript and retry after HTTP 429; actual browser
  AudioWorklet PCM through an authenticated WebSocket to the relay/lesson UI;
  final text after Stop; Saved stopping capture and local deletion; disconnect;
  mobile layout and fixed visible listening control; actual browser microphone
  denial/recovery; and clear-history persistence. The fixtures intentionally use
  synthetic Chromium microphone audio and mocked Google transcription/lessons.
- Web core assertions passed for exact original-source conservation, complete
  lexical definitions and replies, pronunciation spacing, language aliases, 16/44.1/
  48 kHz resampling to exactly 16,000 samples/second, PCM clipping/scaling and partial
  frames. One least-significant PCM bit of floating-point rounding is allowed.
- The **production Dockerfile built successfully** and its unprivileged `appuser`
  container served the real website, current JavaScript and prepared example in
  Chromium. `/health` returned HTTP 200, version `1.1`, `configured:false`;
  the live API correctly returned 503 without runtime secrets. Source ownership was
  fixed so the non-root container can read files copied from this restricted
  workspace. The Cloud Run deployment helper passes `bash -n`.

The environment's Docker daemon initially lacked the provided proxy hostname and
CA trust. Local build verification passed the existing proxy route and mounted
its existing trusted CA bundle via an optional BuildKit secret. TLS verification
was retained; the CA secret is not copied into the image. Cloud builds on standard
Google networking do not need this development-only trust input.

Browser tests initially exposed test timing assumptions around asynchronously
flushed speech and IndexedDB deletion. Checks now wait for the actual relevant
state instead of assuming no speech can arrive after Stop. The permission-denial
check uses a separate browser without the fake automatic permission-grant flag.
The final microphone code also binds each socket to its own language pair so a
late final transcript cannot inherit a newly selected pair, and handles capture
cancellation without closing a subsequent session's audio context.

Evidence: `validation/web-backend-tests.txt`, `web-browser-tests.txt`,
`web-browser-results.json`, `web-core-tests.txt`, `web-container-build.txt`,
`web-container-check.json`, and desktop/mobile/example/listening/container PNGs.

**No live Google inference, physical microphone, Safari/iOS capture, public Cloud
Run deployment or hackathon eligibility has been verified.** Google credentials
remain intentionally unbundled. Deployment needs the user's selected project,
authorized Cloud credentials and Secret Manager setup. Existing local success is
not a claim that a public website or paid Google Cloud resources were created.

# Cloud Run deployment and live Google verification — October 17, 2026

LingoLive is deployed in Google Cloud project `locateassist`, region `us-central1`:
https://lingolive-358650584819.us-central1.run.app

The final configuration uses **Vertex AI and the Cloud Run runtime service
account**, with no Google API key bound to the service. The dedicated runtime has
a custom role containing only `aiplatform.endpoints.predict` and
`serviceusage.services.use`, plus access to the app's private-code secret. The
private code stays in Secret Manager. The source builder has `roles/run.builder`.
There is one maximum service instance. Existing unrelated project resources and
repository main were not changed.

**24 backend checks passed** after adding the Vertex provider: the previous 19
regressions, including a clear retryable message for AI Studio HTTP 402, plus five
Vertex checks for keyless configuration, server-controlled project/model setup,
OAuth Flash request shape, authenticated Vertex WebSocket selection, and cached
credential refresh shared by concurrent requests. The existing 13 Chromium UI/
fixture checks remain passing evidence for the unchanged frontend; they do not
represent live Google inference. The core PCM/source/word checks also passed.

Real hosted checks passed with HTTPS certificate verification enabled:

- Public `/` returned 200 and matched the local HTML byte-for-byte; `/health`
  returned `configured:true`. JavaScript assets were reachable.
- Private access-code sign-in succeeded against the deployed service.
- Japanese text sent through the deployed API produced a real Gemini 3.6 Flash
  lesson using the Cloud Run service account. Every original character was retained,
  words had definitions, and three suggested replies were returned.
- A pre-existing 2.128-second, mono 16 kHz PCM synthesized-speech fixture streamed
  through the deployed authenticated WebSocket to real Gemini 3.5 Transcribe Live.
  It transcribed **“John chapter 3 verse 16”**. That transcript then produced a real
  English-learning lesson explained in Japanese, again with exact source coverage
  and three replies. No Google responses were mocked in these hosted API checks.

The first source build encountered new-account IAM propagation. The legacy Cloud
Run source-build worker also required standard Docker instructions; the optional
local BuildKit CA mount was moved to `Dockerfile.dev`. The standard production
Dockerfile then built successfully in Cloud Build. The initially attempted Gemini
API provider returned HTTP 402 because AI Studio prepaid credits were depleted,
even though Cloud billing was enabled. Real Vertex Flash and live-transcription
probes succeeded using Cloud billing, so the final deployment uses Vertex and no
AI Studio prepayment is needed for this provider.

Hosted Chromium automation could not navigate through this environment's TLS
inspection proxy because Chromium lacks the environment CA. Automatic approval
review rejected adding a CA to Chromium's persistent trust store because that
would broaden future HTTPS trust without explicit authorization. The trust store
was left unchanged. The deployed HTTPS API tests used the existing system trust
bundle and passed without disabling certificate verification. No hosted-browser
pass is claimed; the earlier local browser UI checks are distinct evidence.

Physical phone microphone input, Safari/iOS capture and real-world latency remain
unverified. Public multi-user production still needs per-user auth and quotas;
this is a private-access-code hackathon prototype. Deployment and live tests use
billable Google Cloud services.

Evidence: `validation/cloud-deployment.json`, `cloud-public-check.json`,
`cloud-api-results.json`, `cloud-vertex-probe.json`, `cloud-vertex-audio-probe.json`,
`cloud-deploy.txt`, `web-backend-tests.txt` and the earlier `web-browser-results.json`.


## Private-demo cost guards (October 17, 2026)

**34 backend tests passed**, including ten guard regressions: pause blocks both
paid routes before Google; hourly lesson and daily audio budgets block upstream
access; fast PCM and oversized chunked HTTP bodies are rejected; two active
listeners can renew while old final transcripts drain; rolling daily budgets
survive hourly rollover; configuration reads the runtime limits. A fake clock
verified fifteen minutes of correctly paced audio and the reservation/refund math
for two simultaneous fifteen-minute listeners. This was simulated duration, not
a thirty-minute paid microphone soak test. Source/PCM core tests passed.

The production defaults allow 24 lessons/minute, 360/hour, 400/day, two concurrent
lessons and two active listeners. Brief draining sockets do not accept more audio.
Audio connection time is limited to 40 combined minutes/hour and 60/day. Sign-in
cookies last one hour. Input is bounded to 1,000 characters and output to 4,096
tokens. A runtime switch pauses both paid endpoints. Cloud Run scales to zero
with one maximum instance and request-based CPU billing.

These are in-memory per-instance usage guards. Restart/redeploy resets them,
and revision transitions can briefly overlap. They are not a hard billing cap,
per-user accounts, or a production abuse defense. No dollar cost guarantee is
claimed. Physical-phone microphone/latency checks remain outstanding.

Revision `lingolive-00003-727` is serving 100% of traffic. Read-only Google Cloud
configuration checks confirmed all configured usage guards, zero minimum/one
maximum instance, request-based CPU billing and no Google API key in the service.
Real hosted HTTP and WebSocket attempts without credentials were rejected. The
short real Vertex speech-to-lesson check passed again on this guarded revision,
including the reduced output-token allowance. All 13 local Chromium UI checks
were rerun and passed after these changes. See `cloud-guards-results.json`.


## Google account allowlist update (source only; activation blocked)

**46 backend tests passed**: the previous 34 plus 12 Google sign-in regressions.
Locally generated RSA-signed tokens are checked by the actual Google auth verifier
for signature tampering, issuer, audience and expiry; test certificates are
explicit fixtures, not live Google signing keys. Tests also cover required Google
credentials, the private code, verified/invited emails, nonce mismatch/replay/
expiry, legacy cookie/bearer rejection on paid HTTP and audio, allowlist removal,
public non-secret configuration, popup CSP, certificate reuse and fail-closed
missing registration. No test called live Google account sign-in.

All 13 existing Chromium browser checks passed again. **Five additional Chromium
checks passed** with a locally mocked Google SDK and real backend RSA validation:
Google selection required before Connect, uninvited account denied without AI,
invited account plus code creates a complete lesson, reload retains secure cookie
without storing credentials, and disconnect requires signing in again while
retaining saved lessons. Evidence: `web-google-signin-browser-results.json`.

Google OAuth Web application registration is still required. Project locateassist
has no organization, the CLI's IAP OAuth creation APIs are retired, and this
workspace has no signed-in Google Console browser. The support code was then deployed as revision `lingolive-00004-jzp` with Google
sign-in deliberately disabled pending registration. One source build was used,
with no extra paid AI calls. Existing real inference evidence is from revision
`lingolive-00003-727`; the unchanged provider code has not been billed for another
model test on the new revision. First invited account is the owner's
ashish.t.vasant@gmail.com; no additional emails were supplied. New Google auth/
documentation domains were saved in the environment draft but network calls
remain blocked until those settings are applied/published.

The new hosted HTML/JS assets matched source byte-for-byte, `/v1/auth/config`
reported `google_required:false`, and private-code sign-in/session/sign-out
worked on revision `lingolive-00004-jzp`. Both paid unauthenticated routes remained
blocked. Existing model budgets and scale-to-zero/max-one settings were verified.
The owner email is configured as the sole allowlist entry, ready for activation.
Both deployment and activation CLI argument checks preserve comma-separated
emails; activation updates only account settings and missing client ID stops
before any mutation. Evidence: `web-google-signin-status.json`.

The user subsequently selected simple private-access-code sign-in and stopped
the Google activation request. The deployed `/v1/auth/config` confirmed Google
is not required and unauthenticated lesson requests remain blocked. Google
registration is no longer a blocker. Deployment defaults now retain code-only
authentication; optional Google support remains disabled.
