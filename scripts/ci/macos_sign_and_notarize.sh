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

echo "Submitting for notarization..."
xcrun notarytool submit "${DMG_PATH}" --key "${API_KEY}" --key-id "${APPLE_KEY_ID}" --issuer "${APPLE_ISSUER_ID}" --wait
xcrun stapler staple "${DMG_PATH}"

echo "Notarization complete: ${DMG_PATH}"
