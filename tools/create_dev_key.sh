#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../android"
mkdir -p .signing
if [[ -f .signing/debug.keystore ]]; then
  echo 'Existing signing key retained.'
  exit 0
fi
keytool -genkeypair -keystore .signing/debug.keystore -storepass android \
  -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 \
  -validity 10000 -dname 'CN=LingoLive Development,O=U4AR,C=IN'
