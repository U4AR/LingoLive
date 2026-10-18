#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROJECT_ID:?Set your Google Cloud project ID}"
: "${SERVICE_ACCOUNT:?Set a dedicated Cloud Run service-account email}"
: "${ACCESS_TOKEN_SECRET:?Set the existing Secret Manager secret name holding a random private access token of at least 32 characters}"
LINGOLIVE_REGION="${REGION:-us-central1}"
LINGOLIVE_CLOUD_PROVIDER="${LINGOLIVE_PROVIDER:-vertex}"
LINGOLIVE_BUILD_ACCOUNT="${BUILD_SERVICE_ACCOUNT:-lingolive-build@${PROJECT_ID}.iam.gserviceaccount.com}"
LINGOLIVE_SECRET_BINDINGS="LINGOLIVE_ACCESS_TOKEN=${ACCESS_TOKEN_SECRET}:latest"
LINGOLIVE_MODEL_BINDINGS="LINGOLIVE_PROVIDER=${LINGOLIVE_CLOUD_PROVIDER},LINGOLIVE_FLASH_MODEL=${LINGOLIVE_FLASH_MODEL:-gemini-3.1-flash-lite},LINGOLIVE_TRANSCRIBE_MODEL=${LINGOLIVE_TRANSCRIBE_MODEL:-gemini-3.5-transcribe-live}"
if [[ "$LINGOLIVE_CLOUD_PROVIDER" == vertex ]]; then
  LINGOLIVE_MODEL_BINDINGS+=",LINGOLIVE_VERTEX_PROJECT=${PROJECT_ID},LINGOLIVE_VERTEX_LOCATION=${LINGOLIVE_VERTEX_LOCATION:-global}"
elif [[ "$LINGOLIVE_CLOUD_PROVIDER" == gemini ]]; then
  : "${GOOGLE_KEY_SECRET:?Set the existing Secret Manager secret name holding your Gemini API key}"
  LINGOLIVE_SECRET_BINDINGS+=",GEMINI_API_KEY=${GOOGLE_KEY_SECRET}:latest"
else
  echo 'LINGOLIVE_PROVIDER must be vertex or gemini' >&2
  exit 2
fi
LINGOLIVE_MODEL_BINDINGS+=",LINGOLIVE_LESSON_STRATEGY=${LINGOLIVE_LESSON_STRATEGY:-parallel},LINGOLIVE_THINKING_LEVEL=${LINGOLIVE_THINKING_LEVEL:-auto},LINGOLIVE_AI_ENABLED=${LINGOLIVE_AI_ENABLED:-true},LINGOLIVE_BYOK_ENABLED=${LINGOLIVE_BYOK_ENABLED:-true},LINGOLIVE_REQUESTS_PER_MINUTE=24,LINGOLIVE_LESSONS_PER_HOUR=360,LINGOLIVE_LESSONS_PER_DAY=400,LINGOLIVE_AUDIO_SECONDS_PER_HOUR=2400,LINGOLIVE_AUDIO_SECONDS_PER_DAY=3600,LINGOLIVE_MAX_OUTPUT_TOKENS=4096"
# Custom separator preserves commas inside the invited-email allowlist.
LINGOLIVE_MODEL_BINDINGS="^|^${LINGOLIVE_MODEL_BINDINGS//,/|}"
if [[ "${LINGOLIVE_GOOGLE_SIGNIN_REQUIRED:-false}" == true ]]; then
  : "${LINGOLIVE_GOOGLE_CLIENT_ID:?Register a Google OAuth Web application client first}"
  if [[ "${LINGOLIVE_PUBLIC_DEMO:-false}" != true ]]; then
    : "${LINGOLIVE_ALLOWED_GOOGLE_EMAILS:?Set invited email addresses, or enable the public demo for any verified Google account}"
  fi
  [[ "$LINGOLIVE_GOOGLE_CLIENT_ID" =~ ^[a-zA-Z0-9.-]+\.apps\.googleusercontent\.com$ ]] || { echo 'Invalid Google OAuth client ID' >&2; exit 2; }
  [[ "$LINGOLIVE_ALLOWED_GOOGLE_EMAILS" != *'|'* ]] || { echo 'Invalid email-list separator' >&2; exit 2; }
  LINGOLIVE_MODEL_BINDINGS+="|LINGOLIVE_GOOGLE_SIGNIN_REQUIRED=true|LINGOLIVE_GOOGLE_CLIENT_ID=${LINGOLIVE_GOOGLE_CLIENT_ID}|LINGOLIVE_ALLOWED_GOOGLE_EMAILS=${LINGOLIVE_ALLOWED_GOOGLE_EMAILS:-}"
else
  LINGOLIVE_MODEL_BINDINGS+="|LINGOLIVE_GOOGLE_SIGNIN_REQUIRED=false"
fi
if [[ "${LINGOLIVE_PUBLIC_DEMO:-false}" == true ]]; then
  : "${LINGOLIVE_QUOTA_BUCKET:?Create a private, runtime-writable quota bucket first}"
  LINGOLIVE_MODEL_BINDINGS+="|LINGOLIVE_PUBLIC_DEMO=true|LINGOLIVE_QUOTA_BUCKET=${LINGOLIVE_QUOTA_BUCKET}|LINGOLIVE_PUBLIC_AUDIO_SECONDS_PER_DAY=1200|LINGOLIVE_PUBLIC_MODEL_CALLS_PER_DAY=200"
fi
if [[ "${LINGOLIVE_GOOGLE_AUTH_PROVIDER:-gis}" == firebase ]]; then
  : "${LINGOLIVE_FIREBASE_API_KEY:?Set the app-specific restricted public Firebase browser key}"
  : "${LINGOLIVE_FIREBASE_AUTH_DOMAIN:?Set the existing Firebase auth handler domain}"
  LINGOLIVE_MODEL_BINDINGS+="|LINGOLIVE_GOOGLE_AUTH_PROVIDER=firebase|LINGOLIVE_FIREBASE_API_KEY=${LINGOLIVE_FIREBASE_API_KEY}|LINGOLIVE_FIREBASE_AUTH_DOMAIN=${LINGOLIVE_FIREBASE_AUTH_DOMAIN}"
fi

gcloud run deploy lingolive --source . --project "$PROJECT_ID" --region "$LINGOLIVE_REGION" \
  --service-account "$SERVICE_ACCOUNT" \
  --build-service-account "projects/${PROJECT_ID}/serviceAccounts/${LINGOLIVE_BUILD_ACCOUNT}" \
  --allow-unauthenticated --max-instances 1 --min-instances 0 --cpu-throttling --concurrency 12 \
  --timeout 600 --memory 512Mi --cpu 1 \
  --set-secrets "$LINGOLIVE_SECRET_BINDINGS" --set-env-vars "$LINGOLIVE_MODEL_BINDINGS"
