"""Shared CSV/workbook field aliases and unambiguous column resolution."""
from __future__ import annotations

import re


def normalize_header(value: object) -> str:
    return re.sub(r"[\s_-]+", "", str(value or "")).casefold()


def pick_column(cols: list[str], candidates: list[str], exclude_substrings: list[str] | None = None) -> str | None:
    """Prefer exact aliases in priority order; reject ties instead of guessing."""
    excluded = [normalize_header(s) for s in (exclude_substrings or [])]
    eligible = [c for c in cols if not any(e in normalize_header(c) for e in excluded)]
    # Only the two documented canonical measurement headers take precedence.
    canonical = normalize_header(candidates[0])
    if canonical in {"methaneconcentration", "relativealtitude"}:
        matches = [c for c in eligible if normalize_header(c) == canonical]
        if len(matches) == 1:
            return matches[0]
    aliases = {normalize_header(alias) for alias in candidates}
    matches = [c for c in eligible if normalize_header(c) in aliases]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous column for {candidates[0]}: {matches}")
    if matches:
        return matches[0]
    matches = [c for c in eligible if any(normalize_header(a) in normalize_header(c) for a in candidates)]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous column for {candidates[0]}: {matches}")
    return matches[0] if matches else None


def pac_column(cols: list[str]) -> str | None:
    matches = [c for c in cols if c.strip().casefold() == "pac"]
    if len(matches) > 1:
        raise ValueError("Multiple PAC columns; keep a single unambiguous PAC header.")
    return matches[0] if matches else None

PHOTO_COL_CANDIDATES = ["photo", "image", "filename", "file", "sourcefile"]
LAT_COL_CANDIDATES = ["latitude", "lat", "gpslatitude"]
LON_COL_CANDIDATES = ["longitude", "lon", "lng", "gpslongitude"]
TIME_COL_CANDIDATES = ["timestamp", "time", "datetime", "date"]
PPM_COL_CANDIDATES = ["methane_concentration", "concentration", "ppm", "methane", "ch4"]

# Extended metadata column candidates
ALT_COL_CANDIDATES = ["altitude", "alt", "gpsaltitude"]
REL_ALT_COL_CANDIDATES = ["relative_altitude", "rel_alt", "agl", "height_agl"]
LIGHT_COL_CANDIDATES = ["light_intensity", "light", "lux", "brightness"]
UAV_PITCH_CANDIDATES = ["uav_pitch", "pitch"]
UAV_ROLL_CANDIDATES = ["uav_roll", "roll"]
UAV_YAW_CANDIDATES = ["uav_yaw", "yaw", "heading"]
GIMBAL_PITCH_CANDIDATES = ["gimbal_pitch", "cam_pitch"]
GIMBAL_ROLL_CANDIDATES = ["gimbal_roll", "cam_roll"]
GIMBAL_YAW_CANDIDATES = ["gimbal_yaw", "cam_yaw"]
FOCAL_LENGTH_CANDIDATES = ["camera_focal_length", "focal_length", "focal", "lens_focal"]
ZOOM_CANDIDATES = ["camera_zoom", "zoom", "digital_zoom", "zoom_ratio"]
TARGET_LAT_COL_CANDIDATES = ["dest_latitude", "target_latitude", "target_lat", "destination_latitude", "destination_lat"]
TARGET_LON_COL_CANDIDATES = ["dest_longitude", "target_longitude", "target_lon", "destination_longitude", "destination_lon"]
DISTANCE_COL_CANDIDATES = ["distance", "target_distance", "methane_distance"]
STATUS_COL_CANDIDATES = ["status"]
ERR_CODE_COL_CANDIDATES = ["err_code", "error_code"]
SNR_COL_CANDIDATES = ["snr"]
RELIABILITY_COL_CANDIDATES = ["reliability"]
FLIGHT_STATUS_COL_CANDIDATES = ["flight_status"]
DIS_CODE_COL_CANDIDATES = ["dis_code"]
HOME_DISTANCE_COL_CANDIDATES = ["home_distance"]
SPEED_COL_CANDIDATES = ["speed"]


def validate_mappings(columns: list[str]) -> None:
    """Reject ambiguous table mappings before either matching or exporting any rows."""
    groups = (
        PPM_COL_CANDIDATES, REL_ALT_COL_CANDIDATES, PHOTO_COL_CANDIDATES, TIME_COL_CANDIDATES,
        LIGHT_COL_CANDIDATES, UAV_PITCH_CANDIDATES, UAV_ROLL_CANDIDATES,
        UAV_YAW_CANDIDATES, GIMBAL_PITCH_CANDIDATES, GIMBAL_ROLL_CANDIDATES, GIMBAL_YAW_CANDIDATES,
        FOCAL_LENGTH_CANDIDATES, ZOOM_CANDIDATES, TARGET_LAT_COL_CANDIDATES, TARGET_LON_COL_CANDIDATES,
        DISTANCE_COL_CANDIDATES, STATUS_COL_CANDIDATES, ERR_CODE_COL_CANDIDATES, SNR_COL_CANDIDATES,
        RELIABILITY_COL_CANDIDATES, FLIGHT_STATUS_COL_CANDIDATES, DIS_CODE_COL_CANDIDATES,
        HOME_DISTANCE_COL_CANDIDATES, SPEED_COL_CANDIDATES,
    )
    for aliases in groups:
        pick_column(columns, aliases)
    pick_column(columns, ALT_COL_CANDIDATES, REL_ALT_COL_CANDIDATES)
    pick_column(columns, LAT_COL_CANDIDATES, ["dest_lat", "target_lat", "destination_lat"])
    pick_column(columns, LON_COL_CANDIDATES, ["dest_lon", "target_lon", "destination_lon"])
    pac_column(columns)

