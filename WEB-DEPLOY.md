# Deploy LingoLive on Cloud Run

Web 1.8 adds guarded saved-place memory and prioritizes live replies; word meanings and practice open separately in
Saved. The UI change adds no model request for later review. The proposed new
video has not been produced: `docs/submission/DEMO-TRANSCRIPT-V2.md` awaits approval.

The web 1.8 deployment defaults to `gemini-3.1-flash-lite`, minimal thinking and
two parallel requests per lesson. Source understanding and replies are validated
and merged into the same public format. Transcription remains
`gemini-3.5-transcribe-live`. Current live revision and measured timings are
recorded in `validation/cloud-current-deployment.json` and `docs/LATENCY.md`.

Deployment now uses a normal refreshable Cloud SDK login. The account login and
refresh exchange were verified and credentials are kept in the private SDK
configuration outside this source repository. There is no need to supply an
hourly copied token. The app runtime uses its separate dedicated service account.
Use `gcloud auth list` before diagnosing operator authentication failures.
Keep Google sign-in disabled for the selected private access-code flow. Context
uses the existing model endpoint and adds no services. Optional recent audio
increases teach request size to at most 300,000 bytes; other API bodies remain
capped at 40,000 bytes. See `MEMORY.md` and `validation/cloud-current-*.json`.


One Cloud Run service hosts the responsive website, live Google transcription,
and Gemini Flash language lessons. The container listens on `$PORT` (8080 by
default). `/` serves the site; `/health` reports setup; protected `/v1/` endpoints
handle learning. Transcripts and lessons remain in the browser's IndexedDB.

## Connection choices

The web Connect dialog offers **Use access code** and **Use my Google API key**.
Host-code mode uses the configured provider (recommended: Vertex runtime service
account). Personal-key mode always uses Gemini Developer API with the learner's
AI Studio key for both Flash and Transcribe Live, never the runtime account.
No host key/code is needed for personal-key-only local operation; the recommended
deployment helper still configures host access as well.

`LINGOLIVE_BYOK_ENABLED=true` is the default. Set it to `false` to disable new
personal-key sessions. Keys stay in RAM for at most one hour; keep one instance,
without worker replication. Restart/scale-to-zero forgets them, so users may need
to reconnect. A Google-invalid key can create a session but paid operations return
a safe Google access/billing error; no host fallback occurs. Allow server-side
requests on restricted keys and enable access/quota for the configured models.
The relay does not log request bodies or upstream key-bearing URLs; keep proxy
and error logging from recording credentials when customizing deployment.

Existing raw model-call allowances are unchanged; a parallel lesson consumes two units. Personal-key users share a separate set of
those allowances; both groups share the concurrency/pacing limits. Google model
charges go to the personal key's project; Cloud Run relay costs remain with the
host. Session creation remains rate limited and at most 64 personal-key sessions
are retained per process. Emergency AI pause blocks both modes. Optional Google
invitation requirements continue to apply only to host-code access.

## Recommended: Vertex AI with the Cloud Run service account

Use an existing signed-in Cloud Shell, or a normal persistent Cloud SDK login on
the machine doing the deployment. On a workstation, `gcloud auth login` stores
refreshable credentials in the SDK's private configuration; subsequent deploys
normally refresh automatically. In an already authorized Cloud Shell, use that
existing login. Check `gcloud auth list` before starting a new login.

This agent workspace and a phone's Cloud Shell are different machines. A pasted
`gcloud auth print-access-token` value is only a short-lived bearer token, without
the refresh credential. It does not sign this workspace into gcloud permanently.
Do not use repeated token copying as the normal deployment workflow. Never put
SDK credential files, refresh tokens or access tokens in Git or the app image.
The deployed runtime account obtains its own credentials automatically; operator
token expiry does not sign users out or stop the existing app's Google access.

Use a billing-enabled Google Cloud project. Enable Vertex AI (`aiplatform`),
Cloud Run, Cloud Build, Artifact Registry, IAM and Secret Manager.
The deployment defaults are Gemini 3.1 Flash-Lite (minimal thinking, parallel) and Gemini 3.5 Transcribe Live through Vertex;
host-code operation needs **no Google API key** in the browser or recommended runtime. Personal-key mode accepts a key only at connection time; source contains no keys.
Google authentication uses the runtime service account's automatically refreshed
OAuth token. Usage is billed to the Cloud project. AI Studio prepaid credits are
not used by this provider.

Create dedicated service accounts `lingolive` (runtime) and `lingolive-build`
(source builder). Grant the builder `roles/run.builder`. The deployment operator
needs normal Cloud Run/source-build permissions and permission to act as both
accounts. Newly granted IAM roles may take a few minutes to propagate.

Give the runtime only these model permissions, for example in a custom project role:

- `aiplatform.endpoints.predict`
- `serviceusage.services.use`

Create a Secret Manager secret named `lingolive-private-access`, containing a
cryptographically random access code of at least 32 characters. Grant the runtime
`roles/secretmanager.secretAccessor` on that secret. Share the code privately with
judges/testers. Do not put its value in source, build arguments, or a public video.

Deploy from the extracted source root with an authenticated Google Cloud CLI:

```bash
PROJECT_ID=YOUR_PROJECT \
SERVICE_ACCOUNT=lingolive@YOUR_PROJECT.iam.gserviceaccount.com \
BUILD_SERVICE_ACCOUNT=lingolive-build@YOUR_PROJECT.iam.gserviceaccount.com \
ACCESS_TOKEN_SECRET=lingolive-private-access \
LINGOLIVE_GOOGLE_SIGNIN_REQUIRED=false \
REGION=us-central1 \
bash tools/deploy_cloud_run.sh
```

The helper defaults to `LINGOLIVE_PROVIDER=vertex`, binds the configured project,
and uses `global` for the model location. Model IDs can be overridden with
`LINGOLIVE_FLASH_MODEL` and `LINGOLIVE_TRANSCRIBE_MODEL`. `LINGOLIVE_LESSON_STRATEGY=parallel`
and `LINGOLIVE_THINKING_LEVEL=auto` select the fast default. Set
`LINGOLIVE_LESSON_STRATEGY=single` and `LINGOLIVE_FLASH_MODEL=gemini-3.8-flash`
for the legacy full-field comparison path; auto selects low thinking for that model.
Python `Config` retains legacy defaults for callers without environment settings;
use `backend/.env.example` or the deployment helper for the fast configuration. Default Cloud Run limits
are zero minimum/one maximum instance, two active listeners, two concurrent
lessons and a 600-second request timeout. Brief five-second draining connections
keep both listeners' final words during automatic renewal. Host-funded calls require
the private code (one-hour secure browser cookie, or Android bearer token).
Personal-key calls require a separate active key session and use that key.

Shared rolling model-call allowances: 24/minute, 360/hour, 400/day. Each parallel
lesson reserves two units, permitting at most 12 lessons/minute, 180/hour, 200/day.
There are 40 combined audio
minutes/hour and 60/day. Google connection time, including silence, is counted;
unused reservations are refunded after disconnect. Audio must be paced in real
time, frames are bounded, and missing frames close the stream after 20 seconds.
Lesson input is limited to 1,000 characters. The combined 4,096-token output cap
is divided between the two concurrent branches. Failed calls are not retried
automatically and do not trigger a third model call. Normal
two-user, fifteen-minute use fits these allowances; this is not a measured phone
latency or provider availability guarantee. Counters are per instance and reset
on restart or redeployment. They are not a hard dollar budget.

The corresponding runtime variables are `LINGOLIVE_REQUESTS_PER_MINUTE`,
`LINGOLIVE_LESSONS_PER_HOUR`, `LINGOLIVE_LESSONS_PER_DAY`,
`LINGOLIVE_AUDIO_SECONDS_PER_HOUR`, `LINGOLIVE_AUDIO_SECONDS_PER_DAY`, and
`LINGOLIVE_MAX_OUTPUT_TOKENS`. Pause both paid routes immediately with:

```bash
gcloud run services update lingolive --project=YOUR_PROJECT --region=us-central1 \
  --update-env-vars=LINGOLIVE_AI_ENABLED=false
```

To resume, set the same variable to `true`. Saved lessons and the prepared
example remain available while AI is paused. Cloud billing alerts are separate
and do not stop spending. Keep the private code private; a public launch needs
individual identity and durable cross-instance quotas.

The HTTPS service URL printed at the end serves the website. Click **Connect**
and enter your private access code, or choose your own Google key. To retrieve that code in your own authorized
Cloud Shell, run (do not send the output to a public chat):

```bash
gcloud secrets versions access latest \
  --secret=lingolive-private-access --project=YOUR_PROJECT
```

Choose your two languages, allow microphone access, and speak. Verify the actual
transcript, word definitions, three replies, and Saved persistence before recording
the competition video. A prepared example is labeled and never inserted as speech.

## Optional: Google AI Studio / Gemini API provider

For `LINGOLIVE_PROVIDER=gemini`, create another secret holding an AI Studio key,
set `GOOGLE_KEY_SECRET` to its name, and grant the runtime access to that secret.
The helper will bind it as `GEMINI_API_KEY`. AI Studio model access/quota and
prepaid billing requirements apply separately. Listing models does not prove
that generation has available credit. An upstream HTTP 402 is surfaced as a
clear, retryable AI Studio billing message while preserving the transcript.
Android's on-device-key option still uses this Gemini API provider; its hosted
connection option works with either backend provider.

## Local verification

```bash
uv venv backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
backend/.venv/bin/python -m unittest discover -s backend/tests -v
backend/.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8093 --no-access-log
```

Without runtime settings, the site and prepared example open; `/health` reports
`configured:false` and protected API requests return 503. For live local Vertex
calls, supply valid Application Default Credentials, the Vertex project/provider
settings and the private access code. A local shell/health check is not evidence
of live model inference. Read `VALIDATION.md` for actual completed checks.

The production Dockerfile uses standard instructions compatible with Cloud Run's
managed source builds. `Dockerfile.dev` retains an optional BuildKit `build_ca`
secret for local development behind a TLS-inspecting proxy. Use that development
file with an existing trusted CA bundle if needed; never disable TLS verification.

The event submission also requires the eligible problem statement/category,
a proposal PDF, a public three-minute demo video, and English materials. A working
cloud deployment does not by itself establish contest eligibility.


## Optional Google sign-in (disabled; private-code sign-in selected)

The new source requires a registered OAuth **Web application** client before
Google login can be activated. No client secret is needed: Google Identity
Services returns a signed ID token to the browser; the server verifies its RSA
signature, issuer, audience, expiry and per-browser nonce using Google's auth
library. Public certificates are cached for five minutes. Only explicitly invited
verified Google email addresses can receive a signed one-hour app session, and
the private access code is still required. Old code-only sessions and bearer-only
API/WebSocket calls are rejected in required mode. Google credentials remain in
memory and are not written to local storage, URLs or the service worker cache.

The Google support code is included in revision `lingolive-00005-lch`, with
private-code access confirmed working. Google sign-in is not enabled yet. The project is outside a
Google organization. The official installed Cloud SDK documents that IAP OAuth
Admin client/brand creation APIs shut down March 19, 2026, and that first-time
IAP setup for an organization-less project requires the Cloud Console. No
authenticated Google Console browser is available to the agent, so the OAuth
registration cannot be completed with the currently available access.

One-time owner registration:

1. Open https://console.cloud.google.com/auth/clients?project=locateassist .
2. If Google displays **Get started**, use application name **LingoLive**, support
   and contact email **ashish.t.vasant@gmail.com**, and **External** audience.
   If the consent screen is in Testing mode, add the owner's email as a test user.
3. Create a client with application type **Web application**, name **LingoLive Web**.
4. Add this **Authorized JavaScript origin**, without a trailing slash:
   `https://lingolive-358650584819.us-central1.run.app`.
   The popup callback flow does not require an authorized redirect URI.
5. Copy only the public **Client ID** ending in `.apps.googleusercontent.com`.
   Keep any client secret private; this app does not use it.

After registration, activate the deployed support with the authorized CLI
without another source build:

```bash
PROJECT_ID=locateassist \
LINGOLIVE_GOOGLE_CLIENT_ID=YOUR_PUBLIC_WEB_CLIENT_ID.apps.googleusercontent.com \
LINGOLIVE_ALLOWED_GOOGLE_EMAILS=ashish.t.vasant@gmail.com \
bash tools/enable_google_signin.sh
```

Use the exact public origin above when opening the app. Any additional host or
Cloud Run alias must be registered as another authorized JavaScript origin.
Additional invited users need their email added to the comma-separated runtime
`LINGOLIVE_ALLOWED_GOOGLE_EMAILS` list. While Google's consent screen is in
Testing mode, also add them to Google's test-user list. Do not use a wildcard.
The deployment helper preserves comma-separated email values. All existing
model/audio usage guards remain unchanged.

The current Android APK uses bearer-only access and does not support this extra
Google step; it will be denied by a Google-required deployment. The update is
for the web app. Real Google account sign-in must be checked after registration;
fixture tokens and a mocked browser SDK do not establish live OAuth readiness.

`tools/enable_google_signin.sh` updates only the three account settings and
preserves budgets, model configuration and secret bindings. For a new deployment,
`tools/deploy_cloud_run.sh` defaults to private-code-only sign-in, as the user
requested. Optional `LINGOLIVE_GOOGLE_SIGNIN_REQUIRED=true` requires registered
client credentials and invited emails before building. Never disable an already
activated Google requirement during a routine redeploy.

The user selected simple private-access-code sign-in. Google registration is not
a blocker for this app; no further Google setup is requested.
