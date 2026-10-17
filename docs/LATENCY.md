# Live latency measurements

Measured October 17, 2026 on the public LingoLive web 1.4 service:
https://lingolive-358650584819.us-central1.run.app.

The latest runtime was already deployed as `lingolive-00008-cos`, serving 100%
of traffic. Cloud metadata, model settings and deployed web assets were verified.
Runtime source still matches commit `cfd348ea9066f0c4835b424a59ea813fcb533bd8`.
No application change or rebuild was needed for this measurement.

Gemini 3.8 Flash uses low reasoning. Each lesson request returns translation,
three replies, every word meaning and all required Latin readings in one call.
Timing starts when the test client posts `/v1/teach` and ends when the complete
JSON is received. Successful results also passed the app's source-preservation,
word-definition and reply validation.

| Short phrase, learning language | Samples | Median | Range |
| --- | ---: | ---: | ---: |
| Japanese | 2 | 6.55 s | 5.36–7.74 s |
| Hindi | 2 | 11.63 s | 8.58–14.67 s |
| Spanish | 2 | 8.54 s | 6.90–10.18 s |

Two independent signed-in sessions started requests within 2 ms of each other:
Japanese completed in **4.69 s**, Hindi in **8.36 s**. These requests ran alongside
each other with the existing two-lesson concurrency limit.

The real Google speech test used a **2.128-second synthesized reference WAV**,
streamed at real-time speed through the authenticated public WebSocket.

| Speech pipeline component | Observed time |
| --- | ---: |
| Socket and Google speech setup | 0.79 s |
| Final transcript after last audio frame | 0.35 s |
| Test client's socket-close/handoff overhead | 1.10 s |
| Lesson response, with conversation context and no audio attachment | 6.96 s |
| Last audio frame → complete lesson, including test handoff | **8.40 s** |
| Socket start → complete lesson, including speaking | **11.33 s** |
| Same transcript/context, with optional audio attachment | **19.18 s** |

All **10 lesson requests succeeded**, including complete meanings/readings and
three replies. No automatic model retries were made. One short speech stream was
used. Credentials remained in RAM/Cloud SDK, outside the report and Git.

Responses still take seconds. In the one matched comparison, adding optional
recent sound was slower (19.18 s versus 6.96 s). Sound context remains off by
default. This sample does not establish that audio always adds the same delay.
The current UI receives a whole validated JSON response; it does not stream a
partial translation before all reply/word fields finish.

These are small warm-path samples from this cloud workspace. The service was
probed for health/assets before measurement; a cold start was not measured.
Phone microphone handling, browser rendering and mobile networks were not tested.
Two samples per language are insufficient for reliable tail percentiles or a
language-wide performance claim. The test paused between sequential and
concurrent phases to fix a harness name collision; completed model calls were
retained rather than repeated, and individual request timers exclude that pause.

Raw timings: [cloud-latency-results.json](../validation/cloud-latency-results.json).

## Reproduce deliberately

These checks make real Google calls and may incur charges. They run only with
`--run-live`, cap lesson attempts at ten, retain all existing service quotas and
never change the deployment or instance limits. Use the normal refreshable
`gcloud` login with access to the existing `locateassist` service and its private
access-code secret. The key/code is never accepted as a CLI argument or printed.

From the repository root:

```bash
backend/.venv/bin/python tools/measure_cloud_latency.py --run-live
```

The synthesized speech fixture is included in `tools/fixtures/reference.wav`.
`--output PATH` selects a report path. `--resume` continues unmeasured cases in
the same report, checks the revision, and retains the ten-attempt ceiling; it
does not automatically retry completed failures. Do not rerun just to get a
better-looking timing. This script is excluded from the Cloud Run image.
