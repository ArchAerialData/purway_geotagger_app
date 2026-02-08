#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DMG_PATH="${1:-}"

if [[ -z "${DMG_PATH}" ]]; then
  echo "Usage: $0 /path/to/PurwayGeotagger.dmg"
  exit 2
fi
if [[ ! -f "${DMG_PATH}" ]]; then
  echo "Missing DMG: ${DMG_PATH}"
  exit 2
fi

: "${APPLE_KEY_ID:?Missing APPLE_KEY_ID}"
: "${APPLE_ISSUER_ID:?Missing APPLE_ISSUER_ID}"
: "${APPLE_API_KEY_P8:?Missing APPLE_API_KEY_P8 (base64 .p8)}"

NOTARY_WAIT_TIMEOUT="${NOTARY_WAIT_TIMEOUT:-20m}"
SUBMISSION_ID="${NOTARY_SUBMISSION_ID:-}"

if [[ -z "${SUBMISSION_ID}" ]]; then
  if [[ -f "${REPO_DIR}/dist/notarization_submission_id.txt" ]]; then
    SUBMISSION_ID="$(cat "${REPO_DIR}/dist/notarization_submission_id.txt" | tr -d ' \t\r\n')"
  elif [[ -f "$(dirname "${DMG_PATH}")/notarization_submission_id.txt" ]]; then
    SUBMISSION_ID="$(cat "$(dirname "${DMG_PATH}")/notarization_submission_id.txt" | tr -d ' \t\r\n')"
  fi
fi

if [[ -z "${SUBMISSION_ID}" ]]; then
  echo "Missing notarization submission id."
  echo "Provide NOTARY_SUBMISSION_ID env var, or include notarization_submission_id.txt next to DMG."
  exit 2
fi

WORK_DIR="$(mktemp -d)"
API_KEY="${WORK_DIR}/AuthKey_${APPLE_KEY_ID}.p8"

cleanup() {
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

decode_base64 "${APPLE_API_KEY_P8}" "${API_KEY}"
chmod 600 "${API_KEY}"

echo "Finalizing notarization for: ${DMG_PATH}"
echo "Submission id: ${SUBMISSION_ID}"

info_json() {
  xcrun notarytool info "${SUBMISSION_ID}" \
    --key "${API_KEY}" \
    --key-id "${APPLE_KEY_ID}" \
    --issuer "${APPLE_ISSUER_ID}" \
    --output-format json
}

status_from_json() {
  python3 - <<'PY'
import json
import sys
data = json.load(sys.stdin)
print(str(data.get("status") or data.get("Status") or "").strip())
PY
}

INFO_JSON="$(info_json)"
STATUS="$(printf '%s\n' "${INFO_JSON}" | status_from_json)"
STATUS_LC="$(printf '%s' "${STATUS}" | tr '[:upper:]' '[:lower:]')"
echo "Current status: ${STATUS:-<unknown>}"

if [[ "${STATUS_LC}" != "accepted" && "${STATUS_LC}" != "rejected" && "${STATUS_LC}" != "invalid" ]]; then
  echo "Waiting up to ${NOTARY_WAIT_TIMEOUT} for acceptance..."
  set +e
  xcrun notarytool wait "${SUBMISSION_ID}" \
    --key "${API_KEY}" \
    --key-id "${APPLE_KEY_ID}" \
    --issuer "${APPLE_ISSUER_ID}" \
    --timeout "${NOTARY_WAIT_TIMEOUT}"
  WAIT_RC=$?
  set -e
  echo "notarytool wait exit code: ${WAIT_RC}"

  INFO_JSON="$(info_json)"
  STATUS="$(printf '%s\n' "${INFO_JSON}" | status_from_json)"
  STATUS_LC="$(printf '%s' "${STATUS}" | tr '[:upper:]' '[:lower:]')"
  echo "Status after wait: ${STATUS:-<unknown>}"
fi

if [[ "${STATUS_LC}" == "accepted" ]]; then
  echo "Stapling notarization ticket to DMG..."
  xcrun stapler staple "${DMG_PATH}"
  echo "Running Gatekeeper assessment..."
  spctl --assess --type open -vv "${DMG_PATH}"
  echo "Finalize complete."
  exit 0
fi

if [[ "${STATUS_LC}" == "rejected" || "${STATUS_LC}" == "invalid" ]]; then
  echo "Notarization failed with status: ${STATUS}. Fetching log..."
  xcrun notarytool log "${SUBMISSION_ID}" \
    --key "${API_KEY}" \
    --key-id "${APPLE_KEY_ID}" \
    --issuer "${APPLE_ISSUER_ID}"
  exit 1
fi

echo "Notarization still pending (status: ${STATUS:-unknown}). Re-run finalize later."
exit 3

