"""Snapshot build inputs before packaging; reject changes during the build."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def hashes() -> dict[str, str]:
    paths = list((ROOT / "src").rglob("*.py"))
    for folder in ("config", "assets", "scripts/windows", ".github/workflows"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    paths.extend(ROOT.glob("requirements*.txt"))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest().upper()
            for p in sorted(set(paths))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    inputs = hashes()
    if args.verify:
        saved = json.loads(args.output.read_text(encoding="utf-8"))
        if saved["input_sha256"] != inputs:
            raise SystemExit("Build inputs changed during packaging; rebuild before publishing.")
        return
    sys.path.insert(0, str(ROOT / "src"))
    from purway_geotagger import __version__
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    changed = subprocess.check_output(["git", "status", "--porcelain", "--", "src", "config", "assets", "scripts/windows", ".github/workflows", "requirements.txt", "requirements-dev.txt"], cwd=ROOT, text=True).strip()
    now = datetime.now(timezone.utc)
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    info = dict(app_version=__version__, built_at_utc=now.isoformat(), git_revision=revision,
                source_modified=bool(changed), input_fingerprint=fingerprint,
                build_id=f"{now:%Y%m%d-%H%M}-{fingerprint[:8]}",
                input_sha256=inputs,
                source_sha256={p: digest for p, digest in inputs.items() if p.startswith("src/")})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(info, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
