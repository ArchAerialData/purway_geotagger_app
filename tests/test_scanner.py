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


def test_scan_inputs_skips_macos_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "root"
    macos_dir = root / "__MACOSX"
    macos_dir.mkdir(parents=True)

    good_csv = root / "data.csv"
    bad_csv = root / "._data.csv"
    ds_store = root / ".DS_Store"
    macos_csv = macos_dir / "data.csv"

    good_csv.write_text("a,b\n1,2\n", encoding="utf-8")
    bad_csv.write_text("x", encoding="utf-8")
    ds_store.write_text("x", encoding="utf-8")
    macos_csv.write_text("a,b\n1,2\n", encoding="utf-8")

    scan = scan_inputs([root])

    assert good_csv in scan.csvs
    assert bad_csv not in scan.csvs
    assert macos_csv not in scan.csvs
