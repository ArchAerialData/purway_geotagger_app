from __future__ import annotations

from pathlib import Path
import sys

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def is_jpg(p: Path) -> bool:
    return p.suffix.lower() in {".jpg", ".jpeg"}

def is_csv(p: Path) -> bool:
    return p.suffix.lower() == ".csv"

def is_macos_artifact(p: Path) -> bool:
    name = p.name
    if name.startswith("._") or name == ".DS_Store":
        return True
    parts = p.parts
    return "__MACOSX" in parts

def resource_path(relative: Path) -> Path:
    """Return a filesystem path to a packaged resource (PyInstaller-safe)."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / relative
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / relative
