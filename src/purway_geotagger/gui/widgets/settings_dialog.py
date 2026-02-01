from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QDialogButtonBox,
    QMessageBox,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QWidget,
)

from purway_geotagger.core.settings import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.ppm_edges_edit = QLineEdit(", ".join(str(x) for x in settings.ppm_bin_edges))
        self.join_delta_spin = QSpinBox()
        self.join_delta_spin.setRange(1, 3600)
        self.join_delta_spin.setValue(settings.max_join_delta_seconds)

        self.write_xmp_chk = QCheckBox("Write XMP tags by default")
        self.write_xmp_chk.setChecked(settings.write_xmp_default)

        self.backup_chk = QCheckBox("Create .bak when overwriting originals")
        self.backup_chk.setChecked(settings.create_backup_on_overwrite)

        self.cleanup_chk = QCheckBox("Allow cleanup of empty dirs when flattening")
        self.cleanup_chk.setChecked(settings.cleanup_empty_dirs_default)

        self.exiftool_edit = QLineEdit(settings.exiftool_path)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_exiftool)
        exiftool_row = QHBoxLayout()
        exiftool_row.addWidget(self.exiftool_edit, 1)
        exiftool_row.addWidget(browse_btn)
        exiftool_widget = QWidget()
        exiftool_widget.setLayout(exiftool_row)

        form.addRow("PPM bin edges (comma-separated)", self.ppm_edges_edit)
        form.addRow("Max join delta (seconds)", self.join_delta_spin)
        form.addRow("", self.write_xmp_chk)
        form.addRow("", self.backup_chk)
        form.addRow("", self.cleanup_chk)
        form.addRow("ExifTool path (optional)", exiftool_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        try:
            edges = _parse_edges(self.ppm_edges_edit.text())
        except ValueError as e:
            QMessageBox.warning(self, "Invalid bin edges", str(e))
            return

        self.settings.ppm_bin_edges = edges
        self.settings.max_join_delta_seconds = int(self.join_delta_spin.value())
        self.settings.write_xmp_default = self.write_xmp_chk.isChecked()
        self.settings.create_backup_on_overwrite = self.backup_chk.isChecked()
        self.settings.cleanup_empty_dirs_default = self.cleanup_chk.isChecked()
        self.settings.exiftool_path = self.exiftool_edit.text().strip()
        self.settings.save()
        self.accept()

    def _browse_exiftool(self) -> None:
        start_dir = self.exiftool_edit.text().strip() or ""
        path, _ = QFileDialog.getOpenFileName(self, "Select ExifTool", start_dir)
        if path:
            self.exiftool_edit.setText(path)


def _parse_edges(value: str) -> list[int]:
    parts = [p for p in re.split(r"[,\s]+", value.strip()) if p]
    if not parts:
        raise ValueError("Provide at least one integer edge value.")
    try:
        edges = [int(p) for p in parts]
    except ValueError as e:
        raise ValueError("Bin edges must be integers.") from e
    edges = sorted(set(edges))
    return edges
