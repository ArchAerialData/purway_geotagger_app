from __future__ import annotations

from pathlib import Path
import csv

from purway_geotagger.ops.methane_outputs import generate_methane_outputs


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_cleaned_csv_filters_by_matching_jpg(tmp_path: Path) -> None:
    # Create JPGs in same folder as CSV
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "b.jpg").write_bytes(b"")
    (tmp_path / "c.jpg").write_bytes(b"")

    csv_path = tmp_path / "methane.csv"
    fieldnames = ["time", "methane_concentration", "latitude", "longitude", "file_name"]
    rows = [
        {"time": "t1", "methane_concentration": "1500", "latitude": "1", "longitude": "2", "file_name": "a.jpg"},
        {"time": "t2", "methane_concentration": "900", "latitude": "1", "longitude": "2", "file_name": "b.jpg"},
        {"time": "t3", "methane_concentration": "2000", "latitude": "1", "longitude": "2", "file_name": "missing.jpg"},
        {"time": "t4", "methane_concentration": "1200", "latitude": "1", "longitude": "2", "file_name": "c.jpg"},
        {"time": "t5", "methane_concentration": "1500", "latitude": "1", "longitude": "2", "file_name": ""},
    ]
    _write_csv(csv_path, fieldnames, rows)

    results = generate_methane_outputs([csv_path], threshold=1000, generate_kmz=True)
    assert len(results) == 1
    result = results[0]

    assert result.cleaned_status == "success"
    assert result.cleaned_rows == 2  # a.jpg + c.jpg
    assert result.missing_photo_rows == 2  # missing.jpg + blank
    assert result.photo_col_missing is False

    assert result.cleaned_csv is not None and result.cleaned_csv.exists()
    assert result.kmz is not None and result.kmz.exists()
    assert result.kmz_rows == 2

    # Ensure cleaned CSV only includes matching JPG names
    with result.cleaned_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        kept = [row["file_name"] for row in reader]
    assert kept == ["a.jpg", "c.jpg"]


def test_fallback_when_photo_column_missing(tmp_path: Path) -> None:
    csv_path = tmp_path / "methane.csv"
    fieldnames = ["time", "methane_concentration", "latitude", "longitude"]
    rows = [
        {"time": "t1", "methane_concentration": "1500", "latitude": "1", "longitude": "2"},
        {"time": "t2", "methane_concentration": "900", "latitude": "1", "longitude": "2"},
    ]
    _write_csv(csv_path, fieldnames, rows)

    results = generate_methane_outputs([csv_path], threshold=1000, generate_kmz=False)
    assert len(results) == 1
    result = results[0]

    assert result.cleaned_status == "success"
    assert result.cleaned_rows == 1
    assert result.photo_col_missing is True
    assert result.missing_photo_rows == 0
