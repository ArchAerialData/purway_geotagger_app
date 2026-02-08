#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python}"

if [[ ! -d ".venv" ]]; then
  "${PYTHON_BIN}" -m venv .venv
fi

# shellcheck disable=SC1091
source ".venv/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt

export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-13.0}"

# Prefer vendored ExifTool for deterministic tests/builds and portable app bundling.
VENDORED_EXIFTOOL="$(find "${REPO_DIR}/scripts/macos/vendor" -maxdepth 2 -type f -name exiftool | sort | tail -n 1)"
if [[ -n "${VENDORED_EXIFTOOL}" ]]; then
  chmod +x "${VENDORED_EXIFTOOL}" || true
  export PURWAY_EXIFTOOL_PATH="${VENDORED_EXIFTOOL}"
  export EXIFTOOL_PATH="${VENDORED_EXIFTOOL}"
  echo "Using vendored ExifTool: ${VENDORED_EXIFTOOL}"
else
  echo "WARNING: Vendored ExifTool not found under scripts/macos/vendor."
fi

python -m pytest

bash scripts/macos/build_app.sh

APP_PATH="dist/PurwayGeotagger.app"
if [[ ! -d "${APP_PATH}" ]]; then
  echo "Build failed: ${APP_PATH} not found."
  exit 1
fi

echo "Build complete: ${APP_PATH}"
