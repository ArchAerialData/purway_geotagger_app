#!/usr/bin/env bash
set -euo pipefail

# Build a macOS .app using PyInstaller.
# NOTE: Code signing/notarization not included.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

# Optional overrides:
#   EXIFTOOL_PATH=/path/to/exiftool
#   BUNDLE_ID=com.archaerial.purwaygeotagger
EXIFTOOL_PATH="${EXIFTOOL_PATH:-}"
BUNDLE_ID="${BUNDLE_ID:-com.archaerial.purwaygeotagger}"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Missing venv at ${VENV_DIR}."
  echo "Run: bash scripts/macos/setup_macos.sh"
  exit 1
fi

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"

cd "${REPO_DIR}"

# Try to locate ExifTool for bundling (preferred for pilot builds).
# 1) Prefer vendored ExifTool in scripts/macos/vendor/Image-ExifTool-*/
EXIFTOOL_LIB_DIR=""
VENDOR_ROOT="${REPO_DIR}/scripts/macos/vendor"
VENDOR_DIR=""

if [[ -d "${VENDOR_ROOT}" ]]; then
  VENDOR_DIR="$(find "${VENDOR_ROOT}" -maxdepth 1 -type d -name 'Image-ExifTool-*' | sort | tail -n 1)"
  if [[ -z "${VENDOR_DIR}" ]]; then
    VENDOR_ARCHIVE="$(find "${VENDOR_ROOT}" -maxdepth 1 -type f -name 'Image-ExifTool-*.tar.gz' | sort | tail -n 1)"
    if [[ -n "${VENDOR_ARCHIVE}" ]]; then
      echo "Extracting vendored ExifTool archive: ${VENDOR_ARCHIVE}"
      tar -xzf "${VENDOR_ARCHIVE}" -C "${VENDOR_ROOT}"
      VENDOR_DIR="$(find "${VENDOR_ROOT}" -maxdepth 1 -type d -name 'Image-ExifTool-*' | sort | tail -n 1)"
    fi
  fi
fi

if [[ -z "${EXIFTOOL_PATH}" ]]; then
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
if [[ -z "${EXIFTOOL_PATH}" ]]; then
  echo "ERROR: ExifTool not found for bundling."
  echo "Expected vendored ExifTool under scripts/macos/vendor/Image-ExifTool-*/exiftool"
  echo "or pass EXIFTOOL_PATH=/path/to/exiftool."
  exit 1
fi

if [[ ! -x "${EXIFTOOL_PATH}" ]]; then
  chmod +x "${EXIFTOOL_PATH}" || true
fi
if [[ -z "${EXIFTOOL_LIB_DIR}" ]]; then
  EXIFTOOL_DIR="$(cd "$(dirname "${EXIFTOOL_PATH}")" && pwd)"
  if [[ -d "${EXIFTOOL_DIR}/lib" ]]; then
    EXIFTOOL_LIB_DIR="${EXIFTOOL_DIR}/lib"
  fi
fi
if [[ -z "${EXIFTOOL_LIB_DIR}" || ! -d "${EXIFTOOL_LIB_DIR}" ]]; then
  echo "ERROR: ExifTool lib directory not found for portable bundling."
  echo "Resolved ExifTool path: ${EXIFTOOL_PATH}"
  exit 1
fi

echo "Bundling ExifTool from: ${EXIFTOOL_PATH}"
echo "Bundling ExifTool libs from: ${EXIFTOOL_LIB_DIR}"
EXIFTOOL_ARGS+=(--add-binary "${EXIFTOOL_PATH}:bin")
EXIFTOOL_ARGS+=(--add-data "${EXIFTOOL_LIB_DIR}:bin/lib")

pyinstaller --noconfirm --clean \
  --name "PurwayGeotagger" \
  --windowed \
  --onedir \
  --specpath "build" \
  --osx-bundle-identifier "${BUNDLE_ID}" \
  --paths "${REPO_DIR}/src" \
  --add-data "${REPO_DIR}/config/default_templates.json:config" \
  --add-data "${REPO_DIR}/config/wind_templates:config/wind_templates" \
  --add-data "${REPO_DIR}/config/exiftool_config.txt:config" \
  --add-data "${REPO_DIR}/assets:assets" \
  "${EXIFTOOL_ARGS[@]}" \
  "${REPO_DIR}/src/purway_geotagger/app.py"

APP_RESOURCES="${REPO_DIR}/dist/PurwayGeotagger.app/Contents/Resources"
BUNDLED_EXIFTOOL="${APP_RESOURCES}/bin/exiftool"
BUNDLED_EXIFTOOL_LIB="${APP_RESOURCES}/bin/lib"

for rel in \
  "config/default_templates.json" \
  "config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx" \
  "config/exiftool_config.txt" \
  "assets"
do
  if [[ ! -e "${APP_RESOURCES}/${rel}" ]]; then
    echo "ERROR: Missing bundled resource: ${APP_RESOURCES}/${rel}"
    exit 1
  fi
done

if [[ ! -x "${BUNDLED_EXIFTOOL}" ]]; then
  echo "ERROR: Missing bundled ExifTool at ${BUNDLED_EXIFTOOL}"
  exit 1
fi
if [[ ! -d "${BUNDLED_EXIFTOOL_LIB}" ]]; then
  echo "ERROR: Missing bundled ExifTool lib directory at ${BUNDLED_EXIFTOOL_LIB}"
  exit 1
fi
if grep -q "Cellar/exiftool" "${BUNDLED_EXIFTOOL}"; then
  echo "ERROR: Bundled ExifTool references Homebrew Cellar paths and is not portable."
  echo "Use vendored ExifTool distribution (scripts/macos/vendor/Image-ExifTool-*/)."
  exit 1
fi
PERL5LIB="" "${BUNDLED_EXIFTOOL}" -ver >/dev/null


echo "Build complete. See dist/ (or dist/PurwayGeotagger.app depending on flags)."
echo "You will likely want a one-folder build (--onedir) for bundling Qt plugins cleanly."
