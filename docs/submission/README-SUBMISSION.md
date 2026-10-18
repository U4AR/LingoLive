# LingoLive — submission files and judge guide

Team: CreativeEngine — Ashish T. Vasant (leader), Janhvi Singh.
Category: Accessibility. Theme: Sustainability & Social Impact.

1. Open https://lingolive-358650584819.us-central1.run.app on mobile or desktop.
   Complete/skip the first-use tutorial. Sign in with Google; no passcode is needed.
   The existing consent project may be called LocateAssist. Your own Google key is optional.
2. Choose English / Kannada. Optionally save a plan before leaving: take a cab
   to Bengaluru railway station; stop for tea if there is time.
3. Tap the large microphone button and allow microphone access. Ask a Kannada
   question, or type one via the optional text input. Choose/read a useful reply.
   A recognized full/partial readback stays as your turn without new reply cards.
   Correct who spoke if needed. New speech from the other person gets new replies.
4. Afterwards, open Saved, choose the phrase and tap words for meanings. Place
   memory needs explicit opt-in and guarded return matching; the film discloses
   simulated microphone/location/time and genuine ASR limitations.

Required pitch: LingoLive-Pitch-Deck.pdf, built from the supplied official PPTX.
Editable source: LingoLive-Pitch-Deck.pptx. Details: LingoLive-Writeup.pdf.
Form text: ENTRY.md and BRIEF-DESCRIPTION.txt.
Current video: LingoLive-Demo.mp4 (approximately 3:17), plus SRT/VTT.
Source snapshot: LingoLive-web-source.zip; history audit: source-secret-audit.json.
Complete bundle: LingoLive-Submission.zip; checksums: SHA256SUMS.txt.

Firebase Authentication provides Google sign-in. Cloud Run hosts the app and AI relay; Gemini handles live speech and two parallel lesson branches. Private Cloud Storage persists shared daily counters. IndexedDB and local learner profiles retain saved exchanges, plans, personal facts and location-linked memory. Saved-place notes are retrieved after a fresh stationary return near the rounded saved area.

The shared daily demo pool is 20 listening minutes and 100 two-branch lessons across visitors, resetting at midnight IST. The technical PDF includes an estimated US$5 per active learner per month, explicit token assumptions and a separate combined hosted-demo budget.

Public source: https://github.com/U4AR/LingoLive
Current materials: https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/index.html

For a YouTube submission, upload the provided 3:17 MP4 as a public video and enter its YouTube URL in the portal. Keep the prototype and source available during evaluation.
