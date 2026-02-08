from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.widgets.mac_stepper import MacStepper


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(760)
        self.resize(820, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        scroll.setWidget(content)

        title = QLabel("Settings")
        title.setProperty("cssClass", "h2")
        content_layout.addWidget(title)

        subtitle = QLabel(
            "Configure defaults used across runs. These values are saved per user profile."
        )
        subtitle.setProperty("cssClass", "subtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        content_layout.addWidget(self._build_general_group())
        content_layout.addWidget(self._build_processing_group())
        content_layout.addWidget(self._build_confirmation_group())
        content_layout.addWidget(self._build_tools_group())
        content_layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.reset_btn = buttons.addButton("Reset Defaults", QDialogButtonBox.ResetRole)
        self.reset_btn.clicked.connect(self._reset_defaults)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._populate_from_settings(self.settings)

    def _build_general_group(self) -> QGroupBox:
        group = QGroupBox("Run Defaults")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        self.overwrite_chk = QCheckBox("Overwrite originals by default")
        self.flatten_chk = QCheckBox("Flatten output folder structure by default")
        self.cleanup_chk = QCheckBox("Allow cleanup of empty dirs when flattening")
        self.sort_ppm_chk = QCheckBox("Sort methane output by PPM bins by default")
        self.dry_run_chk = QCheckBox("Dry run by default (no write operations)")
        self._style_settings_checkboxes(
            self.overwrite_chk,
            self.flatten_chk,
            self.cleanup_chk,
            self.sort_ppm_chk,
            self.dry_run_chk,
        )

        layout.addRow(self.overwrite_chk)
        layout.addRow(self.flatten_chk)
        layout.addRow(self.cleanup_chk)
        layout.addRow(self.sort_ppm_chk)
        layout.addRow(self.dry_run_chk)
        return group

    def _build_processing_group(self) -> QGroupBox:
        group = QGroupBox("Processing + Metadata")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        self.write_xmp_chk = QCheckBox("Write XMP tags by default")
        self.backup_chk = QCheckBox("Create .bak before overwrite")
        self._style_settings_checkboxes(self.write_xmp_chk, self.backup_chk)
        self.join_delta_spin = QSpinBox()
        self.join_delta_spin.setRange(1, 3600)
        self.join_delta_spin.setSuffix(" s")
        self.join_delta_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.join_delta_spin.setFixedWidth(92)
        self.join_delta_spin.setToolTip("Max timestamp delta used when correlating images and CSV rows.")
        self.join_delta_field = self._with_stepper(self.join_delta_spin)

        self.ppm_edges_edit = QLineEdit()
        self.ppm_edges_edit.setPlaceholderText("0, 1000")

        layout.addRow(self.write_xmp_chk)
        layout.addRow(self.backup_chk)
        layout.addRow("Max join delta", self.join_delta_field)
        layout.addRow("PPM bin edges", self.ppm_edges_edit)

        ppm_help = QLabel("Use comma-separated integers. Example: 0, 1000, 2500")
        ppm_help.setProperty("cssClass", "subtitle")
        ppm_help.setWordWrap(True)
        layout.addRow("", ppm_help)
        return group

    def _build_confirmation_group(self) -> QGroupBox:
        group = QGroupBox("Confirmations + Theme")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        self.confirm_methane_chk = QCheckBox("Show pre-run confirmation for Methane mode")
        self.confirm_encroachment_chk = QCheckBox("Show pre-run confirmation for Encroachment mode")
        self.confirm_combined_chk = QCheckBox("Show pre-run confirmation for Combined mode")
        self._style_settings_checkboxes(
            self.confirm_methane_chk,
            self.confirm_encroachment_chk,
            self.confirm_combined_chk,
        )

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")

        layout.addRow("Theme", self.theme_combo)
        layout.addRow(self.confirm_methane_chk)
        layout.addRow(self.confirm_encroachment_chk)
        layout.addRow(self.confirm_combined_chk)
        return group

    def _build_tools_group(self) -> QGroupBox:
        group = QGroupBox("Tool Paths")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        self.exiftool_edit = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_exiftool)

        exiftool_row = QHBoxLayout()
        exiftool_row.setContentsMargins(0, 0, 0, 0)
        exiftool_row.setSpacing(8)
        exiftool_row.addWidget(self.exiftool_edit, 1)
        exiftool_row.addWidget(browse_btn)

        exiftool_widget = QWidget()
        exiftool_widget.setLayout(exiftool_row)

        layout.addRow("ExifTool path (optional)", exiftool_widget)
        return group

    def _populate_from_settings(self, source: AppSettings) -> None:
        self.overwrite_chk.setChecked(source.overwrite_originals_default)
        self.flatten_chk.setChecked(source.flatten_default)
        self.cleanup_chk.setChecked(source.cleanup_empty_dirs_default)
        self.sort_ppm_chk.setChecked(source.sort_by_ppm_default)
        self.dry_run_chk.setChecked(source.dry_run_default)

        self.write_xmp_chk.setChecked(source.write_xmp_default)
        self.backup_chk.setChecked(source.create_backup_on_overwrite)
        self.join_delta_spin.setValue(int(source.max_join_delta_seconds))
        self.ppm_edges_edit.setText(", ".join(str(x) for x in source.ppm_bin_edges))

        self.confirm_methane_chk.setChecked(source.confirm_methane)
        self.confirm_encroachment_chk.setChecked(source.confirm_encroachment)
        self.confirm_combined_chk.setChecked(source.confirm_combined)

        desired_theme = (source.ui_theme or "light").strip().lower()
        index = self.theme_combo.findData(desired_theme)
        self.theme_combo.setCurrentIndex(index if index >= 0 else 0)

        self.exiftool_edit.setText(source.exiftool_path or "")

    def _reset_defaults(self) -> None:
        self._populate_from_settings(AppSettings())

    def _on_accept(self) -> None:
        try:
            edges = _parse_edges(self.ppm_edges_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid PPM bin edges", str(exc))
            return

        self.settings.overwrite_originals_default = self.overwrite_chk.isChecked()
        self.settings.flatten_default = self.flatten_chk.isChecked()
        self.settings.cleanup_empty_dirs_default = self.cleanup_chk.isChecked()
        self.settings.sort_by_ppm_default = self.sort_ppm_chk.isChecked()
        self.settings.dry_run_default = self.dry_run_chk.isChecked()

        self.settings.write_xmp_default = self.write_xmp_chk.isChecked()
        self.settings.create_backup_on_overwrite = self.backup_chk.isChecked()
        self.settings.max_join_delta_seconds = int(self.join_delta_spin.value())
        self.settings.ppm_bin_edges = edges

        self.settings.confirm_methane = self.confirm_methane_chk.isChecked()
        self.settings.confirm_encroachment = self.confirm_encroachment_chk.isChecked()
        self.settings.confirm_combined = self.confirm_combined_chk.isChecked()
        self.settings.ui_theme = str(self.theme_combo.currentData() or "light")

        self.settings.exiftool_path = self.exiftool_edit.text().strip()
        self.settings.save()
        self.accept()

    def _browse_exiftool(self) -> None:
        start_dir = self.exiftool_edit.text().strip() or ""
        path, _ = QFileDialog.getOpenFileName(self, "Select ExifTool", start_dir)
        if path:
            self.exiftool_edit.setText(path)

    def _style_settings_checkboxes(self, *widgets: QCheckBox) -> None:
        for widget in widgets:
            widget.setProperty("cssClass", "settings_checkbox")

    def _with_stepper(self, editor: QAbstractSpinBox) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(editor)

        stepper = MacStepper()
        stepper.step_up.connect(lambda: editor.stepBy(1))
        stepper.step_down.connect(lambda: editor.stepBy(-1))
        layout.addWidget(stepper)
        return container


def _parse_edges(value: str) -> list[int]:
    parts = [p for p in re.split(r"[,\s]+", value.strip()) if p]
    if not parts:
        raise ValueError("Provide at least one integer edge value.")
    try:
        edges = [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError("Bin edges must be integers.") from exc
    return sorted(set(edges))
