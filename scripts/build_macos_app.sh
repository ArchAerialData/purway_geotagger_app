#!/usr/bin/env bash
set -euo pipefail

# Build a macOS .app using PyInstaller.
# NOTE: Code signing/notarization not included.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"

cd "${REPO_DIR}"

pyinstaller --noconfirm --clean \
  --name "PurwayGeotagger" \
  --windowed \
  --onedir \
  --paths "src" \
  --collect-all "PySide6" \
  --add-data "config/default_templates.json:config" \
  "src/purway_geotagger/app.py"

echo "Build complete. See dist/ (or dist/PurwayGeotagger.app depending on flags)."
echo "You will likely want a one-folder build (--onedir) for bundling Qt plugins cleanly."
