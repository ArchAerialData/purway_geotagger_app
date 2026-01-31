from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.scanner import scan_inputs


def test_scan_inputs_recurses_and_dedupes(tmp_path: Path) -> None:
    root = tmp_path / "root"
    child = root / "nested"
    child.mkdir(parents=True)

    jpg1 = root / "IMG_0001.JPG"
    jpg2 = child / "img_0002.jpeg"
    csv1 = child / "data.CSV"

    jpg1.write_text("x", encoding="utf-8")
    jpg2.write_text("x", encoding="utf-8")
    csv1.write_text("a,b\n1,2\n", encoding="utf-8")

    # Provide root and one file to test deduplication.
    scan = scan_inputs([root, jpg1])

    assert len(scan.photos) == 2
    assert len(scan.csvs) == 1
    assert jpg1 in scan.photos
    assert jpg2 in scan.photos
    assert csv1 in scan.csvs
