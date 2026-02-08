#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_PATH="${1:-${REPO_DIR}/dist/PurwayGeotagger.app}"

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { printf '[%s] %s\n' "$(ts)" "$*"; }

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Missing app bundle: ${APP_PATH}"
  exit 1
fi

: "${MACOS_CERT_P12:?Missing MACOS_CERT_P12 (base64 .p12)}"
: "${MACOS_CERT_PASSWORD:?Missing MACOS_CERT_PASSWORD}"
: "${APPLE_KEY_ID:?Missing APPLE_KEY_ID}"
: "${APPLE_ISSUER_ID:?Missing APPLE_ISSUER_ID}"
: "${APPLE_API_KEY_P8:?Missing APPLE_API_KEY_P8 (base64 .p8)}"

WORK_DIR="$(mktemp -d)"
KEYCHAIN="${WORK_DIR}/ci-signing.keychain-db"
KEYCHAIN_PASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)"
CERT_P12="${WORK_DIR}/cert.p12"
API_KEY="${WORK_DIR}/AuthKey_${APPLE_KEY_ID}.p8"
NOTARY_WAIT_TIMEOUT="${NOTARY_WAIT_TIMEOUT:-}"

cleanup() {
  security delete-keychain "${KEYCHAIN}" >/dev/null 2>&1 || true
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

decode_base64() {
  local input="$1"
  local output="$2"
  if base64 --decode </dev/null >/dev/null 2>&1; then
    printf '%s' "${input}" | base64 --decode > "${output}"
  else
    printf '%s' "${input}" | base64 -D > "${output}"
  fi
}

log "Preparing signing materials..."
decode_base64 "${MACOS_CERT_P12}" "${CERT_P12}"
decode_base64 "${APPLE_API_KEY_P8}" "${API_KEY}"
chmod 600 "${API_KEY}"

log "Creating + unlocking temporary keychain..."
security create-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}"
security set-keychain-settings -lut 21600 "${KEYCHAIN}"
security unlock-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}"
security default-keychain -s "${KEYCHAIN}"
log "Importing Developer ID certificate into keychain..."
# -A avoids GUI access prompts (headless CI); we still keep a minimal tool allowlist.
security import "${CERT_P12}" -k "${KEYCHAIN}" -P "${MACOS_CERT_PASSWORD}" -A -T /usr/bin/codesign -T /usr/bin/security
security list-keychain -d user -s "${KEYCHAIN}"
log "Granting codesign key access (partition list)..."
security set-key-partition-list -S apple-tool:,apple: -s -k "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}" >/dev/null

log "Locating Developer ID identity..."
IDENTITY="$(security find-identity -v -p codesigning "${KEYCHAIN}" | awk -F\" '/Developer ID Application/ {print $2; exit}')"
if [[ -z "${IDENTITY}" ]]; then
  echo "Developer ID Application identity not found in keychain."
  exit 1
fi

log "Signing app with identity: ${IDENTITY}"
codesign --force --options runtime --timestamp --sign "${IDENTITY}" --keychain "${KEYCHAIN}" --deep "${APP_PATH}"
codesign --verify --deep --strict --verbose=2 "${APP_PATH}"

log "Packaging DMG..."
bash "${REPO_DIR}/scripts/ci/macos_package.sh" "${APP_PATH}"
DMG_PATH="${REPO_DIR}/dist/PurwayGeotagger.dmg"

log "Submitting for notarization (async)..."

SUBMIT_TXT_PATH="${REPO_DIR}/dist/notarization_submit.txt"
SUBMIT_ID_PATH="${REPO_DIR}/dist/notarization_submission_id.txt"
INFO_JSON_PATH="${REPO_DIR}/dist/notarization_info.json"
WAIT_JSON_PATH="${REPO_DIR}/dist/notarization_wait.json"
LOG_JSON_PATH="${REPO_DIR}/dist/notarization_log.json"

# Keep normal output so CI shows upload progress; parse the submission id from output.
set +o pipefail
xcrun notarytool submit "${DMG_PATH}" \
  --key "${API_KEY}" \
  --key-id "${APPLE_KEY_ID}" \
  --issuer "${APPLE_ISSUER_ID}" \
  --no-wait \
  --verbose \
  --output-format normal \
  --progress \
  --no-s3-acceleration \
  2>&1 | tee "${SUBMIT_TXT_PATH}"
SUBMIT_RC=${PIPESTATUS[0]}
set -o pipefail
if [[ "${SUBMIT_RC}" -ne 0 ]]; then
  echo "notarytool submit failed with exit code: ${SUBMIT_RC}"
  exit "${SUBMIT_RC}"
fi

SUBMISSION_ID="$(
  python3 - <<'PY' <"${SUBMIT_TXT_PATH}"
import re
import sys

text = sys.stdin.read()
m = re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", text)
if not m:
    raise SystemExit("Unable to locate notarization submission id in notarytool output.")
print(m.group(0))
PY
)"
printf '%s\n' "${SUBMISSION_ID}" > "${SUBMIT_ID_PATH}"
log "Notarization submission id: ${SUBMISSION_ID}"

if [[ -n "${NOTARY_WAIT_TIMEOUT}" ]]; then
  log "Waiting up to ${NOTARY_WAIT_TIMEOUT} for notarization to complete..."
  set +e
  WAIT_JSON="$(
    xcrun notarytool wait "${SUBMISSION_ID}" \
      --key "${API_KEY}" \
      --key-id "${APPLE_KEY_ID}" \
      --issuer "${APPLE_ISSUER_ID}" \
      --timeout "${NOTARY_WAIT_TIMEOUT}" \
      --output-format json 2>&1
  )"
  WAIT_RC=$?
  set -e
  printf '%s\n' "${WAIT_JSON}" > "${WAIT_JSON_PATH}"
  log "notarytool wait exit code: ${WAIT_RC}"
fi

log "Fetching notarization status..."
INFO_JSON="$(
  xcrun notarytool info "${SUBMISSION_ID}" \
    --key "${API_KEY}" \
    --key-id "${APPLE_KEY_ID}" \
    --issuer "${APPLE_ISSUER_ID}" \
    --output-format json
)"
printf '%s\n' "${INFO_JSON}" > "${INFO_JSON_PATH}"

STATUS="$(
  python3 - <<'PY'
import json
import sys

data = json.load(sys.stdin)
status = data.get("status") or data.get("Status") or ""
print(str(status).strip())
PY
  <<<"${INFO_JSON}"
)"
log "Notarization status: ${STATUS:-<unknown>}"

STATUS_LC="$(printf '%s' "${STATUS}" | tr '[:upper:]' '[:lower:]')"
if [[ "${STATUS_LC}" == "accepted" ]]; then
  log "Stapling notarization ticket..."
  xcrun stapler staple "${APP_PATH}" || true
  xcrun stapler staple "${DMG_PATH}"
elif [[ "${STATUS_LC}" == "rejected" || "${STATUS_LC}" == "invalid" ]]; then
  echo "Notarization failed with status: ${STATUS}. Fetching log..."
  set +e
  xcrun notarytool log "${SUBMISSION_ID}" \
    --key "${API_KEY}" \
    --key-id "${APPLE_KEY_ID}" \
    --issuer "${APPLE_ISSUER_ID}" \
    "${LOG_JSON_PATH}"
  set -e
  exit 1
else
  echo "Not notarized yet (status: ${STATUS:-unknown}). Skipping stapling in this run."
fi

if [[ "${STATUS_LC}" == "accepted" ]]; then
  log "Running Gatekeeper assessments..."
  spctl --assess --type open -vv "${DMG_PATH}"
fi

log "Distribution artifact ready: ${DMG_PATH}"
