#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_PATH="${1:-${REPO_DIR}/dist/PurwayGeotagger.app}"

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

decode_base64 "${MACOS_CERT_P12}" "${CERT_P12}"
decode_base64 "${APPLE_API_KEY_P8}" "${API_KEY}"

security create-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}"
security set-keychain-settings -lut 21600 "${KEYCHAIN}"
security unlock-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}"
security import "${CERT_P12}" -k "${KEYCHAIN}" -P "${MACOS_CERT_PASSWORD}" -T /usr/bin/codesign -T /usr/bin/security
security list-keychain -d user -s "${KEYCHAIN}"
security set-key-partition-list -S apple-tool:,apple: -s -k "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}" >/dev/null

IDENTITY="$(security find-identity -v -p codesigning "${KEYCHAIN}" | awk -F\" '/Developer ID Application/ {print $2; exit}')"
if [[ -z "${IDENTITY}" ]]; then
  echo "Developer ID Application identity not found in keychain."
  exit 1
fi

echo "Signing app with identity: ${IDENTITY}"
codesign --force --options runtime --timestamp --sign "${IDENTITY}" --deep "${APP_PATH}"
codesign --verify --deep --strict --verbose=2 "${APP_PATH}"

bash "${REPO_DIR}/scripts/ci/macos_package.sh" "${APP_PATH}"
DMG_PATH="${REPO_DIR}/dist/PurwayGeotagger.dmg"

echo "Submitting for notarization (async)..."

SUBMIT_JSON_PATH="${REPO_DIR}/dist/notarization_submit.json"
SUBMIT_ID_PATH="${REPO_DIR}/dist/notarization_submission_id.txt"
INFO_JSON_PATH="${REPO_DIR}/dist/notarization_info.json"
WAIT_JSON_PATH="${REPO_DIR}/dist/notarization_wait.json"
LOG_JSON_PATH="${REPO_DIR}/dist/notarization_log.json"

SUBMIT_JSON="$(
  xcrun notarytool submit "${DMG_PATH}" \
    --key "${API_KEY}" \
    --key-id "${APPLE_KEY_ID}" \
    --issuer "${APPLE_ISSUER_ID}" \
    --output-format json
)"
printf '%s\n' "${SUBMIT_JSON}" > "${SUBMIT_JSON_PATH}"

SUBMISSION_ID="$(
  python3 - <<'PY' <<<"${SUBMIT_JSON}"
import json
import sys

data = json.load(sys.stdin)
for key in ("id", "uuid", "submissionId", "submission_id", "requestUUID", "request_uuid"):
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        print(value.strip())
        raise SystemExit(0)
raise SystemExit("Unable to locate notarization submission id in JSON output.")
PY
)"
printf '%s\n' "${SUBMISSION_ID}" > "${SUBMIT_ID_PATH}"
echo "Notarization submission id: ${SUBMISSION_ID}"

if [[ -n "${NOTARY_WAIT_TIMEOUT}" ]]; then
  echo "Waiting up to ${NOTARY_WAIT_TIMEOUT} for notarization to complete..."
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
  echo "notarytool wait exit code: ${WAIT_RC}"
fi

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
echo "Notarization status: ${STATUS:-<unknown>}"

STATUS_LC="$(printf '%s' "${STATUS}" | tr '[:upper:]' '[:lower:]')"
if [[ "${STATUS_LC}" == "accepted" ]]; then
  echo "Stapling notarization ticket..."
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
  echo "Running Gatekeeper assessments..."
  spctl --assess --type open -vv "${DMG_PATH}"
fi

echo "Distribution artifact ready: ${DMG_PATH}"
