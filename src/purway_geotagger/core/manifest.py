from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from pathlib import Path
import csv

@dataclass
class ManifestRow:
    source_path: str
    output_path: str
    status: str  # SUCCESS|FAILED|SKIPPED
    reason: str
    lat: str
    lon: str
    ppm: str
    csv_path: str
    join_method: str  # FILENAME|TIMESTAMP|NONE
    exif_written: str  # YES|NO
    target_lat: str = ""
    target_lon: str = ""
    distance: str = ""
    source_file_name: str = ""
    source_csv: str = ""
    source_sheet: str = ""
    source_row: str = ""
    join_delta_seconds: str = ""
    payload_model: str = ""
    geotagger_version: str = ""
    geotagger_run_id: str = ""
    csv_status: str = ""
    err_code: str = ""
    snr: str = ""
    reliability: str = ""
    flight_status: str = ""
    dis_code: str = ""
    home_distance: str = ""
    speed: str = ""
    # Extended fields
    altitude: str = ""
    relative_altitude: str = ""
    light_intensity: str = ""
    pac: str = ""
    uav_pitch: str = ""
    uav_roll: str = ""
    uav_yaw: str = ""
    gimbal_pitch: str = ""
    gimbal_roll: str = ""
    gimbal_yaw: str = ""
    camera_focal_length: str = ""
    camera_zoom: str = ""
    capture_time: str = ""

class ManifestWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._rows: list[ManifestRow] = []

    def add(self, row: ManifestRow) -> None:
        self._rows.append(row)

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[field.name for field in fields(ManifestRow)])
            w.writeheader()
            for r in self._rows:
                w.writerow(asdict(r))
