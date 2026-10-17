# Speech latency fixture

`reference.wav` is an existing synthesized utterance, “John chapter 3 verse 16”,
used for a repeatable transcription check. It is not a physical microphone or
personal recording. Format: mono 16 kHz PCM16, 2.128 seconds.

The latency tool sends it at real-time speed. It checks that the complete spoken
reference is recognized before requesting a lesson. Other audio can be supplied
with `--wav`, but must use this sentence and format, last at most four seconds,
and contain no private recording unless the operator intends to send it to Google.
