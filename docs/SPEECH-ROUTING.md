# Speech routing in web 1.10

Repeating an offered reply is a learner turn, not a new question to answer.
The previous code detected exact repeats only after `/v1/teach` had already
returned. The live listener now makes this decision before queuing a paid call,
and checks again before sending a queued request.

The reply set currently displayed (otherwise the latest ready set) in the same
learner, conversation and language pair is eligible, and only for three minutes. Matching uses original script,
pronunciation and translated wording, preserving Indic vowel marks. A specific
exact repeat is saved locally as `likely_user`; the current useful reply cards
remain on screen. Its text joins later conversation context. It does not create
another lesson or unconfirmed long-term personal/place memory.

A short/common repeat or near match asks **Who said this?** before spending a
request. Approximate text never silently suppresses a changed intent. **I said
this** saves the learner turn; **Other person said this** releases it for replies.
That same correction is available on an automatically suppressed turn in Recent
phrases. Typed input and explicit **Help me say this** remain available.

## Session voice estimates

Google explicitly documents that live streaming transcription does not support
speaker diarization: https://ai.google.dev/gemini-api/docs/live-api/live-transcribe.
No unsupported speaker flag or extra transcription/model call is added.

The browser computes short-time pitch and 12 cepstral coefficients from the
existing 16 kHz microphone frames. A maximum of 240 voiced feature frames spans
at most ten seconds; a turn uses the most recent eight seconds. Silence, very
short/unstable samples abstain. These are lightweight acoustic features, not a
trained speaker-embedding model or reliable personal identity.

Recent repeated options and explicit speaker corrections supply role anchors.
A sufficiently different source question can provide the other-speaker anchor
when the learner repeats a reply; expression-mode input is excluded. A new turn
is attributed only with both anchors, a close match and a clear distance margin.
Otherwise it remains unknown. An estimated other-speaker turn can override a
text repeat match. No role is inferred from language or presumed gender alone.

At most three samples per role expire after three minutes. Up to twenty transient
turn features support corrections; no waveforms or features are stored in
IndexedDB/localStorage, cookies, API payloads or server memory. Voice estimates
clear on profile/language/conversation changes, reset, disconnect, backgrounding
or reload. Original transcripts remain in the normal local history. Settings →
Speaker matching → Reset speaker matching clears estimates immediately.

Rapid overlapping speakers, similar voices, background sound, delayed transcript
boundaries and changed microphones can defeat this heuristic. Unknown turns can
still reach normal reply generation; the app cannot guarantee perfect separation
of all speakers. Use speaker correction for a wrong estimate. This feature is
not authentication or biometric identification.

## Evidence

- Fifteen routing checks cover Indic text, reading variants, ambiguity, changed
  intent, expiry, isolation, anchors, silence and bounded feature storage.
- Seven real-browser flow checks cover no-call repeats, next-person replies with
  learner context, correction, manual expression and feature privacy. Google
  transcription/lesson outputs are explicit fixtures.
- Four browser audio checks send existing Kannada actor WAVs through the actual
  getUserMedia/AudioWorklet/resampler path: repeated option and a new learner
  utterance consume no lesson, while another voice is processed. Google outputs
  are fixtures; this is not a physical microphone test.
- An offline held-out check using clean generated demo voices recognized three
  of four learner clips. None of four other-speaker clips was labelled user;
  those clips stayed unknown. Calibration clips are excluded. These eight samples
  are functional evidence, not population accuracy or noisy-phone validation.

Evidence lives in `validation/web-speech-routing-*.json`,
`validation/web-speaker-*-results.json`. No new paid model call is needed by routing.
