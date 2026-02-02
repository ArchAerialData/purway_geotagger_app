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
python -m purway_geotagger.app
