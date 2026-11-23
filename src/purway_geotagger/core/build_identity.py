"""Build identity shown without invoking Git on an end user's workstation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from purway_geotagger import __version__


def build_identity() -> tuple[str, str]:
    if not getattr(sys, "frozen", False):
        return f"v{__version__} · development", "Unpackaged source checkout"
    path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "build-info.json"
    try:
        info = json.loads(path.read_text(encoding="utf-8-sig"))
        version, build_id = info["app_version"], info["build_id"]
        revision = info["git_revision"]
        modified = " + local changes" if info.get("source_modified") else ""
        return (f"v{version} · {build_id}",
                f"Built: {info['built_at_utc']}\nCommit: {revision}{modified}\n"
                f"Build fingerprint: {info['input_fingerprint']}")
    except (OSError, ValueError, KeyError, TypeError):
        return f"v{__version__} · build unknown", "Build metadata is missing or invalid"
