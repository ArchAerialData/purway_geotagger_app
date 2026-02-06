#!/usr/bin/env bash
set -euo pipefail

# Build a macOS .app using PyInstaller.
# NOTE: Code signing/notarization not included.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

# Optional overrides:
#   EXIFTOOL_PATH=/path/to/exiftool
#   BUNDLE_ID=com.yourorg.PurwayGeotagger
EXIFTOOL_PATH="${EXIFTOOL_PATH:-}"
BUNDLE_ID="${BUNDLE_ID:-com.yourorg.PurwayGeotagger}"

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"

cd "${REPO_DIR}"

# Try to locate ExifTool for bundling (preferred for pilot builds).
# 1) Prefer vendored ExifTool in scripts/macos/vendor/Image-ExifTool-*/
EXIFTOOL_LIB_DIR=""
if [[ -z "${EXIFTOOL_PATH}" ]]; then
  VENDOR_DIR="$(ls -d "${REPO_DIR}/scripts/macos/vendor/Image-ExifTool-"* 2>/dev/null | sort | tail -n 1)"
  if [[ -n "${VENDOR_DIR}" && -f "${VENDOR_DIR}/exiftool" ]]; then
    EXIFTOOL_PATH="${VENDOR_DIR}/exiftool"
    EXIFTOOL_LIB_DIR="${VENDOR_DIR}/lib"
  fi
fi

# 2) Fall back to PATH or common locations.
if [[ -z "${EXIFTOOL_PATH}" ]]; then
  if command -v exiftool >/dev/null 2>&1; then
    EXIFTOOL_PATH="$(command -v exiftool)"
  else
    for cand in /opt/homebrew/bin/exiftool /usr/local/bin/exiftool /usr/bin/exiftool; do
      if [[ -x "${cand}" ]]; then
        EXIFTOOL_PATH="${cand}"
        break
      fi
    done
  fi
fi

EXIFTOOL_ARGS=()
if [[ -n "${EXIFTOOL_PATH}" ]]; then
  if [[ ! -x "${EXIFTOOL_PATH}" ]]; then
    chmod +x "${EXIFTOOL_PATH}" || true
  fi
  echo "Bundling ExifTool from: ${EXIFTOOL_PATH}"
  EXIFTOOL_ARGS+=(--add-binary "${EXIFTOOL_PATH}:bin")
  if [[ -n "${EXIFTOOL_LIB_DIR}" && -d "${EXIFTOOL_LIB_DIR}" ]]; then
    EXIFTOOL_ARGS+=(--add-data "${EXIFTOOL_LIB_DIR}:bin/lib")
  fi
else
  echo "ExifTool not found. Build will rely on system ExifTool at runtime."
fi

pyinstaller --noconfirm --clean \
  --name "PurwayGeotagger" \
  --windowed \
  --onedir \
  --osx-bundle-identifier "${BUNDLE_ID}" \
  --paths "src" \
  --add-data "config/default_templates.json:config" \
  --add-data "config/exiftool_config.txt:config" \
  --add-data "assets:assets" \
  "${EXIFTOOL_ARGS[@]}" \
  "src/purway_geotagger/app.py"


echo "Build complete. See dist/ (or dist/PurwayGeotagger.app depending on flags)."
echo "You will likely want a one-folder build (--onedir) for bundling Qt plugins cleanly."
