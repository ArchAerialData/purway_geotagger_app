#!/usr/bin/env bash
set -euo pipefail

# PurwayGeotagger macOS setup script
# - Installs Homebrew (if missing)
# - Installs Python 3.11 and ExifTool via brew
# - Creates venv and installs requirements
#
# Run:
#   bash scripts/macos/setup_macos.sh

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

echo "Repo: ${REPO_DIR}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This setup script is intended for macOS."
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

echo "Updating brew..."
brew update

# Python
if ! brew list python@3.11 >/dev/null 2>&1; then
  echo "Installing python@3.11..."
  brew install python@3.11
fi

# ExifTool
if ! brew list exiftool >/dev/null 2>&1; then
  echo "Installing exiftool..."
  brew install exiftool
fi

PY_BIN="$(brew --prefix python@3.11)/bin/python3.11"
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
exiftool -ver
python -c "import PySide6; print('PySide6 OK')"

echo "Setup complete."
echo "Next: ./scripts/macos/run_gui.sh"
