#!/usr/bin/env bash
set -euo pipefail

echo "NOTE: scripts/ci/macos_sign_and_notarize.sh is deprecated." >&2
echo "NOTE: Notarization is disabled; use scripts/ci/macos_sign_and_package.sh instead." >&2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/macos_sign_and_package.sh" "$@"
