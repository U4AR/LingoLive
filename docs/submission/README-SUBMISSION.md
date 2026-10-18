# LingoLive — submission files and judge guide

Team: CreativeEngine — Ashish T. Vasant (leader), Janhvi Singh.
Category: Education. Theme: Media, Content & Digital Experiences.

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

Firebase Authentication provides Google sign-in. Firestore is not used; learning/memory is local to the browser.
Cloud Run hosts the app/relay; Gemini handles speech and two parallel lesson
branches. Google-sign-in and bring-your-own-key usage share durable daily limits. Cookies store opaque
sessions, not keys; personal keys live in server RAM for at most an hour.

The source repository must remain publicly accessible throughout evaluation.
Public GitHub visibility was verified on October 18, 2026; keep it public throughout evaluation.
The public source ZIP is a downloadable snapshot, not a substitute for the required
public GitHub repository. If the portal requires a specific video service, upload
the MP4 to that accepted host. Final portal entry, declarations and receipt are
not completed by preparing these materials. Do not upload any access credential.

The shared daily allowance is 20 listening minutes and 100 parallel lessons across all visitors, resetting at midnight IST. It survives restarts; it is not a hard currency cap for all Google Cloud charges.
