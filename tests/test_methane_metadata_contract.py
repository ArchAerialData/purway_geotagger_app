from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.methane_metadata_contract import (
    requires_target_distance,
    summarize_methane_metadata,
    validate_target_distance,
)
from purway_geotagger.core.modes import RunMode
from purway_geotagger.core.photo_task import PhotoTask


def _task(tmp_path: Path) -> PhotoTask:
    photo = tmp_path / "a.jpg"
    return PhotoTask(src_path=photo, work_path=photo, output_path=photo, matched=True)


def test_valid_target_distance_passes(tmp_path: Path) -> None:
    task = _task(tmp_path)
    task.target_lat = 28.2
    task.target_lon = -97.3
    task.distance = 12.5

    result = validate_target_distance(task)

    assert result.valid is True
    assert result.reason == ""


def test_blank_target_fails(tmp_path: Path) -> None:
    task = _task(tmp_path)
    task.target_lat = None
    task.target_lon = -97.3
    task.distance = 12.5

    result = validate_target_distance(task)

    assert result.valid is False
    assert "target coordinates" in result.reason


def test_zero_zero_target_fails(tmp_path: Path) -> None:
    task = _task(tmp_path)
    task.target_lat = 0.0
    task.target_lon = 0.0
    task.distance = 12.5

    result = validate_target_distance(task)

    assert result.valid is False
    assert "0,0" in result.reason


def test_blank_distance_fails(tmp_path: Path) -> None:
    task = _task(tmp_path)
    task.target_lat = 28.2
    task.target_lon = -97.3
    task.distance = None

    result = validate_target_distance(task)

    assert result.valid is False
    assert "distance" in result.reason


def test_strictness_applies_only_to_methane_modes() -> None:
    assert requires_target_distance(RunMode.METHANE) is True
    assert requires_target_distance(RunMode.COMBINED) is True
    assert requires_target_distance(RunMode.ENCROACHMENT) is False
    assert requires_target_distance(None) is False


def test_metadata_summary_counts_fields_and_join_methods(tmp_path: Path) -> None:
    valid = _task(tmp_path)
    valid.join_method = "FILENAME"
    valid.target_lat = 28.2
    valid.target_lon = -97.3
    valid.distance = 12.5
    valid.status = "SUCCESS"

    invalid = _task(tmp_path)
    invalid.join_method = "TIMESTAMP"
    invalid.target_lat = 0.0
    invalid.target_lon = 0.0
    invalid.distance = None

    summary = summarize_methane_metadata([valid, invalid])

    assert summary.target_coordinates_written == 1
    assert summary.distance_written == 1
    assert summary.invalid_target_distance_rows == 1
    assert summary.join_method_counts == {"FILENAME": 1, "TIMESTAMP": 1}
