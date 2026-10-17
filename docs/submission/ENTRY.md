# AI Builder Cup — prepared entry

Product positioning update: help immigrants and interstate newcomers keep
conversations moving with useful live replies, then teach from Saved afterwards.
The revised Bengaluru/Kannada demonstration awaits transcript approval; the
existing video is the older 1.5 sample, not this new production.

Prepared for **Ashish T. Vasant**. Use the existing registered team; do not replace
its legal identity, membership or eligibility declarations with inferred data.

## Project name

LingoLive

## Tagline

Understand the conversation. Learn the words. Find your next reply.

## Theme and category

**Theme:** Media, Content & Digital Experiences.

**Category:** Education.

## Short description

LingoLive is a Google Cloud Run language-learning companion for real
conversations. It uses Gemini live transcription and two parallel Flash-Lite
requests to show what was said and three useful replies, with pronunciation aids.
Word meanings and practice open afterwards in Saved. Goals are optional; bounded conversation and durable personal memory help replies follow
the exchange and remember useful routines across days. Activities, broad places
and preferences remain editable; inferred memories stay provisional. Lessons stay on the browser. Users connect with a host access code
or their own Google key. Ten earlier-version measured complete lessons averaged 1.79 seconds;
speech-to-result and real-device latency remain longer or unverified.

## Problem and intended impact

Immigrants, interstate newcomers and adults working in another language often understand
part of a sentence but cannot formulate an appropriate next reply. Moving between
translation, pronunciation and notes breaks the conversation. LingoLive puts a
short lesson into that moment: understand the words, choose a context-aware
response and revisit it later. Its intended impact is more accessible everyday
language practice; measured learning-outcome claims are not yet available.

## Proposed solution and innovation

One listening button feeds Google's multilingual transcription. The app shows
the source and translation, three useful responses and tappable word meanings.
Pronunciation views and word bubbles reuse stored data without additional AI
calls. A stated goal, recent turns, prior suggestions and learner notes help
replies preserve the learner's intent; a blank goal allows tentative inference.
Confirmed speech and AI suggestions remain distinct. Optional coarse location
and four seconds of recent sound can help estimate a scene without becoming a
saved recording. The combination is delivered through a minimal responsive web UI.

## Google AI / Google Cloud implementation

FastAPI on Cloud Run serves the website, authenticated speech WebSocket and lesson
API. Gemini 3.5 Transcribe Live receives mono 16 kHz PCM. Gemini 3.1 Flash-Lite
with minimal thinking runs source understanding and reply generation concurrently.
Compact structured words are validated and expanded into exact-source lessons.
The host uses Vertex AI and a runtime service account; BYOK uses the learner's
Google AI Studio key without host fallback. Secret Manager holds the host access
code. Both branches share a 4,096-token maximum; failed work triggers no automatic
retry or third generation call.

## Feasibility, validation and scalability

The web prototype is deployed and has passed real Google speech-to-lesson checks.
There are 93 passing backend tests and 63 Chromium checks with explicit local
fixtures. Ten hosted complete lessons averaged 1.79 seconds with zero failures,
compared with 9.26 seconds in the earlier deployment; two simultaneous sessions
completed in 1.65 and 1.71 seconds. These are small warm-path samples, not mobile
or cold-start guarantees. The speech test took 3.54 seconds after the audio ended.
The current one-instance limit controls prototype costs. A wider launch needs
durable user quotas, stronger identity, cross-instance session design, device
testing and measured educational outcomes.

## Data and responsible operation

Learning history is local to browser IndexedDB, with editable local notes and
bounded recent context. Selected speech and text/context go to Google for AI.
Location/sound are opt-in and temporary. API keys stay only in expiring server
RAM; cookies contain opaque identifiers. Authentication, input/audio bounds,
model-call/audio quotas, two-listener/two-lesson concurrency and an emergency
pause protect host usage. Counters are not a hard billing cap. Model translations,
speaker estimates and suggested replies can be wrong.

## Links and attachments

- Working prototype: https://lingolive-358650584819.us-central1.run.app
- Source: https://github.com/U4AR/LingoLive
- Proposal: `LingoLive-Proposal.pdf`.
- Technical write-up: `WRITEUP.md`.
- Demo: use the verified MP4 listed in `DEMO.md`; upload it to YouTube/Vimeo
  or Google Drive with public viewing and paste that public link into the form.
- No access code, personal key or deployment token belongs in this form's public text.

## Final portal checks

1. Open the existing registered Hack2skill dashboard and confirm its team of 2–4
   and eligibility details. The public site lists an October 18 deadline without
   a verified exact cutoff/time zone.
2. Select the theme/category above; paste the appropriate prepared fields.
3. Attach the PDF and provide the prototype, public repository and approved video-host links.
4. Give judges a way to access live AI privately, or use their own supported key.
   Do not publish the host access code in the PDF, video, source or form description.
5. Check the organizer's declarations yourself, submit through the dashboard,
   and retain its receipt. A prepared bundle is not an accepted submission.
