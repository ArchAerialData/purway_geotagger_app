#!/usr/bin/env bash
set -euo pipefail

# Sign + notarize a macOS .app so pilots avoid Gatekeeper popups.
#
# Prereqs:
# - Apple Developer account
# - "Developer ID Application" certificate installed in Keychain
# - Notarytool profile created:
#     xcrun notarytool store-credentials "AC_PROFILE" --apple-id "you@domain" --team-id "TEAMID" --password "app-specific-password"
#
# Usage:
#   CODESIGN_IDENTITY="Developer ID Application: Name (TEAMID)" \
#   NOTARY_PROFILE="AC_PROFILE" \
#   ./scripts/macos/sign_and_notarize.sh "dist/PurwayGeotagger.app"

APP_PATH="${1:-}"
if [[ -z "${APP_PATH}" ]]; then
  echo "Usage: CODESIGN_IDENTITY=... NOTARY_PROFILE=... $0 /path/to/PurwayGeotagger.app"
  exit 1
fi

if [[ ! -d "${APP_PATH}" ]]; then
  echo "App not found: ${APP_PATH}"
  exit 1
fi

IDENTITY="${CODESIGN_IDENTITY:-}"
if [[ -z "${IDENTITY}" ]]; then
  echo "Missing CODESIGN_IDENTITY env var (Developer ID Application cert)."
  exit 1
fi

PROFILE="${NOTARY_PROFILE:-}"
if [[ -z "${PROFILE}" ]]; then
  echo "Missing NOTARY_PROFILE env var (notarytool profile name)."
  exit 1
fi

echo "Signing app with identity: ${IDENTITY}"
codesign --force --options runtime --timestamp --sign "${IDENTITY}" --deep "${APP_PATH}"

ZIP_PATH="${APP_PATH%.*}.zip"
echo "Creating notarization zip: ${ZIP_PATH}"
ditto -c -k --sequesterRsrc --keepParent "${APP_PATH}" "${ZIP_PATH}"

echo "Submitting to Apple Notary Service..."
xcrun notarytool submit "${ZIP_PATH}" --keychain-profile "${PROFILE}" --wait

echo "Stapling notarization ticket..."
xcrun stapler staple "${APP_PATH}"

echo "Verifying Gatekeeper status..."
spctl -a -vv "${APP_PATH}"

echo "Done."
