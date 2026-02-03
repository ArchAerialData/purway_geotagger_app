from __future__ import annotations

from pathlib import Path
import csv

from purway_geotagger.ops.methane_outputs import generate_methane_outputs, cleaned_csv_path


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_cleaned_csv_filters_threshold(tmp_path: Path) -> None:
    src = tmp_path / "methane.csv"
    _write_csv(
        src,
        ["latitude", "longitude", "ppm", "note"],
        [
            ["1.0", "2.0", "500", "low"],
            ["1.1", "2.1", "1500", "high"],
        ],
    )

    results = generate_methane_outputs([src], threshold=1000, generate_kmz=False)
    assert len(results) == 1
    res = results[0]
    assert res.cleaned_status == "success"
    expected = cleaned_csv_path(src, 1000)
    assert res.cleaned_csv == expected
    assert expected.exists()

    lines = expected.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("latitude")
    assert len(lines) == 2
    assert "1500" in lines[1]


def test_cleaned_csv_skips_when_no_ppm(tmp_path: Path) -> None:
    src = tmp_path / "track.csv"
    _write_csv(
        src,
        ["latitude", "longitude", "time"],
        [
            ["1.0", "2.0", "2026-01-01_00:00:00:000"],
        ],
    )

    results = generate_methane_outputs([src], threshold=1000, generate_kmz=False)
    res = results[0]
    assert res.cleaned_status == "skipped"
    assert res.cleaned_csv is None
