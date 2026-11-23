from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import logging

from purway_geotagger.util.paths import is_csv, is_jpg, is_macos_artifact, is_source_table

@dataclass(frozen=True)
class ScanResult:
    photos: list[Path]
    csvs: list[Path]
    workbooks: list[Path] = field(default_factory=list)

    @property
    def tables(self) -> list[Path]:
        return sorted(self.csvs + self.workbooks)

def scan_inputs(inputs: Iterable[Path]) -> ScanResult:
    """Recursively scan input paths and return all JPG, CSV and XLSX files.

    - Inputs may be files or directories.
    - Directories are scanned recursively.
    - Duplicate paths are deduplicated.
    """
    photos: set[Path] = set()
    csvs: set[Path] = set()
    workbooks: set[Path] = set()

    logger = logging.getLogger(__name__)
    for p in inputs:
        p = p.expanduser().resolve()
        if not p.exists() or is_macos_artifact(p):
            continue
        if p.is_file():
            if is_jpg(p):
                photos.add(p)
            elif is_source_table(p):
                (csvs if is_csv(p) else workbooks).add(p)
            continue

        # directory
        for child in p.rglob("*"):
            if not child.is_file():
                continue
            if is_macos_artifact(child):
                logger.debug("Skipping macOS artifact: %s", child)
                continue
            if is_jpg(child):
                photos.add(child)
            elif is_source_table(child):
                (csvs if is_csv(child) else workbooks).add(child)

    return ScanResult(photos=sorted(photos), csvs=sorted(csvs), workbooks=sorted(workbooks))
