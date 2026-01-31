from __future__ import annotations

from pathlib import Path

from purway_geotagger.parsers.purway_csv import PurwayCSVIndex


def _write_csv(path: Path, text: str, bom: bool = False) -> None:
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(text, encoding=encoding, newline="\n")


def test_parse_csv_with_bom_and_column_variants(tmp_path: Path) -> None:
    csv_path = tmp_path / "Methane.csv"
    _write_csv(
        csv_path,
        "GPSLatitude,GPSLongitude,PPM,Timestamp,Photo\n"
        "34.1234,-117.9876,123,2023-08-30 20:51:00,IMG_0001.jpg\n",
        bom=True,
    )

    index = PurwayCSVIndex.from_csv_files([csv_path])
    assert len(index.records) == 1
    rec = index.records[0]

    assert rec.lat == 34.1234
    assert rec.lon == -117.9876
    assert rec.ppm == 123.0
    assert rec.photo_ref == "IMG_0001.jpg"
    assert rec.timestamp is not None
