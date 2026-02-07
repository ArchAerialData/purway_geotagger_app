from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_main_window_boots_without_header_crash() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.main_window import MainWindow
app = QApplication([])
win = MainWindow(AppSettings())
print("main_window_boot_ok")
win.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "main_window_boot_ok" in completed.stdout
