#!/usr/bin/env bash
set -euo pipefail

# PurwayGeotagger macOS setup script
# - Installs Homebrew (if missing)
# - Installs Python 3.11 and ExifTool via brew
# - Creates venv and installs requirements
#
# Run:
#   bash scripts/macos/setup_macos.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"
LEGACY_VENV="${REPO_DIR}/scripts/.venv"

echo "Script: ${SCRIPT_DIR}"
echo "Repo: ${REPO_DIR}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This setup script is intended for macOS."
  exit 1
fi

if [[ ! -f "${REPO_DIR}/requirements.txt" ]] || [[ ! -d "${REPO_DIR}/src/purway_geotagger" ]]; then
  echo "Could not locate repo root from ${SCRIPT_DIR}."
  echo "Expected: ${REPO_DIR}/requirements.txt and ${REPO_DIR}/src/purway_geotagger/"
  echo "If you moved this script, restore it under scripts/macos/."
  exit 1
fi

if [[ -d "${LEGACY_VENV}" && "${LEGACY_VENV}" != "${VENV_DIR}" ]]; then
  echo "Note: found legacy venv at ${LEGACY_VENV} (created by older script path)."
  echo "It is safe to remove after setup: rm -rf \"${LEGACY_VENV}\""
fi

BREW_BIN=""
if command -v brew >/dev/null 2>&1; then
  BREW_BIN="$(command -v brew)"
elif [[ -x "/opt/homebrew/bin/brew" ]]; then
  BREW_BIN="/opt/homebrew/bin/brew"
elif [[ -x "/usr/local/bin/brew" ]]; then
  BREW_BIN="/usr/local/bin/brew"
fi

if [[ -z "${BREW_BIN}" ]]; then
  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -x "/opt/homebrew/bin/brew" ]]; then
    BREW_BIN="/opt/homebrew/bin/brew"
  elif [[ -x "/usr/local/bin/brew" ]]; then
    BREW_BIN="/usr/local/bin/brew"
  fi
fi

if [[ -z "${BREW_BIN}" ]]; then
  echo "Homebrew install completed but brew is still not available."
  echo "Try opening a new terminal or ensure Homebrew is on PATH."
  exit 1
fi

BREW_PREFIX="$("${BREW_BIN}" --prefix)"
if [[ -d "${BREW_PREFIX}/bin" && ":${PATH}:" != *":${BREW_PREFIX}/bin:"* ]]; then
  export PATH="${BREW_PREFIX}/bin:${PATH}"
fi

echo "Updating brew..."
"${BREW_BIN}" update

# Python
if ! "${BREW_BIN}" list python@3.11 >/dev/null 2>&1; then
  echo "Installing python@3.11..."
  "${BREW_BIN}" install python@3.11
fi

# ExifTool
if ! "${BREW_BIN}" list exiftool >/dev/null 2>&1; then
  echo "Installing exiftool..."
  "${BREW_BIN}" install exiftool
fi

PY_BIN="$("${BREW_BIN}" --prefix python@3.11)/bin/python3.11"
if [[ ! -x "${PY_BIN}" ]]; then
  echo "python@3.11 not found at ${PY_BIN}."
  exit 1
fi
echo "Using Python: ${PY_BIN}"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating venv at ${VENV_DIR} ..."
  "${PY_BIN}" -m venv "${VENV_DIR}"
else
  echo "Using existing venv at ${VENV_DIR}"
fi

# Activate venv
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "${REPO_DIR}/requirements.txt"
if [[ -f "${REPO_DIR}/requirements-dev.txt" ]]; then
  python -m pip install -r "${REPO_DIR}/requirements-dev.txt"
fi

echo "Verifying installs..."
python --version
EXIFTOOL_BIN="$(command -v exiftool || true)"
if [[ -z "${EXIFTOOL_BIN}" && -x "${BREW_PREFIX}/bin/exiftool" ]]; then
  EXIFTOOL_BIN="${BREW_PREFIX}/bin/exiftool"
fi
if [[ -z "${EXIFTOOL_BIN}" ]]; then
  echo "ExifTool not found on PATH after installation."
  echo "Try opening a new terminal or run: ${BREW_PREFIX}/bin/exiftool -ver"
  exit 1
fi
"${EXIFTOOL_BIN}" -ver
python -c "import PySide6; print('PySide6 OK')"

echo "Setup complete."
echo "Next: ./scripts/macos/run_gui.sh"
