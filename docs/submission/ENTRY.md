# LingoLive — AI Builder Cup submission

Team: **CreativeEngine**. Leader: **Ashish T. Vasant**. Member: **Janhvi Singh**.

Project: **LingoLive — Understand. Reply. Keep going.**

Theme: **Sustainability & Social Impact**. Category: **Accessibility**.

## Brief description

LingoLive is a mobile-friendly conversation assistant for immigrants, interstate migrants and newcomers navigating an unfamiliar language. It hears the other person's speech, explains the meaning in the user's familiar language and offers three context-appropriate replies with pronunciation. Users can express their own intention in a familiar language and receive a way to say it locally. Plans prepared before leaving, recent turns, editable personal memory and location-linked notes keep replies relevant. Saved-place notes are recalled only after a fresh stationary return nearby. Forgiving readback handling keeps the learner's repeated reply in context. Afterwards, saved conversations support word meanings and personal language practice.

Google AI powers the interactive pipeline: Gemini 3.5 Transcribe Live streams speech as it happens, while two parallel Gemini 3.1 Flash-Lite calls generate source understanding and useful replies. Compact structured output, bounded memory retrieval, warm HTTP connections and local reuse reduce latency and cost. An earlier ten-lesson warm hosted run averaged 1.79 seconds; a later four-case task-flow check averaged 2.065 seconds.

Cloud Run hosts the web app, FastAPI API and authenticated WebSocket relay. Vertex AI uses a runtime service account. Firebase Authentication enables access with any verified Google account, and users can also connect a personal Google model key. Secret Manager holds the private session-signing secret. Private Cloud Storage persists atomic daily usage counters. Browser IndexedDB and local learner profiles retain saved learning, plans and editable memories, including geographically guarded place notes.

Theme: Sustainability & Social Impact. Category: Accessibility. Migrant associations, NGOs, universities, employers and relocation teams anywhere can sponsor learners. Estimated operation is about US$5 per active learner per month (₹450 at a planning rate of ₹90/US$), assuming ten listening minutes and 20 new reply turns on 20 days each month, with infrastructure shared across 100 learners. The estimate includes contingency. Detailed token assumptions, cost arithmetic and the separate combined hosted-demo budget are included in the technical PDF.

## Links and attachments

- Deployed prototype: https://lingolive-358650584819.us-central1.run.app
- Source repository: https://github.com/U4AR/LingoLive
- All materials: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/index.html
- Official-template pitch PDF: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/LingoLive-Pitch-Deck.pdf
- Editable pitch: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/LingoLive-Pitch-Deck.pptx
- Technical write-up: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/LingoLive-Writeup.pdf
- 3–4-minute functional demo: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/LingoLive-Demo.mp4
- Downloadable video: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/LingoLive-Demo-download.mp4
- Complete downloadable submission: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/LingoLive-Submission.zip

## Prototype access

Sign in with any verified Google account, select familiar and learning languages, and use the large microphone button. A personal Google model key is optional. The shared daily demo pool is 20 listening minutes and 100 two-branch lessons, resetting at midnight IST.
