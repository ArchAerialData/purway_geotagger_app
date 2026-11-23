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


def test_rerun_ignores_app_generated_csv_artifacts(tmp_path):
    from purway_geotagger.parsers.purway_csv import PurwayCSVIndex
    source=tmp_path/'flight.csv'
    source.write_text('ppm,relative_altitude,photo,lat,lon\n1500,3,a.jpg,28,-97\n')
    (tmp_path/'a.jpg').touch()
    previous=tmp_path/'PurwayGeotagger_PREVIOUS'; previous.mkdir()
    manifest=previous/'manifest.csv'; manifest.write_text('source_path,lat,lon,ppm\na.jpg,28,-97,1500\n')
    artifact=previous/'_exiftool_import.csv'
    artifact.write_text('DateTimeOriginal,XMP-ArchAerial:CaptureTime\n2026:01:01,2026:01:01\n')
    cleaned=tmp_path/'flight_Cleaned_1000-PPM.csv'; cleaned.write_text(source.read_text())
    for inputs in ([tmp_path], [source,artifact,manifest,cleaned]):
        scan=scan_inputs(inputs)
        assert scan.tables==[source]
        index=PurwayCSVIndex.from_csv_files(scan.tables)
        assert not index.errors
        assert index.match_photo(tmp_path/'a.jpg',3).pac==500
