#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

APP_PATH="${1:-${REPO_DIR}/dist/PurwayGeotagger.app}"
OUT_DIR="${2:-${REPO_DIR}/dist}"
VOLNAME="${3:-PurwayGeotagger}"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Missing app bundle: ${APP_PATH}"
  exit 1
fi

mkdir -p "${OUT_DIR}"


# Create a temporary staging directory
STAGING_DIR="${OUT_DIR}/dmg_staging"
rm -rf "${STAGING_DIR}"
mkdir -p "${STAGING_DIR}"

# Copy valid app bundle to staging
cp -R "${APP_PATH}" "${STAGING_DIR}/"

# Create symlink to /Applications
ln -s /Applications "${STAGING_DIR}/Applications"

DMG_PATH="${OUT_DIR}/PurwayGeotagger.dmg"
rm -f "${DMG_PATH}"

# Create DMG from staging directory
hdiutil create -volname "${VOLNAME}" -srcfolder "${STAGING_DIR}" -ov -format UDZO "${DMG_PATH}"

# Clean up staging
rm -rf "${STAGING_DIR}"

echo "DMG created: ${DMG_PATH}"
