from __future__ import annotations

from pathlib import Path
import csv

import pytest

from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.exif.exiftool_writer import (
    ExifToolWriter,
    ExifWriteResult,
    _gps_lat_ref,
    _gps_lon_ref,
)
from purway_geotagger.util.errors import ExifToolError


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_gps_ref_helpers() -> None:
    assert _gps_lat_ref(12.3) == "N"
    assert _gps_lat_ref(-0.1) == "S"
    assert _gps_lat_ref(0.0) == "N"
    assert _gps_lon_ref(45.6) == "E"
    assert _gps_lon_ref(-45.6) == "W"
    assert _gps_lon_ref(0.0) == "E"


def test_import_csv_includes_refs_and_xmp(tmp_path: Path) -> None:
    writer = ExifToolWriter(write_xmp=True, dry_run=True)
    t = PhotoTask(
        src_path=tmp_path / "a.jpg",
        work_path=tmp_path / "a.jpg",
        output_path=tmp_path / "a.jpg",
        matched=True,
    )
    t.lat = -12.3
    t.lon = 45.6
    t.datetime_original = "2023:08:30 20:51:00"
    t.image_description = "ppm=10; source_csv=data.csv; purway_payload=PAYLOAD"

    out = tmp_path / "import.csv"
    writer._write_import_csv(out, [t])

    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert rows
    row = rows[0]
    assert "GPSLatitudeRef" in row
    assert "GPSLongitudeRef" in row
    assert "XMP:Description" in row
    assert row["GPSLatitudeRef"] == "S"
    assert row["GPSLongitudeRef"] == "E"
    assert "purway_payload=PAYLOAD" in row["ImageDescription"]
    assert row["XMP:Description"] == row["ImageDescription"]


def test_write_tasks_raises_on_exiftool_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    writer = ExifToolWriter(write_xmp=True, dry_run=False)
    t = PhotoTask(
        src_path=tmp_path / "a.jpg",
        work_path=tmp_path / "a.jpg",
        output_path=tmp_path / "a.jpg",
        matched=True,
    )
    t.lat = 1.0
    t.lon = 2.0
    t.image_description = "ppm=1; source_csv=data.csv"

    def fake_run(*_args, **_kwargs):
        return _Proc(returncode=1, stderr="boom")

    monkeypatch.setattr("purway_geotagger.exif.exiftool_writer.subprocess.run", fake_run)

    with pytest.raises(ExifToolError):
        writer.write_tasks(
            tasks=[t],
            work_dir=tmp_path,
            progress_cb=lambda *_: None,
            cancel_cb=lambda: False,
        )


def test_dry_run_skips_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    writer = ExifToolWriter(write_xmp=True, dry_run=True)
    t = PhotoTask(
        src_path=tmp_path / "a.jpg",
        work_path=tmp_path / "a.jpg",
        output_path=tmp_path / "a.jpg",
        matched=True,
    )
    t.lat = 1.0
    t.lon = 2.0
    t.image_description = "ppm=1; source_csv=data.csv"

    def fake_run(*_args, **_kwargs):
        raise AssertionError("subprocess.run should not be called in dry run")

    monkeypatch.setattr("purway_geotagger.exif.exiftool_writer.subprocess.run", fake_run)

    results = writer.write_tasks(
        tasks=[t],
        work_dir=tmp_path,
        progress_cb=lambda *_: None,
        cancel_cb=lambda: False,
    )
    assert results[t.output_path].success is True


def test_write_tasks_verifies_per_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    writer = ExifToolWriter(write_xmp=True, dry_run=False)
    t = PhotoTask(
        src_path=tmp_path / "a.jpg",
        work_path=tmp_path / "a.jpg",
        output_path=tmp_path / "a.jpg",
        matched=True,
    )
    t.lat = 1.0
    t.lon = 2.0
    t.image_description = "ppm=1; source_csv=data.csv"

    verified_csv = (
        "SourceFile,GPSLatitude,GPSLongitude,GPSLatitudeRef,GPSLongitudeRef\n"
        f"{t.output_path.resolve()},1,2,N,E\n"
    )

    calls = {"n": 0}

    def fake_run(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Proc(returncode=0, stdout="", stderr="")
        return _Proc(returncode=0, stdout=verified_csv, stderr="")

    monkeypatch.setattr("purway_geotagger.exif.exiftool_writer.subprocess.run", fake_run)

    results = writer.write_tasks(
        tasks=[t],
        work_dir=tmp_path,
        progress_cb=lambda *_: None,
        cancel_cb=lambda: False,
    )
    assert results[t.output_path] == ExifWriteResult(success=True)
