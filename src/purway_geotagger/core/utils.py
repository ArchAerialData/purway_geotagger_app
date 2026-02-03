from __future__ import annotations

import sys
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Path relative to repository root (e.g. 'assets/logo.png')
    
    Returns:
        Absolute Path object
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        # In dev, use repository root relative interpretation
        # This file is in src/purway_geotagger/core/
        # Repo root is 3 levels up: core -> purway_geotagger -> src -> root
        base_path = Path(__file__).resolve().parents[3]

    return base_path / relative_path
