from __future__ import annotations

from pathlib import Path
import csv

from purway_geotagger.gui.widgets.run_report_view import (
    parse_manifest_failures,
    collect_output_files,
)


def test_parse_manifest_failures(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_path",
                "output_path",
                "status",
                "reason",
                "lat",
                "lon",
                "ppm",
                "csv_path",
                "join_method",
                "exif_written",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "source_path": "/tmp/a.jpg",
            "output_path": "/tmp/out/a.jpg",
            "status": "SUCCESS",
            "reason": "",
            "lat": "",
            "lon": "",
            "ppm": "",
            "csv_path": "",
            "join_method": "FILENAME",
            "exif_written": "YES",
        })
        writer.writerow({
            "source_path": "/tmp/b.jpg",
            "output_path": "",
            "status": "FAILED",
            "reason": "missing gps",
            "lat": "",
            "lon": "",
            "ppm": "",
            "csv_path": "/tmp/m.csv",
            "join_method": "TIMESTAMP",
            "exif_written": "NO",
        })

    failures = parse_manifest_failures(manifest)
    assert len(failures) == 1
    assert failures[0]["source_path"] == "/tmp/b.jpg"
    assert failures[0]["reason"] == "missing gps"


def test_collect_output_files(tmp_path: Path) -> None:
    cleaned_a = tmp_path / "a_cleaned.csv"
    cleaned_b = tmp_path / "b_cleaned.csv"
    kmz_a = tmp_path / "a_cleaned.kmz"
    cleaned_a.write_text("x", encoding="utf-8")
    cleaned_b.write_text("x", encoding="utf-8")
    kmz_a.write_text("x", encoding="utf-8")

    summary = {
        "run_mode": "methane",
        "methane_outputs": [
            {
                "cleaned_csv": str(cleaned_a),
                "cleaned_status": "success",
                "kmz": str(kmz_a),
                "kmz_status": "success",
            },
            {
                "cleaned_csv": str(cleaned_b),
                "cleaned_status": "success",
                "kmz": None,
                "kmz_status": "skipped",
            },
        ],
        "settings": {},
    }
    outputs = collect_output_files(summary, tmp_path)
    paths = [item["path"] for item in outputs]
    assert str(cleaned_a) in paths
    assert str(kmz_a) in paths
    assert str(cleaned_b) in paths


def test_collect_output_files_encroachment(tmp_path: Path) -> None:
    out_dir = tmp_path / "encroach_out"
    out_dir.mkdir()
    jpg = out_dir / "photo_001.jpg"
    jpg.write_text("x", encoding="utf-8")

    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_path",
                "output_path",
                "status",
                "reason",
                "lat",
                "lon",
                "ppm",
                "csv_path",
                "join_method",
                "exif_written",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "source_path": "/tmp/a.jpg",
            "output_path": str(jpg),
            "status": "SUCCESS",
            "reason": "",
            "lat": "",
            "lon": "",
            "ppm": "",
            "csv_path": "",
            "join_method": "FILENAME",
            "exif_written": "YES",
        })

    summary = {
        "run_mode": "encroachment",
        "settings": {
            "encroachment_output_base": str(out_dir),
        },
    }
    outputs = collect_output_files(summary, tmp_path)
    paths = [item["path"] for item in outputs]
    assert str(jpg) in paths
