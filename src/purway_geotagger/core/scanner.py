from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from purway_geotagger.util.paths import is_csv, is_jpg

@dataclass(frozen=True)
class ScanResult:
    photos: list[Path]
    csvs: list[Path]

def scan_inputs(inputs: Iterable[Path]) -> ScanResult:
    """Recursively scan input paths and return all JPG and CSV files.

    - Inputs may be files or directories.
    - Directories are scanned recursively.
    - Duplicate paths are deduplicated.
    """
    photos: set[Path] = set()
    csvs: set[Path] = set()

    for p in inputs:
        p = p.expanduser().resolve()
        if not p.exists():
            continue
        if p.is_file():
            if is_jpg(p):
                photos.add(p)
            elif is_csv(p):
                csvs.add(p)
            continue

        # directory
        for child in p.rglob("*"):
            if not child.is_file():
                continue
            if is_jpg(child):
                photos.add(child)
            elif is_csv(child):
                csvs.add(child)

    return ScanResult(photos=sorted(photos), csvs=sorted(csvs))
