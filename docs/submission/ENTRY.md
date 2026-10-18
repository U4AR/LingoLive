# AI Builder Cup — prepared submission

Team: **CreativeEngine**. Leader: **Ashish T. Vasant**. Member: **Janhvi Singh**.
Team names are taken from the supplied registration screenshot; eligibility and
portal declarations remain the team's responsibility.

Project: **LingoLive — Understand. Reply. Keep going.**
Theme: **Media, Content & Digital Experiences**. Category: **Education**.

## Brief description (copy into the form)

LingoLive helps immigrants and interstate newcomers respond during everyday conversations in an unfamiliar language, then learn from those exchanges afterwards. A Bengaluru newcomer can understand a Kannada cab driver, get three useful replies with pronunciation aids, and express an English intention in Kannada. A pre-task plan, recent turns and bounded editable personal memory keep replies relevant. Opt-in place notes are recalled only after a guarded return nearby. Forgiving readback detection recognizes full or partial repeated suggestions without generating another reply. Saved conversations provide word meanings and practice later.

Google AI: Gemini 3.5 Transcribe Live streams speech; two parallel Gemini 3.1 Flash-Lite requests produce source understanding and useful replies. Google Cloud Run hosts the responsive web app, FastAPI API and authenticated WebSocket relay. Vertex AI uses a runtime service account; Secret Manager holds host access configuration. Users can alternatively bring their own Google key. Authentication, model/audio quotas, bounded output and concurrency limits control prototype usage. Keys remain only in expiring server memory; cookies contain opaque session identifiers.

Firebase and Firestore are not used in this prototype. Learning history and editable memory remain in browser IndexedDB/LocalStorage. Optional cross-device synchronization is future work. The prototype demonstrates working functions; learning gains, noisy-phone speaker accuracy and a universal sub-two-second response are not claimed.

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

## Judge access and final checks

Use a personal Google AI Studio key or obtain the host access code privately
from the team. Never publish the code in source, video, deck or public form text.
Saved/demo review works without paid AI, but live speech/replies need a connection.

Keep the Cloud Run service, working AI credentials and public source available
through evaluation. GitHub visibility still reports private at this document's
last check despite the owner's public-setting confirmation; verify anonymous
access at the exact repository URL. The integration cannot change visibility.

The supplied requirement is 3–4 minutes; use the current approximately 3:17 video,
not the archived 2:22 version. The official pitch sections and branding are
preserved. If the portal requires YouTube/Vimeo/Drive, upload the MP4 there and
use the accepted host link. No accepted portal host or submission receipt is
claimed here. The registered dashboard and final declarations need the team's
signed-in portal session. Check the actual deadline/cutoff and retain the receipt.
