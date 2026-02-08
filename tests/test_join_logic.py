from __future__ import annotations

from pathlib import Path

import pytest

from purway_geotagger.parsers.purway_csv import (
    PurwayCSVIndex,
    REASON_AMBIGUOUS_TIMESTAMP,
    REASON_NO_FILENAME_TIMESTAMP,
    REASON_NO_PHOTO_OR_TIMESTAMP,
)
from purway_geotagger.util.errors import CorrelationError


def _write_csv(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def test_filename_join_wins_when_photo_column_present(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(
        csv_path,
        "Latitude,Longitude,PPM,Time,SourceFile\n"
        "1.0,2.0,10,2023-08-30 20:51:00,IMG_0001.jpg\n",
    )
    index = PurwayCSVIndex.from_csv_files([csv_path])

    match = index.match_photo(tmp_path / "IMG_0001.jpg", max_join_delta_seconds=3)
    assert match.join_method == "FILENAME"


def test_timestamp_join_nearest_row(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(
        csv_path,
        "Latitude,Longitude,PPM,Timestamp\n"
        "1.0,2.0,10,2023-08-30 20:51:00\n"
        "1.1,2.1,20,2023-08-30 20:51:05\n",
    )
    index = PurwayCSVIndex.from_csv_files([csv_path])

    match = index.match_photo(tmp_path / "2023-08-30_20-51-02.jpg", max_join_delta_seconds=3)
    assert match.join_method == "TIMESTAMP"
    assert match.ppm == 10.0


def test_timestamp_join_ambiguous(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(
        csv_path,
        "Latitude,Longitude,PPM,Timestamp\n"
        "1.0,2.0,10,2023-08-30 20:51:01\n"
        "1.1,2.1,20,2023-08-30 20:51:03\n",
    )
    index = PurwayCSVIndex.from_csv_files([csv_path])

    with pytest.raises(CorrelationError) as excinfo:
        index.match_photo(tmp_path / "2023-08-30_20-51-02.jpg", max_join_delta_seconds=3)
    assert str(excinfo.value) == REASON_AMBIGUOUS_TIMESTAMP


def test_timestamp_join_threshold_fail(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(
        csv_path,
        "Latitude,Longitude,PPM,Timestamp\n"
        "1.0,2.0,10,2023-08-30 20:51:00\n",
    )
    index = PurwayCSVIndex.from_csv_files([csv_path])

    with pytest.raises(CorrelationError) as excinfo:
        index.match_photo(tmp_path / "2023-08-30_20-51-20.jpg", max_join_delta_seconds=3)
    assert "exceeds threshold" in str(excinfo.value)


def test_no_filename_timestamp_reason(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(
        csv_path,
        "Latitude,Longitude,PPM,Timestamp\n"
        "1.0,2.0,10,2023-08-30 20:51:00\n",
    )
    index = PurwayCSVIndex.from_csv_files([csv_path])

    with pytest.raises(CorrelationError) as excinfo:
        index.match_photo(tmp_path / "IMG_0001.jpg", max_join_delta_seconds=3)
    assert str(excinfo.value) == REASON_NO_FILENAME_TIMESTAMP


def test_no_photo_column_and_no_timestamped_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(
        csv_path,
        "Latitude,Longitude,PPM\n"
        "1.0,2.0,10\n",
    )
    index = PurwayCSVIndex.from_csv_files([csv_path])

    with pytest.raises(CorrelationError) as excinfo:
        index.match_photo(tmp_path / "IMG_0001.jpg", max_join_delta_seconds=3)
    assert str(excinfo.value) == REASON_NO_PHOTO_OR_TIMESTAMP
