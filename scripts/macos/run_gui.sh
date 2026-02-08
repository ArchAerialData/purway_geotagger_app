#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Venv not found. Run: bash scripts/macos/setup_macos.sh"
  exit 1
fi

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"
if [[ -z "${PURWAY_EXIFTOOL_PATH:-}" ]]; then
  VENDORED_EXIFTOOL="$(find "${REPO_DIR}/scripts/macos/vendor" -maxdepth 2 -type f -name exiftool | sort | tail -n 1)"
  if [[ -n "${VENDORED_EXIFTOOL}" ]]; then
    export PURWAY_EXIFTOOL_PATH="${VENDORED_EXIFTOOL}"
  fi
fi
python -m purway_geotagger.app
