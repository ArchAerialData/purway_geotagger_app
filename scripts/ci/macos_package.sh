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

DMG_PATH="${OUT_DIR}/PurwayGeotagger.dmg"
rm -f "${DMG_PATH}"

hdiutil create -volname "${VOLNAME}" -srcfolder "${APP_PATH}" -ov -format UDZO "${DMG_PATH}"

echo "DMG created: ${DMG_PATH}"
