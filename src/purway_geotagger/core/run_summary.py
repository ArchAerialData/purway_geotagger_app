from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
from typing import Any


@dataclass
class ExifSummary:
    total: int
    success: int
    failed: int


@dataclass
class MethaneOutputSummary:
    source_csv: str
    cleaned_csv: str | None
    cleaned_status: str
    cleaned_rows: int
    cleaned_error: str
    missing_photo_rows: int = 0
    missing_photo_names: list[str] = field(default_factory=list)
    photo_col_missing: bool = False
    kmz: str | None = None
    kmz_status: str = "skipped"
    kmz_rows: int = 0
    kmz_error: str = ""


@dataclass
class RunSummary:
    run_id: str
    run_mode: str | None
    inputs: list[str]
    settings: dict[str, Any]
    exif: ExifSummary
    methane_outputs: list[MethaneOutputSummary]


def write_run_summary(path: Path, summary: RunSummary) -> None:
    payload = _jsonify(asdict(summary))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _jsonify(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonify(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj
