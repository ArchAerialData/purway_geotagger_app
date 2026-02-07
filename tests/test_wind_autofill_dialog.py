from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_wind_autofill_dialog_opens_and_closes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.pages.wind_data_page import WindDataPage

app = QApplication([])
page = WindDataPage(AppSettings())
page._open_autofill_dialog()
dialog = page._autofill_dialog
assert dialog is not None
print("autofill_dialog_opened")
dialog.reject()
page.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "autofill_dialog_opened" in completed.stdout


def test_wind_autofill_dialog_search_busy_keeps_typing_enabled() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.gui.widgets.wind_autofill_dialog import WindAutofillDialog

app = QApplication([])
dialog = WindAutofillDialog(start_time_24h="10:00", end_time_24h="13:00")
dialog.query_edit.setText("hou")
dialog.query_edit.setFocus()
dialog.set_busy(True, allow_typing_when_busy=True)
print("typing_enabled", dialog.query_edit.isEnabled())
dialog.set_busy(False)
dialog.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "typing_enabled True" in completed.stdout


def test_wind_autofill_dialog_has_popup_target_time_controls() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTime
from purway_geotagger.gui.widgets.wind_autofill_dialog import WindAutofillDialog

app = QApplication([])
dialog = WindAutofillDialog(start_time_24h="10:30", end_time_24h="17:00")
print("defaults", dialog.selected_start_time_24h(), dialog.selected_end_time_24h())
dialog.start_time_edit.setTime(QTime.fromString("1:15", "h:mm"))
dialog.start_meridiem_combo.setCurrentText("PM")
dialog.end_time_edit.setTime(QTime.fromString("5:45", "h:mm"))
dialog.end_meridiem_combo.setCurrentText("PM")
print("edited", dialog.selected_start_time_24h(), dialog.selected_end_time_24h())
dialog.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "defaults 10:30 17:00" in completed.stdout
    assert "edited 13:15 17:45" in completed.stdout


def test_autofill_worker_cleanup_ignores_stale_worker_instance() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.pages.wind_data_page import WindDataPage

class DummyWorker:
    def __init__(self):
        self.deleted = False
    def deleteLater(self):
        self.deleted = True

app = QApplication([])
page = WindDataPage(AppSettings())
current = DummyWorker()
stale = DummyWorker()
page._autofill_fill_worker = current
page._on_autofill_worker_finished(stale)
assert page._autofill_fill_worker is current
assert stale.deleted is True
assert current.deleted is False
page._on_autofill_worker_finished(current)
assert page._autofill_fill_worker is None
assert current.deleted is True
page.close()
print("worker_cleanup_stable")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "worker_cleanup_stable" in completed.stdout


def test_wind_autofill_dialog_converts_24h_time_input_to_12h_plus_pm() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.gui.widgets.wind_autofill_dialog import WindAutofillDialog

app = QApplication([])
dialog = WindAutofillDialog(start_time_24h="10:00", end_time_24h="13:00")
dialog.end_time_edit.lineEdit().setText("22:30")
dialog.end_time_edit.interpretText()
app.processEvents()
print(
    "normalized",
    dialog.end_time_edit.time().toString("h:mm"),
    dialog.end_meridiem_combo.currentText(),
    dialog.selected_end_time_24h(),
)
dialog.end_time_edit.lineEdit().setText("24:00")
# Simulate user-typed overflow input that gets normalized on editingFinished.
dialog._remember_typed_time_text(dialog.end_time_edit, "24:00")
dialog.end_time_edit.editingFinished.emit()
app.processEvents()
print(
    "normalized_24",
    dialog.end_time_edit.time().toString("h:mm"),
    dialog.end_meridiem_combo.currentText(),
    dialog.selected_end_time_24h(),
)
dialog.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "normalized 10:30 PM 22:30" in completed.stdout
    assert "normalized_24 12:00 PM 12:00" in completed.stdout


def test_wind_autofill_dialog_report_date_is_limited_to_current_year_and_today() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from datetime import date
from PySide6.QtWidgets import QApplication
from purway_geotagger.gui.widgets.wind_autofill_dialog import WindAutofillDialog

app = QApplication([])
today = date.today()
jan_first = date(today.year, 1, 1)
last_year = date(today.year - 1, 12, 31)
next_year = date(today.year + 1, 1, 1)

dlg_min = WindAutofillDialog(start_time_24h="10:00", end_time_24h="13:00", report_date=last_year)
dlg_max = WindAutofillDialog(start_time_24h="10:00", end_time_24h="13:00", report_date=next_year)

min_ok = dlg_min.selected_report_date() == jan_first
max_ok = dlg_max.selected_report_date() == today
widget_min = dlg_max.report_date_edit.minimumDate()
widget_max = dlg_max.report_date_edit.maximumDate()
window_ok = (
    widget_min.year() == jan_first.year
    and widget_min.month() == jan_first.month
    and widget_min.day() == jan_first.day
    and widget_max.year() == today.year
    and widget_max.month() == today.month
    and widget_max.day() == today.day
)
print("date_bounds", min_ok, max_ok, window_ok)
dlg_min.close()
dlg_max.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "date_bounds True True True" in completed.stdout


def test_wind_autofill_calendar_weekend_color_and_size_match_theme() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication
from purway_geotagger.gui.widgets.wind_autofill_dialog import WindAutofillDialog

app = QApplication([])
dialog = WindAutofillDialog(start_time_24h="10:00", end_time_24h="13:00")
weekend_color = dialog._report_calendar.weekdayTextFormat(Qt.Saturday).foreground().color().name()
theme_color = dialog.palette().color(QPalette.WindowText).name()
calendar_size_ok = dialog._report_calendar.width() >= 320 and dialog._report_calendar.height() >= 240
menu_size_ok = dialog._report_date_menu.width() >= 340 and dialog._report_date_menu.height() >= 260
print("calendar_style", weekend_color == theme_color, calendar_size_ok, menu_size_ok)
dialog.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "calendar_style True True True" in completed.stdout
