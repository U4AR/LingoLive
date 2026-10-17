#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ID:?Set the existing Google Cloud project ID}"
: "${LINGOLIVE_GOOGLE_CLIENT_ID:?Set the registered public Web application client ID}"
: "${LINGOLIVE_ALLOWED_GOOGLE_EMAILS:?Set the explicit invited email list}"
[[ "$LINGOLIVE_GOOGLE_CLIENT_ID" =~ ^[a-zA-Z0-9.-]+\.apps\.googleusercontent\.com$ ]] || { echo 'Invalid Google OAuth client ID' >&2; exit 2; }
[[ "$LINGOLIVE_ALLOWED_GOOGLE_EMAILS" != *'|'* ]] || { echo 'Invalid email-list separator' >&2; exit 2; }
# Update just these three settings, preserving model budgets, credentials and scaling.
gcloud run services update lingolive --project "$PROJECT_ID" --region "${REGION:-us-central1}" \
  --update-env-vars "^|^LINGOLIVE_GOOGLE_SIGNIN_REQUIRED=true|LINGOLIVE_GOOGLE_CLIENT_ID=${LINGOLIVE_GOOGLE_CLIENT_ID}|LINGOLIVE_ALLOWED_GOOGLE_EMAILS=${LINGOLIVE_ALLOWED_GOOGLE_EMAILS}"
