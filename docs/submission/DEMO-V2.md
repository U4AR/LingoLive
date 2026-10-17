# Current demonstration — LingoLive web 1.9

[Watch the current video](https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/v2.1/index.html) · [Download MP4](https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/v2.1/LingoLive-Demo-download.mp4)

The user approved the script with “Ok make it.” The new video is **2:22.021**,
H.264 1920×1080 at 25 fps, with AAC stereo, English captions, Kannada dialogue
and Indian-English narration. The learning feature appears at **1:57**, near
the end as an additional benefit. Unnecessary end-frame holds have been trimmed;
an actual speech-recognition error and its visible correction remain. Dialogue and
browser captures are not sped up.

The video opens on an illustrated communication problem faced by immigrants and
people moving between Indian states, then introduces LingoLive. Actual app
capture shows a pre-task cab/optional-tea/station plan, Kannada conversational
replies, expressing English intent in Kannada, opt-in place memory after a
simulated return, and word meanings/practice in Saved afterwards.

The corrected timeline is 0:00 problem, 0:26 solution, 0:37 plan, 0:46 cab,
1:03 own-language intent, 1:18 tea stall, 1:34 place memory, 1:57 later learning,
and 2:11 closing. The approved script retains its original planning timestamps;
these are the actual edit timings.

## Provenance and limits

- Narrator Kore, newcomer Orus, driver Charon and shopkeeper Algieba are generated
  voices from Google's `gemini-3.1-flash-tts-preview`, Vertex AI `us-central1`.
  These are preset synthetic voices, without cloning an identifiable person.
  Reference: https://cloud.google.com/text-to-speech/docs/gemini-tts.
- The opening is a generated still illustration with a slow camera move, not
  filmed actors or generated talking-head footage. The fictional characters and
  AI image are disclosed. Image source: OpenAI image generation tool.
- The corrected v2.1 soundtrack uses clean, unchanged TTS voices without an
  artificial ambience bed. The original four microphone input WAVs still include
  the disclosed synthetic noise and entered Chromium's
  actual getUserMedia MediaStream / AudioWorklet / deployed Google transcription
  path during the recorded take. The film substitutes each matching dry source
  voice at the same time; recorded input mixes remain in the media-assets ZIP.
  Narration is an editing track and is not microphone input.
- The final take made seven real lesson requests (14 parallel generation calls).
  A previous incomplete take made three lesson requests; it is retained in the
  media evidence. No Google response was mocked, replaced or pasted into the app.
- The tea-stall question was misidentified as Bengali. Its failed recognition,
  response wait and typed correction are visible. The return question used mixed
  Telugu/Kannada script but retained useful meaning. This is a prototype with
  recognition limitations, not a flawless or broad noisy-speech benchmark.
- A real source response proposed the ginger-tea place note; the UI confirmed it.
  A separate away request withheld it. A new blank-goal conversation on simulated
  return included the relevant note, without sending saved anchor coordinates.
  GPS and elapsed time are explicitly simulated; no physical location was tested.
- A separate audio-only Google check transcribed the three source questions and
  four actual selected Kannada replies. This is an automated quality check, not
  human native-speaker review. Actors speak actual selected model phrases with
  matching English meanings; wording may differ from the proposed script.
- Host-code sign-in occurred off-screen. Code/token/cookie values, traces and
  browser profiles are absent from published recordings and source materials.
  Fictional demo data is used. App authentication and cost guards are unchanged.

## Audio repair and verification

The original v2 export had a timing defect: ffmpeg's loudness filter emitted
frames without timestamps when flushing short WAVs. The subsequent delay/mix
placed several actors at the scene's beginning, leaving the visible dialogue
nearly silent (roughly -50 dBFS RMS). The overall loudness check missed this.
The opening artificial engine hum was also distracting.

V2.1 measures each voice separately, applies constant gain to a timestamped
stream, and verifies every source waveform against the decoded final MP4.
No voice synthesis or Google app/model call was repeated. All 23 expected speech
events must correlate at least 0.82 with the source and exceed -30 dBFS active
speech RMS; long pauses and peaks are checked too. The before/after reports are
retained. Real inference waits, the typed correction and original speaking speed
are preserved; only redundant holds were trimmed. No artificial ambience is
added to the corrected soundtrack.

## Reproduce deliberately

Use the approved transcript, a working Cloud Run deployment, normal Google Cloud
SDK login with access to its Secret Manager code/Vertex models, Playwright,
Chromium, ffmpeg and the pinned backend Python environment. Requests are opt-in,
small Google charges apply, and no model call is automatically retried.
The existing app and runtime service account are not changed by media tooling.

```bash
backend/.venv/bin/python tools/make_submission_audio_v2.py --run-live
backend/.venv/bin/python tools/prepare_demo_ambience_v2.py
backend/.venv/bin/python tools/record_submission_demo_v2.py --run-live
backend/.venv/bin/python tools/make_submission_audio_v2.py --run-live --replies /tmp/lingolive-video-v2/reply-lines.json
backend/.venv/bin/python tools/check_demo_voices_v2.py --run-live
node tools/render_submission_frames_v2.cjs /tmp/lingolive-video-v2
backend/.venv/bin/python tools/render_submission_video_v2.py
```

The approved output's media-assets ZIP supplies `establishing.png`, WAVs,
`reply-lines.json`, the final and incomplete recording evidence, audio provenance
and checks. Copy those into the output directory when reproducing the edit.
The recorder selects actual model replies and writes reply-lines.json from its
`selected` dictionary when recording a fresh take. Keep legitimate TLS validation;
Chromium must trust the environment's current inspection CA, without bypass flags.

Prepare the verified media/docs ZIPs and preview page with
`backend/.venv/bin/python tools/build_submission_bundle_v2.py`, then publish only
those explicit files with `tools/publish_submission_v2.py --publish`.
The dedicated bucket already allows public artifact reading; the script changes
no IAM, runtime configuration, repository visibility or event submission.

## Submission status

The video can be watched/downloaded publicly from the existing Cloud Storage demo
site. Official YouTube/Vimeo/public Google Drive hosting, the source-visibility
requirement, team/eligibility confirmation and a Hack2skill portal receipt remain
separate. No accepted entry or approved third-party video host is claimed.
The old web 1.5 media remains available as an explicitly archived version.
