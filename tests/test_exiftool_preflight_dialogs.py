from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def _run_script(script: str) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_methane_mode_shows_exiftool_preflight_dialog_with_settings_path() -> None:
    script = r"""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.modes import RunMode
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
import purway_geotagger.gui.pages.methane_page as methane_mod

app = QApplication([])

class FakeMessageBox:
    Warning = 1
    AcceptRole = 0
    Cancel = 2
    last = None

    def __init__(self, *_args, **_kwargs):
        self._title = ""
        self._text = ""
        self._buttons = []
        self._clicked = None
        FakeMessageBox.last = self

    def setIcon(self, *_args, **_kwargs):
        return None

    def setWindowTitle(self, title):
        self._title = title

    def setText(self, text):
        self._text = text

    def addButton(self, label_or_button, role=None):
        if isinstance(label_or_button, str):
            label = label_or_button
        else:
            label = "<standard>"
        token = object()
        self._buttons.append((label, role, token))
        return token

    def exec(self):
        self._clicked = None

    def clickedButton(self):
        return self._clicked

class FakeSettingsDialog:
    opened = 0
    def __init__(self, *_args, **_kwargs):
        pass
    def exec(self):
        FakeSettingsDialog.opened += 1

methane_mod.QMessageBox = FakeMessageBox
methane_mod.SettingsDialog = FakeSettingsDialog
methane_mod.is_exiftool_available = lambda: False

state = ModeState(mode=RunMode.METHANE)
state.inputs = [Path("/tmp")]
controller = JobController(AppSettings())
page = methane_mod.MethanePage(state, controller)
page._run_methane()

msg = FakeMessageBox.last
assert msg is not None
labels = [label for (label, _role, _token) in msg._buttons]
assert msg._title == "ExifTool required"
assert "Install ExifTool or set its path in Settings." in msg._text
assert "Open Settings" in labels
print("methane_dialog_ok")
page.close()
"""
    completed = _run_script(script)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "methane_dialog_ok" in completed.stdout


def test_combined_mode_shows_exiftool_preflight_dialog_with_settings_path() -> None:
    script = r"""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.modes import RunMode
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
import purway_geotagger.gui.pages.combined_wizard as combined_mod

app = QApplication([])

class FakeMessageBox:
    Warning = 1
    AcceptRole = 0
    Cancel = 2
    last = None

    def __init__(self, *_args, **_kwargs):
        self._title = ""
        self._text = ""
        self._buttons = []
        self._clicked = None
        FakeMessageBox.last = self

    def setIcon(self, *_args, **_kwargs):
        return None

    def setWindowTitle(self, title):
        self._title = title

    def setText(self, text):
        self._text = text

    def addButton(self, label_or_button, role=None):
        if isinstance(label_or_button, str):
            label = label_or_button
        else:
            label = "<standard>"
        token = object()
        self._buttons.append((label, role, token))
        return token

    def exec(self):
        self._clicked = None

    def clickedButton(self):
        return self._clicked

class FakeSettingsDialog:
    opened = 0
    def __init__(self, *_args, **_kwargs):
        pass
    def exec(self):
        FakeSettingsDialog.opened += 1

combined_mod.QMessageBox = FakeMessageBox
combined_mod.SettingsDialog = FakeSettingsDialog
combined_mod.is_exiftool_available = lambda: False

state = ModeState(mode=RunMode.COMBINED)
state.inputs = [Path("/tmp")]
state.encroachment_output_base = Path("/tmp/out")
controller = JobController(AppSettings())
page = combined_mod.CombinedWizard(state, controller)
page._run_combined()

msg = FakeMessageBox.last
assert msg is not None
labels = [label for (label, _role, _token) in msg._buttons]
assert msg._title == "ExifTool required"
assert "Install ExifTool or set its path in Settings." in msg._text
assert "Open Settings" in labels
print("combined_dialog_ok")
page.close()
"""
    completed = _run_script(script)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "combined_dialog_ok" in completed.stdout
