# Live latency comparison — October 17, 2026

[Open LingoLive](https://lingolive-358650584819.us-central1.run.app).
Web 1.5 revision `lingolive-00010-naj` now serves 100% of public traffic.
Runtime source: `a0a91d9e9cd8b236edf31f2286c864c6b4e4f509`.

The optimized deployment averaged **1.79 seconds for ten complete,
validated lessons**, compared with **9.26 seconds** for the earlier web 1.4
sample. All ten new lessons succeeded. This meets the requested two-second average
in this small warm-path test; it is not a guarantee for mobile networks, cold starts,
long speech, every language or provider load.

## Comparison of one request and two parallel requests

A bounded direct Vertex comparison used the same three prepared Japanese, Hindi
and Spanish phrases with English explanations. These timings are direct Google
requests from this workspace, separate from the deployed-app results below.

| Design | Successful lessons | Mean elapsed |
| --- | ---: | ---: |
| Gemini 3.8 Flash, original one-call full lesson | 3/3 | 6.71 s |
| Gemini 3.8 Flash, two parallel calls with original full fields | 3/3 | 9.55 s |
| Gemini 3.8 Flash, two parallel calls with compact word triples | 3/3 | 3.61 s |
| Gemini 3.1 Flash-Lite, first compact experiment | 1/3 | Unreliable: missing readings/definitions |
| Flash-Lite, required nonempty triples | 3/3 | 1.99 s |
| Flash-Lite, shorter explanations/replies, follow-up experiment | 3/3 | 2.25 s |

Splitting the original request alone did not help reliably. The final change also
uses Flash-Lite with minimal thinking, compact structured fields, shorter replies
and reusable server-side HTTP connections. The final prompt was shortened further
after those preflights. Gains cannot be attributed to parallelism alone, nor to a
single prompt change. All experimental results, including failed/slow variants,
are retained in `validation/parallel-*.json`.

## Deployed app measurements

The final candidate was measured through its authenticated HTTPS revision tag,
then the identical revision/image was promoted. The public URL's health, nine
assets, runtime settings and 100% routing were rechecked afterward. No paid call
was repeated just to get a better timing. The report retains the exact tested tag
URL; that temporary tag has now been removed.

Timing starts at the test client's POST `/v1/teach` and ends when the complete
JSON arrives: translation, every required word meaning/Latin reading, all three
replies, and context. Validation checks exact source reconstruction and complete
lexical definitions. Results were received as full JSON, not a partial preview.

| Learning language, two sequential samples | Previous 3.8 median | Parallel Lite median |
| --- | ---: | ---: |
| Japanese | 6.55 s | 1.81 s |
| Hindi | 11.63 s | 1.91 s |
| Spanish | 8.54 s | 1.53 s |

The six sequential short-phrase calls averaged **1.75 seconds**
(previously 8.90 seconds). Two independent sessions started
within 2 ms of each other: Hindi **1.65 s**, Japanese **1.71 s**. A source/context
lesson with English speech and Japanese explanations took **2.09 s**, and the
same context with an optional WAV took **1.95 s**. The single optional-audio pair
does not establish a general audio speed advantage.

A separate staged functional check, before the ten-call measurement, took
**2.34 s** for a contextual audio lesson; it remains in
`validation/cloud-current-api-results.json` and is excluded from the declared
ten-case protocol. Across that check and the ten measured lessons, the mean is
**1.84 s** (11/11 validated).

| Real Google speech pipeline, synthesized 2.128-second WAV | Observed time |
| --- | ---: |
| Socket and Google speech setup | 0.71 s |
| Final transcription after the last audio frame | 0.34 s |
| Test client's socket-close/handoff overhead | 1.11 s |
| Complete contextual lesson after HTTP request | 2.09 s |
| Last audio frame → complete lesson, including test handoff | **3.54 s** |
| Socket start → complete lesson, including speaking | **6.40 s** |

The two-second target is met for mean lesson HTTP latency here, **not the entire
speech-to-result pipeline**. The browser queues final transcripts immediately;
the test harness closes the speech socket before its HTTP handoff. No phone
microphone, browser paint timing or cold start was measured. Existing scale-to-zero
is retained. With only two sequential samples per language, percentiles and broad
language/semantic quality claims would be unsupported.

## Implementation, compatibility and cost bounds

Each lesson runs two tasks concurrently: source translation/word meanings/context,
and three short suggested replies with their meanings/readings. Both see incoming
history, goal and learner notes. New source-branch scene inference affects replies
on the next turn; the reply branch does not wait for it. Optional recent audio goes
to the source branch only. Public/saved lesson format remains compatible. The
explanation is concise, meanings are brief, and optional tip/per-word notes are
empty. The UI's word bubbles, pronunciation toggle and first-use tutorial remain.
An artificial 2.5-second client queue wait was removed.

No automatic retry, fallback or third paid model call occurs. Failed work cancels
its sibling. Two model calls consume two units of the unchanged 24/minute,
360/hour and 400/day model-call allowances: effectively 12/180/200 parallel
lessons. The two branch output caps total at most 4,096 tokens. The service keeps
one maximum instance, zero minimum, 512 MiB, one CPU, request-based billing, two
concurrent lessons and existing audio/auth guards. No always-warm resource was
added to reach this result. A cheaper model and reduced output do not constitute
a fixed dollar budget; input context is duplicated across the two requests.

## Evidence and deliberate reproduction

- [Final hosted results](../validation/cloud-parallel-latency-results.json)
- [Earlier 1.4 baseline](../validation/cloud-latency-results.json)
- [Direct architecture comparison](../validation/parallel-architecture-comparison.json)
- [Required-triple preflight](../validation/parallel-lite-preflight.json)
- [Shorter-prompt preflight](../validation/parallel-lite-tight-preflight.json)

The opt-in harness makes at most ten lessons (twenty generation calls in parallel
mode) and one short speech stream, using normal Cloud SDK login and Secret Manager.
Credentials remain in RAM, never CLI arguments or reports. From the repository root:

```bash
backend/.venv/bin/python tools/measure_cloud_latency.py --run-live --output /tmp/lingolive-latency.json
```

It checks deployment settings, runtime/source fingerprints, public assets, auth,
output validity and unchanged limits. `--resume` continues unmeasured cases in the
same report/revision, retains the ten-attempt ceiling and never retries completed
failures. `--url` plus `--expected-traffic 0` supports a verified staging tag.
The synthesized fixture is included in `tools/fixtures/reference.wav`. Valid
personal-key inference and physical-phone latency remain unverified.
