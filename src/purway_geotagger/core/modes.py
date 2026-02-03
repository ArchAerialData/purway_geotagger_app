from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable
import os


class RunMode(str, Enum):
    METHANE = "methane"
    ENCROACHMENT = "encroachment"
    COMBINED = "combined"


def _normalize_root(path: Path) -> Path:
    p = path.expanduser()
    return p if p.is_dir() else p.parent


def common_parent(paths: Iterable[Path]) -> Path | None:
    items = [str(_normalize_root(p)) for p in paths if str(p).strip()]
    if not items:
        return None
    try:
        common = os.path.commonpath(items)
    except ValueError:
        return None
    return Path(common)


def default_methane_log_base(inputs: Iterable[Path]) -> Path | None:
    roots = list(inputs)
    if not roots:
        return None
    base = common_parent(roots)
    return base if base is not None else _normalize_root(roots[0])


def default_encroachment_base(inputs: Iterable[Path], folder_name: str = "Encroachment_Output") -> Path | None:
    roots = list(inputs)
    if not roots:
        return None
    base = common_parent(roots)
    if base is None:
        base = _normalize_root(roots[0])
    return _unique_path(base / folder_name)


def encroachment_run_base(output_base: Path) -> Path:
    """Return a sibling folder for run artifacts/logs."""
    return output_base.parent / f"{output_base.name}_RunLogs"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 10_000):
        candidate = path.parent / f"{path.name}_{i}"
        if not candidate.exists():
            return candidate
    return path
