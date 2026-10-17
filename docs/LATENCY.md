## Web 1.8 place memory and mobile submit correction

Place extraction uses the existing source branch and returned place notes are
bounded to two. No third model call, paid mapping service or output-cap increase
was introduced. Final functional HTTP times are 2.254 / 1.864 / 1.691 s
(mean 1.936 s); full browser interactions are 2.335 / 1.983 / 1.814 s. These are
three functional simulated-location cases, not a stable average/physical speech
benchmark. Current isolated HTTP and total UI interaction timings are
recorded separately in `validation/cloud-v1.8-api-results.json`.

The previous browser functional timers began before clicking the submit button.
A mobile status banner could intercept that click: a local test measured 6.046 s
to request before, 0.134 s after the non-intercepting notice fix. Earlier 1.7
browser samples and the 1.8 before-fix 2.745/7.761/7.375 s interaction samples
include that auto-wait; they must not be described as isolated Google latency.
The separate direct-HTTP 1.7 comparison remains valid: with memory 1.989/2.029 s,
without 1.933/1.567 s. Small samples do not establish a stable average or a
physical speech/mobile-network guarantee. All earlier slow/failed evidence is
retained, including the place-note extraction-quality failure.

## Web 1.7 memory update

Durable personal memory adds up to five 160-character items to both existing
parallel prompts and at most two source-side proposals. It adds no third model
request and preserves the combined 4,096-token cap. The older ten-request averages
below predate these changes. The functional requests took 2.040 s and 7.604 s. Two subsequent memory
requests took 1.989 s and 2.029 s (mean 2.009 s), while two without memory
took 1.933 s and 1.567 s (mean 1.750 s). All succeeded; this tiny interleaved
comparison does not establish causality. Full results, including the slow call,
are in `validation/cloud-v1.7-api-results.json` and
`validation/cloud-v1.7-memory-timings.json`; do not relabel them as a
fresh ten-request average or a noisy physical-phone speech benchmark.

> Web 1.6 moves teaching into Saved and prioritizes replies during a live exchange.
> The measurements below were collected on web 1.5; they are not a fresh 1.6
> benchmark. Models, request format, parallelism and budgets are unchanged.

# Live latency comparison — October 17, 2026

[Open LingoLive](https://lingolive-358650584819.us-central1.run.app).
Web 1.5 revision `lingolive-00010-naj` was the measured deployment.
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
