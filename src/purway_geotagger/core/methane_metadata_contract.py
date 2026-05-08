from __future__ import annotations

from dataclasses import dataclass, field
import math

from purway_geotagger.core.modes import RunMode
from purway_geotagger.core.photo_task import PhotoTask


METADATA_SCHEMA_VERSION = "wwm-methane-xmp-v1"


@dataclass(frozen=True)
class MethaneMetadataValidation:
    valid: bool
    reason: str = ""


@dataclass
class MethaneMetadataSummary:
    schema_version: str = METADATA_SCHEMA_VERSION
    target_coordinates_written: int = 0
    distance_written: int = 0
    invalid_target_distance_rows: int = 0
    join_method_counts: dict[str, int] = field(default_factory=dict)


def requires_target_distance(run_mode: RunMode | None) -> bool:
    return run_mode in (RunMode.METHANE, RunMode.COMBINED)


def validate_target_distance(task: PhotoTask) -> MethaneMetadataValidation:
    reasons: list[str] = []

    target_reason = _target_reason(task.target_lat, task.target_lon)
    if target_reason:
        reasons.append(target_reason)

    if not _is_finite_number(task.distance) or task.distance <= 0:
        reasons.append("distance is blank, zero, or invalid")

    if reasons:
        return MethaneMetadataValidation(
            valid=False,
            reason="missing required methane target/distance metadata: " + "; ".join(reasons),
        )
    return MethaneMetadataValidation(valid=True)


def summarize_methane_metadata(tasks: list[PhotoTask]) -> MethaneMetadataSummary:
    summary = MethaneMetadataSummary()
    for task in tasks:
        if task.matched and task.join_method and task.join_method != "NONE":
            summary.join_method_counts[task.join_method] = summary.join_method_counts.get(task.join_method, 0) + 1
        metadata_written = task.status == "SUCCESS"
        if metadata_written and _target_reason(task.target_lat, task.target_lon) is None:
            summary.target_coordinates_written += 1
        if metadata_written and _is_finite_number(task.distance) and task.distance > 0:
            summary.distance_written += 1
        if task.matched and not validate_target_distance(task).valid:
            summary.invalid_target_distance_rows += 1
    return summary


def _target_reason(lat: float | None, lon: float | None) -> str | None:
    if not _is_finite_number(lat) or not _is_finite_number(lon):
        return "target coordinates are blank or invalid"
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return "target coordinates are outside valid latitude/longitude ranges"
    if lat == 0 and lon == 0:
        return "target coordinates are 0,0"
    return None


def _is_finite_number(value: float | None) -> bool:
    return value is not None and math.isfinite(value)
