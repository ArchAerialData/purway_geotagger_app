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


def test_combined_failure_popup_routes_to_run_report_dialog() -> None:
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
    Ok = 2
    last = None

    def __init__(self, *_args, **_kwargs):
        self._buttons = []
        self._clicked = None
        self._view_btn = None
        FakeMessageBox.last = self

    def setIcon(self, *_args, **_kwargs):
        return None

    def setWindowTitle(self, *_args, **_kwargs):
        return None

    def setText(self, *_args, **_kwargs):
        return None

    def addButton(self, label_or_button, role=None):
        token = object()
        if isinstance(label_or_button, str) and label_or_button == "View Log":
            self._view_btn = token
        self._buttons.append((label_or_button, role, token))
        return token

    def exec(self):
        self._clicked = self._view_btn

    def clickedButton(self):
        return self._clicked

class FakeRunReportDialog:
    opened = 0
    def __init__(self, *_args, **_kwargs):
        pass
    def exec(self):
        FakeRunReportDialog.opened += 1

combined_mod.QMessageBox = FakeMessageBox
combined_mod.RunReportDialog = FakeRunReportDialog

state = ModeState(mode=RunMode.COMBINED)
controller = JobController(AppSettings())
page = combined_mod.CombinedWizard(state, controller)
page._last_run_folder = Path("/tmp")
page._show_failure_popup("Synthetic failure")
assert FakeRunReportDialog.opened == 1
print("combined_failure_popup_routed")
page.close()
"""
    completed = _run_script(script)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "combined_failure_popup_routed" in completed.stdout


def test_combined_view_outputs_opens_run_report_dialog() -> None:
    script = r"""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.modes import RunMode
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
import purway_geotagger.gui.pages.combined_wizard as combined_mod

app = QApplication([])

class FakeRunReportDialog:
    opened = 0
    def __init__(self, *_args, **_kwargs):
        pass
    def exec(self):
        FakeRunReportDialog.opened += 1

combined_mod.RunReportDialog = FakeRunReportDialog

state = ModeState(mode=RunMode.COMBINED)
controller = JobController(AppSettings())
page = combined_mod.CombinedWizard(state, controller)
page._last_run_folder = Path("/tmp")
page._view_outputs()
assert FakeRunReportDialog.opened == 1
print("combined_view_outputs_routed")
page.close()
"""
    completed = _run_script(script)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "combined_view_outputs_routed" in completed.stdout
