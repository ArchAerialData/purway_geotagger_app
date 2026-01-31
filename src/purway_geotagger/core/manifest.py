from __future__ import annotations

from dataclasses import dataclass, asdict
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

class ManifestWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._rows: list[ManifestRow] = []

    def add(self, row: ManifestRow) -> None:
        self._rows.append(row)

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(self._rows[0]).keys()) if self._rows else [
                "source_path","output_path","status","reason","lat","lon","ppm","csv_path","join_method","exif_written"
            ])
            w.writeheader()
            for r in self._rows:
                w.writerow(asdict(r))
