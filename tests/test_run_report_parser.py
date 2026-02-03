from __future__ import annotations

from pathlib import Path
import csv

from purway_geotagger.gui.widgets.run_report_view import parse_manifest_failures


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
