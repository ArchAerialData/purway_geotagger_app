from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_settings_dialog_saves_extended_fields() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog

app = QApplication([])
settings = AppSettings()
settings.save = lambda: None
dlg = SettingsDialog(settings)

dlg.overwrite_chk.setChecked(True)
dlg.flatten_chk.setChecked(True)
dlg.cleanup_chk.setChecked(True)
dlg.sort_ppm_chk.setChecked(False)
dlg.dry_run_chk.setChecked(True)

dlg.write_xmp_chk.setChecked(False)
dlg.backup_chk.setChecked(False)
dlg.join_delta_spin.setValue(42)
dlg.ppm_edges_edit.setText("0, 500, 1000")

dlg.confirm_methane_chk.setChecked(False)
dlg.confirm_encroachment_chk.setChecked(False)
dlg.confirm_combined_chk.setChecked(False)
dlg.theme_combo.setCurrentIndex(dlg.theme_combo.findData("dark"))
dlg.exiftool_edit.setText("/usr/local/bin/exiftool")

dlg._on_accept()
print(
    "settings_saved",
    settings.overwrite_originals_default,
    settings.flatten_default,
    settings.cleanup_empty_dirs_default,
    settings.sort_by_ppm_default,
    settings.dry_run_default,
    settings.write_xmp_default,
    settings.create_backup_on_overwrite,
    settings.max_join_delta_seconds,
    settings.ppm_bin_edges,
    settings.confirm_methane,
    settings.confirm_encroachment,
    settings.confirm_combined,
    settings.ui_theme,
    settings.exiftool_path,
)
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
    assert (
        "settings_saved True True True False True False False 42 [0, 500, 1000] "
        "False False False dark /usr/local/bin/exiftool"
    ) in completed.stdout


def test_settings_dialog_reset_defaults_reloads_control_values() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    script = """
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog

app = QApplication([])
settings = AppSettings(
    overwrite_originals_default=True,
    flatten_default=True,
    cleanup_empty_dirs_default=True,
    sort_by_ppm_default=False,
    dry_run_default=True,
    write_xmp_default=False,
    create_backup_on_overwrite=False,
    max_join_delta_seconds=59,
    ppm_bin_edges=[3, 7],
    ui_theme="dark",
    confirm_methane=False,
    confirm_encroachment=False,
    confirm_combined=False,
)

dlg = SettingsDialog(settings)
dlg._reset_defaults()
defaults = AppSettings()
print(
    "defaults_reset",
    dlg.overwrite_chk.isChecked() == defaults.overwrite_originals_default,
    dlg.flatten_chk.isChecked() == defaults.flatten_default,
    dlg.cleanup_chk.isChecked() == defaults.cleanup_empty_dirs_default,
    dlg.sort_ppm_chk.isChecked() == defaults.sort_by_ppm_default,
    dlg.dry_run_chk.isChecked() == defaults.dry_run_default,
    dlg.write_xmp_chk.isChecked() == defaults.write_xmp_default,
    dlg.backup_chk.isChecked() == defaults.create_backup_on_overwrite,
    dlg.join_delta_spin.value() == defaults.max_join_delta_seconds,
    dlg.ppm_edges_edit.text() == ", ".join(str(x) for x in defaults.ppm_bin_edges),
    dlg.theme_combo.currentData() == defaults.ui_theme,
    dlg.confirm_methane_chk.isChecked() == defaults.confirm_methane,
    dlg.confirm_encroachment_chk.isChecked() == defaults.confirm_encroachment,
    dlg.confirm_combined_chk.isChecked() == defaults.confirm_combined,
)
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
    assert "defaults_reset True True True True True True True True True True True True True" in completed.stdout
