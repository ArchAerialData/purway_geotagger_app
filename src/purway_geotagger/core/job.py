from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from purway_geotagger.templates.models import RenameTemplate

@dataclass
class JobOptions:
    output_root: Path
    overwrite_originals: bool
    create_backup_on_overwrite: bool
    flatten: bool
    cleanup_empty_dirs: bool
    sort_by_ppm: bool
    ppm_bin_edges: list[int]
    write_xmp: bool
    dry_run: bool
    max_join_delta_seconds: int
    purway_payload: str

    # renaming
    enable_renaming: bool
    rename_template: Optional[RenameTemplate]
    start_index: int

@dataclass
class JobState:
    stage: str = "PENDING"
    progress: int = 0
    scanned_photos: int = 0
    scanned_csvs: int = 0
    matched: int = 0
    success: int = 0
    failed: int = 0
    message: str = ""

@dataclass
class Job:
    id: str
    name: str
    inputs: list[Path]
    options: JobOptions
    state: JobState = field(default_factory=JobState)
    run_folder: Path | None = None
