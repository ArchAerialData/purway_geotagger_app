from __future__ import annotations

import os
import sys

def configure_macos_app_identity() -> None:
    """Set macOS-specific Qt app identity.

    NOTE: In a signed .app you may want to set CFBundleName/Identifier in packaging.
    For development this helps with menu naming and settings storage.
    """
    if sys.platform != "darwin":
        return

    # Optional: set organization/app name for QSettings if used later.
    os.environ.setdefault("PURWAY_GEOTAGGER_ORG", "YourOrg")
    os.environ.setdefault("PURWAY_GEOTAGGER_APP", "PurwayGeotagger")


import subprocess
from pathlib import Path

def open_in_finder(path: Path) -> None:
    """Open a folder (or file) in Finder on macOS; best-effort on other OSes."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=False)
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", str(path)], check=False)
    except Exception:
        pass
