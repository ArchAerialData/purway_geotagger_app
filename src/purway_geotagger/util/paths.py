from __future__ import annotations

from pathlib import Path

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def is_jpg(p: Path) -> bool:
    return p.suffix.lower() in {".jpg", ".jpeg"}

def is_csv(p: Path) -> bool:
    return p.suffix.lower() == ".csv"
