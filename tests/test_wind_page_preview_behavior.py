from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_preview_updates_without_report_metadata() -> None:
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
page.client_edit.clear()
page.system_edit.clear()
page.timezone_edit.clear()
page.entry_grid.start_direction_edit.setText("SSW")
page.entry_grid.start_speed_spin.setValue(5)
page.entry_grid.start_gust_spin.setValue(20)
page.entry_grid.start_temp_spin.setValue(51)
page.entry_grid.end_direction_edit.setText("NNW")
page.entry_grid.end_speed_spin.setValue(16)
page.entry_grid.end_gust_spin.setValue(20)
page.entry_grid.end_temp_spin.setValue(55)
page._refresh_preview()
print(
    "preview|"
    + page.start_time_preview.text()
    + "|"
    + page.start_string_preview.text()
    + "|"
    + page.end_time_preview.text()
    + "|"
    + page.end_string_preview.text()
)
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
    assert "preview|10:00am|SSW 5 mph / Gusts 20 mph / 51°F|1:00pm|NNW 16 mph / Gusts 20 mph / 55°F" in completed.stdout


def test_main_wind_time_inputs_convert_24h_to_12h_with_meridiem_sync() -> None:
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
page.entry_grid.start_time_edit.lineEdit().setText("22:00")
page.entry_grid.start_time_edit.interpretText()
app.processEvents()
print(
    "time_normalized",
    page.entry_grid.start_time_edit.time().toString("h:mm"),
    page.entry_grid.start_meridiem_combo.currentText(),
    page.entry_grid.start_time_24h_text(),
)
page.entry_grid.start_time_edit.lineEdit().setText("24:00")
# Simulate user-typed overflow input that gets normalized on editingFinished.
page.entry_grid._remember_typed_time_text(page.entry_grid.start_time_edit, "24:00")
page.entry_grid.start_time_edit.editingFinished.emit()
app.processEvents()
print(
    "time_normalized_24",
    page.entry_grid.start_time_edit.time().toString("h:mm"),
    page.entry_grid.start_meridiem_combo.currentText(),
    page.entry_grid.start_time_24h_text(),
)
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
    assert "time_normalized 10:00 PM 22:00" in completed.stdout
    assert "time_normalized_24 12:00 PM 12:00" in completed.stdout


def test_autofill_dialog_inherits_report_date_and_applies_bounds() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.pages.wind_data_page import WindDataPage

app = QApplication([])
today = date.today()
jan_first = date(today.year, 1, 1)

page = WindDataPage(AppSettings())
page.date_edit.setDate(QDate(today.year - 1, 12, 31))
page._open_autofill_dialog()
dialog = page._autofill_dialog
assert dialog is not None
selected = dialog.selected_report_date()
print("dialog_date_clamped", selected == jan_first)
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
    assert "dialog_date_clamped True" in completed.stdout


def test_autofill_popup_times_are_pushed_back_to_main_wind_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
import purway_geotagger.gui.pages.wind_data_page as wind_page_module
from purway_geotagger.gui.pages.wind_data_page import WindDataPage
from purway_geotagger.core.wind_weather_autofill import LocationSuggestion

class _Signal:
    def connect(self, _fn):
        return None

class DummyWorker:
    def __init__(self, request):
        self.request = request
        self.result_ready = _Signal()
        self.failed = _Signal()
        self.finished = _Signal()
    def isRunning(self):
        return False
    def start(self):
        return None

wind_page_module.WindAutofillWorker = DummyWorker

app = QApplication([])
page = WindDataPage(AppSettings())
page._open_autofill_dialog()
dialog = page._autofill_dialog
assert dialog is not None
dialog.set_suggestions([
    LocationSuggestion(
        query_text="77008",
        display_name="Houston, Texas, US, 77008",
        latitude=29.8,
        longitude=-95.4,
        timezone_name="America/Chicago",
        city="Houston",
        state="Texas",
        postal_code="77008",
    )
])
dialog.start_time_edit.setTime(QTime.fromString("10:30", "h:mm"))
dialog.start_meridiem_combo.setCurrentText("PM")
dialog.end_time_edit.setTime(QTime.fromString("11:15", "h:mm"))
dialog.end_meridiem_combo.setCurrentText("PM")
page._start_autofill_fill()
print("times_synced", page.entry_grid.start_time_24h_text(), page.entry_grid.end_time_24h_text())
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
    assert "times_synced 22:30 23:15" in completed.stdout


def test_region_field_is_optional_and_wired_to_metadata() -> None:
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
page.client_edit.setText("ClientA")
page.system_edit.setText("System1")
page.region_edit.clear()
empty_region = page._build_metadata().region_id
page.region_edit.setText("North Sector")
filled_region = page._build_metadata().region_id
print("region_metadata", repr(empty_region), repr(filled_region))
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
    assert "region_metadata '' 'North Sector'" in completed.stdout
