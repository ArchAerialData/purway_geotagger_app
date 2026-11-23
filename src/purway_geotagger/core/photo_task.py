from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass
class PhotoTask:
    """Represents one photo through the processing pipeline.

    - src_path: original discovered photo path
    - work_path: current path being modified (either original or a copied version)
    - output_path: final output path after rename/flatten (starts as work_path)
    """
    src_path: Path
    work_path: Path
    output_path: Path

    # Match / metadata
    matched: bool = False
    join_method: str = "NONE"  # FILENAME|TIMESTAMP|NONE
    csv_path: str = ""
    lat: float | None = None
    lon: float | None = None
    ppm: float | None = None
    datetime_original: str | None = None
    image_description: str = ""

    # Extended metadata from CSV
    altitude: float | None = None
    relative_altitude: float | None = None
    light_intensity: float | None = None
    uav_pitch: float | None = None
    uav_roll: float | None = None
    uav_yaw: float | None = None
    gimbal_pitch: float | None = None
    gimbal_roll: float | None = None
    gimbal_yaw: float | None = None
    camera_focal_length: float | None = None
    camera_zoom: float | None = None
    timestamp_raw: str | None = None
    target_lat: float | None = None
    target_lon: float | None = None
    distance: float | None = None
    source_file_name: str = ""
    source_csv: str = ""
    source_sheet: str = ""
    source_row: str = ""
    join_delta_seconds: float | None = None
    payload_model: str = ""
    geotagger_version: str = ""
    geotagger_run_id: str = ""
    csv_status: str = ""
    err_code: str = ""
    snr: float | None = None
    reliability: float | None = None
    flight_status: str = ""
    dis_code: str = ""
    home_distance: float | None = None
    speed: float | None = None

    # Derived fields
    pac: float | None = None  # Path Average Concentration: ppm / relative_altitude

    # Results
    status: str = "PENDING"  # SUCCESS|FAILED|SKIPPED|PENDING
    reason: str = ""
    exif_written: bool = False
