# Archived web 1.5 demonstration

The app now uses a reply-first/live and learn-later/Saved flow. The revised
Bengaluru/Kannada transcript is in [DEMO-TRANSCRIPT-V2.md](DEMO-TRANSCRIPT-V2.md),
awaiting approval. The video linked below is the earlier version; it has not been
relabelled or replaced as v2.

[Watch the demo and download all materials](https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/index.html).
The final MP4 is **2 minutes 53 seconds**, H.264/AAC at 1280×720, approximately
3.8 MB. A four-page write-up and eight-page proposal accompany the video.

The final video is an English-narrated, captioned demonstration of the deployed
LingoLive web application, designed to remain under the FAQ's three-minute limit.
Exact duration, checksum, codec and decode results are in
`validation/submission-demo.json`; final public artifact URLs are in
`validation/submission-publication.json`.

## What is shown

1. The learner problem and the first-use tutorial. The tutorial example is
   prepared and labelled; it makes no Google inference request.
2. A fresh Japanese lesson from the real deployed Google service, including
   translations, three replies and source/reply word meanings.
3. Original-script/pronunciation switching and word bubbles using stored data.
4. A follow-up Japanese question with a stated takeaway goal, recent history and
   editable learner notes sent into the live lesson request.
5. Searching/reopening saved learning and resetting a conversation scene.
6. Synthesized English speech sent through Chromium's actual microphone
   AudioWorklet to deployed Google transcription, followed by a live lesson
   with Hindi explanations. This is not a physical-microphone recording.
7. Host-code/BYOK choices, architecture, previous measured performance and limits.

The live source/lesson APIs are not intercepted or replaced. The recorder checks
the exact source, every required definition/reading, three replies, successful
responses and absence of browser page errors. Chapter cards explain the design;
they are not presented as app screens. The video is edited into chapters at
recorded speed. It is not a new latency benchmark, and does not claim real-world
speaker-identification or learning accuracy.

## Audio and credentials

Narration and the spoken English input are generated locally using Piper and
`rhasspy/piper-voices`'s `en_US-ljspeech-high` voice. Its model card identifies
the LJ Speech dataset as public domain:
https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD.
The ONNX bytes were SHA-256 checked against Hugging Face's LFS metadata before
use. There is no impersonated speaker. The script, voice source and synthetic
input are disclosed; the voice/model binary is not included in the app/repository.

The recorder obtains the host code from Secret Manager using the normal existing
Cloud SDK login. The code enters the recorder through stdin, stays in RAM and is
used in an off-screen API sign-in. No real key/code is typed on the recorded screen.
There is no HAR, Playwright trace, cookie export or stored browser profile. The
recorded connection dialog has empty credential fields. No credentials belong
in a public video or submission document.

## Reproduce deliberately

Recording uses at most three lesson attempts (six parallel generation requests)
and one short Google speech stream. This is opt-in and may incur small model
charges. Failed UI setup attempts before a lesson was sent are not live model
tests. Rendering/narration use local CPU only and do not change the deployed app.

With the existing Playwright/Chromium, ffmpeg/ffprobe, optional Piper tooling,
verified matching voice/config files and authorized Cloud SDK access:

```bash
python tools/narrate_submission_demo.py --model /path/to/en_US-ljspeech-high.onnx
backend/.venv/bin/python tools/record_submission_demo.py --run-live
python tools/render_submission_video.py
```

Use a Python environment containing Piper for the first command; it is optional
video tooling, not a production dependency. Default working files are under
`/tmp/lingolive-submission`. `--output` overrides that path. The recorder reuses
system ffmpeg in an isolated temporary Playwright cache. HTTPS verification stays
enabled; the recording browser must trust the environment's legitimate proxy CA.
Model calls are never retried automatically by the app. Do not repeat successful
recordings to manufacture better latency results.

## Hackathon video-host requirement

The public Google Cloud MP4/preview links are available for viewing and download.
The official event specifies **YouTube, Vimeo or public Google Drive** for the
video link. This workspace does not have upload authorization for those accounts;
its existing Google Cloud credential was checked and lacks Drive access.
Upload the provided MP4 to one of those services, enable public viewing and use
that approved host URL in the registered dashboard. A Cloud Storage preview is
not represented as a Google Drive or YouTube upload.

The submission status remains prepared until the registered dashboard reports a
receipt. Account eligibility and team membership are not attested by this video.
