from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QListWidget,
    QFileDialog,
    QSpinBox,
    QCheckBox,
    QLineEdit,
    QMessageBox,
    QProgressBar,
)

from purway_geotagger.core.modes import common_parent, default_methane_log_base
from purway_geotagger.exif.exiftool_writer import is_exiftool_available
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
from purway_geotagger.gui.widgets.log_viewer import LogViewerDialog
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog
from purway_geotagger.gui.widgets.drop_zone import DropZone


class MethanePage(QWidget):
    back_requested = Signal()

    def __init__(self, state: ModeState, controller: JobController, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.controller = controller
        self._last_job_id: str | None = None
        self._last_job_stage: str | None = None
        self._last_run_folder: Path | None = None
        self.controller.jobs_changed.connect(self._on_jobs_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)
        header.addStretch(1)
        layout.addLayout(header)

        title = QLabel("Methane Reports Only")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title.setFont(title_font)
        layout.addWidget(title)

        input_group = QGroupBox("1) Add Inputs")
        input_layout = QVBoxLayout(input_group)
        input_layout.addWidget(QLabel("Drop Raw Data folders/files below:"))
        self.drop_zone = DropZone()
        self.drop_zone.paths_dropped.connect(self._on_paths_dropped)
        self.drop_zone.setMinimumHeight(90)
        input_layout.addWidget(self.drop_zone)

        input_btn_row = QHBoxLayout()
        add_folder_btn = QPushButton("Add Folder…")
        add_folder_btn.clicked.connect(self._add_folder)
        add_files_btn = QPushButton("Add Files…")
        add_files_btn.clicked.connect(self._add_files)
        clear_btn = QPushButton("Clear Inputs")
        clear_btn.clicked.connect(self._clear_inputs)
        input_btn_row.addWidget(add_folder_btn)
        input_btn_row.addWidget(add_files_btn)
        input_btn_row.addStretch(1)
        input_btn_row.addWidget(clear_btn)
        input_layout.addLayout(input_btn_row)

        self.inputs_list = QListWidget()
        self.inputs_list.setMinimumHeight(80)
        input_layout.addWidget(self.inputs_list)
        layout.addWidget(input_group)

        options_group = QGroupBox("2) Methane Options")
        options_layout = QVBoxLayout(options_group)
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("PPM threshold:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 1_000_000)
        self.threshold_spin.setValue(max(1, int(self.state.methane_threshold)))
        self.threshold_spin.valueChanged.connect(self._on_threshold_changed)
        self.threshold_spin.setToolTip("Rows with PPM below this value are filtered out.")
        threshold_row.addWidget(self.threshold_spin)
        threshold_row.addWidget(QLabel("PPM"))
        threshold_row.addStretch(1)
        options_layout.addLayout(threshold_row)

        self.kmz_chk = QCheckBox("Generate KMZ from cleaned CSV (optional)")
        self.kmz_chk.setChecked(bool(self.state.methane_generate_kmz))
        self.kmz_chk.toggled.connect(self._on_kmz_toggled)
        options_layout.addWidget(self.kmz_chk)

        self.cleaned_preview = QLabel()
        self.cleaned_preview.setWordWrap(True)
        self.kmz_preview = QLabel()
        self.kmz_preview.setWordWrap(True)
        options_layout.addWidget(self.cleaned_preview)
        options_layout.addWidget(self.kmz_preview)
        layout.addWidget(options_group)

        output_group = QGroupBox("3) Run Logs")
        output_layout = QVBoxLayout(output_group)
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Logs saved to:"))
        self.log_location_edit = QLineEdit()
        self.log_location_edit.setReadOnly(True)
        output_row.addWidget(self.log_location_edit, 1)
        self.change_log_btn = QPushButton("Select Log Folder…")
        self.change_log_btn.setFlat(True)
        self.change_log_btn.clicked.connect(self._change_log_location)
        output_row.addWidget(self.change_log_btn)
        self.view_log_btn = QPushButton("View log…")
        self.view_log_btn.setFlat(True)
        self.view_log_btn.setEnabled(False)
        self.view_log_btn.clicked.connect(self._view_log)
        output_row.addWidget(self.view_log_btn)
        output_layout.addLayout(output_row)
        self.log_note = QLabel("")
        self.log_note.setWordWrap(True)
        output_layout.addWidget(self.log_note)
        layout.addWidget(output_group)

        actions_row = QHBoxLayout()
        self.run_btn = QPushButton("Run Methane")
        self.run_btn.clicked.connect(self._run_methane)
        self.run_btn.setMinimumHeight(36)
        actions_row.addWidget(self.run_btn)
        self.view_log_btn2 = QPushButton("View log…")
        self.view_log_btn2.setEnabled(False)
        self.view_log_btn2.clicked.connect(self._view_log)
        actions_row.addWidget(self.view_log_btn2)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch(1)

        self.refresh_summary()

    def refresh_summary(self) -> None:
        self.inputs_list.clear()
        for p in self.state.inputs:
            self.inputs_list.addItem(str(p))
        self.threshold_spin.setValue(max(1, int(self.state.methane_threshold)))
        self.kmz_chk.setChecked(bool(self.state.methane_generate_kmz))
        self._update_log_location()
        self._update_naming_preview()

    def _on_paths_dropped(self, paths: list[str]) -> None:
        self._add_inputs([Path(p) for p in paths])

    def _add_folder(self) -> None:
        start_dir = str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select input folder", start_dir)
        if selected:
            self._add_inputs([Path(selected)])

    def _add_files(self) -> None:
        start_dir = str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(self, "Select input files", start_dir)
        if files:
            self._add_inputs([Path(p) for p in files])

    def _add_inputs(self, paths: list[Path]) -> None:
        updated = list(self.state.inputs)
        for p in paths:
            if p not in updated:
                updated.append(p)
        self.state.inputs = updated
        self.refresh_summary()

    def _clear_inputs(self) -> None:
        self.state.inputs = []
        self.refresh_summary()

    def _on_threshold_changed(self, value: int) -> None:
        self.state.methane_threshold = max(1, int(value))
        self._update_naming_preview()

    def _on_kmz_toggled(self, enabled: bool) -> None:
        self.state.methane_generate_kmz = enabled
        self._update_naming_preview()

    def _update_naming_preview(self) -> None:
        threshold = max(1, int(self.state.methane_threshold))
        self.cleaned_preview.setText(f"Cleaned CSV name: *_Cleaned_{threshold}-PPM.csv")
        self.kmz_preview.setVisible(self.kmz_chk.isChecked())
        if self.kmz_chk.isChecked():
            self.kmz_preview.setText(f"KMZ name: *_Cleaned_{threshold}-PPM.kmz")

    def _update_log_location(self) -> None:
        resolved = default_methane_log_base(self.state.inputs) if self.state.methane_log_base is None else self.state.methane_log_base
        text = str(resolved) if resolved else "Select inputs to determine log location."
        self.log_location_edit.setText(text)
        self.log_location_edit.setToolTip(text)
        self.log_note.setText(
            "Choose a different location if you want logs saved elsewhere."
            if self.state.inputs
            else ""
        )

    def _change_log_location(self) -> None:
        start_dir = str(default_methane_log_base(self.state.inputs) or Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select log location", start_dir)
        if selected:
            self.state.methane_log_base = Path(selected)
            self._update_log_location()

    def _run_methane(self) -> None:
        if not self.state.inputs:
            QMessageBox.information(self, "No inputs", "Add input folders or files before running.")
            return
        if not is_exiftool_available():
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("ExifTool required")
            msg.setText(
                "ExifTool is required to write EXIF metadata.\n\n"
                "Install ExifTool or set its path in Settings."
            )
            open_btn = msg.addButton("Open Settings", QMessageBox.AcceptRole)
            msg.addButton(QMessageBox.Cancel)
            msg.exec()
            if msg.clickedButton() == open_btn:
                dlg = SettingsDialog(self.controller.settings, parent=self)
                dlg.exec()
            return

        confirm = QMessageBox.question(
            self,
            "Confirm in-place EXIF write",
            "Methane mode writes EXIF metadata in-place.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.progress.setVisible(True)
        self.run_btn.setEnabled(False)
        self.status_label.setText("Running methane job...")
        job = self.controller.start_job_from_mode_state(self.state, self.progress)
        self._last_job_id = job.id if job else None
        self._last_job_stage = None
        self._last_run_folder = job.run_folder if job else None
        self._update_view_log_buttons()

    def _on_jobs_changed(self) -> None:
        if not self._last_job_id:
            return
        job = next((j for j in self.controller.jobs if j.id == self._last_job_id), None)
        if not job:
            return
        if self._last_run_folder is None:
            self._last_run_folder = job.run_folder
            self._update_view_log_buttons()
        if job.state.stage != self._last_job_stage:
            self._last_job_stage = job.state.stage
        if job.state.stage in ("DONE", "FAILED", "CANCELLED"):
            self.run_btn.setEnabled(True)
            if job.state.stage == "DONE":
                self.status_label.setText("Completed successfully.")
            elif job.state.stage == "CANCELLED":
                self.status_label.setText("Cancelled.")
            else:
                msg = job.state.message or "Job failed."
                self.status_label.setText(f"Failed: {msg}")
                self._show_failure_popup(msg)
            self._update_view_log_buttons()

    def _log_path(self) -> Path | None:
        if not self._last_run_folder:
            return None
        return self._last_run_folder / "run_log.txt"

    def _update_view_log_buttons(self) -> None:
        log_path = self._log_path()
        enabled = bool(log_path and log_path.exists())
        self.view_log_btn.setEnabled(enabled)
        self.view_log_btn2.setEnabled(enabled)

    def _view_log(self) -> None:
        log_path = self._log_path()
        if not log_path or not log_path.exists():
            QMessageBox.information(self, "Log not available", "Run log not available yet.")
            return
        dlg = LogViewerDialog(log_path, parent=self)
        dlg.exec()

    def _show_failure_popup(self, message: str) -> None:
        if not message:
            message = "Job failed."
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Methane run failed")
        msg.setText(message)
        view_btn = msg.addButton("View Log", QMessageBox.AcceptRole)
        msg.addButton(QMessageBox.Ok)
        msg.exec()
        if msg.clickedButton() == view_btn:
            self._view_log()
