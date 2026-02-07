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


def test_home_page_uses_clickable_mode_cards() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.main_window import MainWindow

app = QApplication([])
win = MainWindow(AppSettings())
cards = list(win.home_page._card_order)
all_clickable = all(card.cursor().shape() == Qt.PointingHandCursor for card in cards)
all_focusable = all(card.focusPolicy() == Qt.StrongFocus for card in cards)
print("home_mode_cards", len(cards), all_clickable, all_focusable)
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
    assert "home_mode_cards 4 True True" in completed.stdout


def test_home_page_wind_card_opens_wind_tab() -> None:
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
start_index = win.main_stack.currentIndex()
win.home_page.wind_data_selected.emit()
app.processEvents()
after_index = win.main_stack.currentIndex()
print("home_wind_card_tab_switch", start_index, after_index)
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
    assert "home_wind_card_tab_switch 0 3" in completed.stdout


def test_home_page_mode_cards_reflow_at_narrow_width() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.gui.pages.home_page import HomePage

app = QApplication([])
page = HomePage()
page.show()
page.resize(1280, 760)
page._relayout_mode_cards()
app.processEvents()
wide_cols = page._current_card_columns
page.resize(860, 760)
page._relayout_mode_cards()
app.processEvents()
narrow_cols = page._current_card_columns
print("home_mode_reflow", wide_cols, narrow_cols)
page.close()
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
    assert "home_mode_reflow 2 2" in completed.stdout
