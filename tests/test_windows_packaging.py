"""Offline dependency integrity and failed-stage preservation checks."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_vendored_exiftool_complete_and_verified():
    vendor = ROOT / "scripts/windows/vendor"
    manifest = json.loads((vendor / "exiftool.json").read_text())
    archive = vendor / manifest["archive"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest().upper() == manifest["sha256"]
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        names = bundle.namelist()
        prefix = f"exiftool-{manifest['version']}_64/"
        assert prefix + "exiftool(-k).exe" in names
        assert any(name.startswith(prefix + "exiftool_files/") and name.endswith("LICENSE") for name in names)


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell staging runs on Windows")
def test_corrupt_exiftool_never_replaces_previous_stage(tmp_path):
    script = tmp_path / "stage_exiftool.ps1"
    shutil.copyfile(ROOT / "scripts/windows/stage_exiftool.ps1", script)
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "broken.zip").write_bytes(b"corrupt archive")
    (vendor / "exiftool.json").write_text(json.dumps(dict(version="13.50", archive="broken.zip", sha256="0" * 64)))
    stage = tmp_path / "build/stage"
    stage.mkdir(parents=True)
    sentinel = stage / "previous.txt"
    sentinel.write_text("keep existing payload")
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        "-Version", "13.50", "-BuildDir", str(tmp_path / "build"), "-StageDir", str(stage),
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert "checksum mismatch" in result.stderr
    assert sentinel.read_text() == "keep existing payload"
