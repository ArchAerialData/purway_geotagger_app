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


def test_templates_tab_uses_filename_style_index_preview() -> None:
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
items = [win.templates_list.item(i).text() for i in range(win.templates_list.count())]
has_items = len(items) > 0
has_no_start_prefix = all(" - Start " not in item for item in items)
has_filename_style = all(
    (" - " in item)
    and ("_" in item.rsplit(" - ", 1)[1])
    for item in items
)
print("template_label_format_ok", has_items and has_no_start_prefix and has_filename_style)
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
    assert "template_label_format_ok True" in completed.stdout
