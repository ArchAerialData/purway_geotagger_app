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

    # Results
    status: str = "PENDING"  # SUCCESS|FAILED|SKIPPED|PENDING
    reason: str = ""
    exif_written: bool = False
