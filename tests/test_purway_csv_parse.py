from __future__ import annotations

from pathlib import Path

from purway_geotagger.parsers.purway_csv import PurwayCSVIndex


def _write_csv(path: Path, text: str, bom: bool = False) -> None:
    encoding = "utf-8-sig" if bom else "utf-8"
    with path.open("w", encoding=encoding, newline="\n") as f:
        f.write(text)


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


def test_parse_csv_skips_non_utf8_files(tmp_path: Path) -> None:
    good = tmp_path / "good.csv"
    bad = tmp_path / "._bad.csv"
    _write_csv(
        good,
        "Latitude,Longitude,PPM,Timestamp\n"
        "1.0,2.0,10,2023-08-30 20:51:00\n",
    )
    bad.write_bytes(b"\xff\xfe\x00\x00")

    index = PurwayCSVIndex.from_csv_files([good, bad])
    assert len(index.records) == 1


def test_parse_model_ii_target_distance_and_diagnostics(tmp_path: Path) -> None:
    csv_path = tmp_path / "methane_model_ii.csv"
    _write_csv(
        csv_path,
        "time,methane_concentration,longitude,latitude,dest_longitude,dest_latitude,"
        "distance,altitude,relative_altitude,file_name,status,err_code,SNR,reliability\n"
        "2026-01-28_23:57:19:149,1500,-97.2,28.1,-97.3,28.2,12.5,40,25,"
        "20260128_235719.jpg,SUCCESS,0,18.5,0.97\n",
    )
    photo = tmp_path / "20260128_235719.jpg"

    match = PurwayCSVIndex.from_csv_files([csv_path]).match_photo(photo, max_join_delta_seconds=3)

    assert match.join_method == "FILENAME"
    assert match.join_delta_seconds == 0.0
    assert match.target_lat == 28.2
    assert match.target_lon == -97.3
    assert match.distance == 12.5
    assert match.source_file_name == "20260128_235719.jpg"
    assert match.source_csv == csv_path.name
    assert match.payload_model == "Purway Model II"
    assert match.csv_status == "SUCCESS"
    assert match.err_code == "0"
    assert match.snr == 18.5
    assert match.reliability == 0.97


def test_parse_model_iii_timestamp_join_source_file_fallback(tmp_path: Path) -> None:
    csv_path = tmp_path / "methane_model_iii.csv"
    _write_csv(
        csv_path,
        "time,methane_concentration,longitude,latitude,dest_longitude,dest_latitude,"
        "distance,file_name,flight_status,dis_code,home_distance,speed\n"
        "2026-01-28_23:57:19:000,1700,-97.2,28.1,-97.4,28.4,22.5,,IN_AIR,D7,120.0,8.2\n",
    )
    photo = tmp_path / "20260128_235719.jpg"

    match = PurwayCSVIndex.from_csv_files([csv_path]).match_photo(photo, max_join_delta_seconds=3)

    assert match.join_method == "TIMESTAMP"
    assert match.join_delta_seconds == 0.0
    assert match.source_file_name == photo.name
    assert match.payload_model == "Purway Model III"
    assert match.flight_status == "IN_AIR"
    assert match.dis_code == "D7"
    assert match.home_distance == 120.0
    assert match.speed == 8.2


def test_target_coordinates_do_not_replace_standard_gps(tmp_path: Path) -> None:
    csv_path = tmp_path / "target_only.csv"
    _write_csv(
        csv_path,
        "methane_concentration,dest_longitude,dest_latitude,distance,file_name\n"
        "1500,-97.3,28.2,12.5,a.jpg\n",
    )

    index = PurwayCSVIndex.from_csv_files([csv_path])

    assert index.records == []
