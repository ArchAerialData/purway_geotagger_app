from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QListWidget,
    QFileDialog,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QMessageBox,
    QProgressBar,
)

from purway_geotagger.core.modes import default_encroachment_base
from purway_geotagger.exif.exiftool_writer import is_exiftool_available
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
from purway_geotagger.gui.widgets.drop_zone import DropZone
from purway_geotagger.gui.widgets.required_marker import RequiredMarker
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog
from purway_geotagger.gui.widgets.template_editor import TemplateEditorDialog
from purway_geotagger.templates.models import RenameTemplate
from purway_geotagger.templates.template_manager import render_filename
from purway_geotagger.gui.widgets.log_viewer import LogViewerDialog


class EncroachmentPage(QWidget):
    back_requested = Signal()

    def __init__(self, state: ModeState, controller: JobController, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.controller = controller
        self._output_auto = True
        self._last_job_id: str | None = None
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

        title = QLabel("Encroachment Reports Only")
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

        output_group = QGroupBox("2) Output Folder (required)")
        output_layout = QVBoxLayout(output_group)
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Encroachment output:"))
        self.output_edit = QLineEdit()
        self.output_edit.textChanged.connect(self._on_output_changed)
        output_row.addWidget(self.output_edit, 1)
        output_btn = QPushButton("Select Output Folder…")
        output_btn.clicked.connect(self._select_output_folder)
        output_row.addWidget(output_btn)
        output_layout.addLayout(output_row)
        output_help = QLabel("Defaults to Encroachment_Output under the common input root.")
        output_help.setWordWrap(True)
        output_layout.addWidget(output_help)
        layout.addWidget(output_group)

        rename_group = QGroupBox("3) Renaming (optional)")
        rename_layout = QVBoxLayout(rename_group)
        self.rename_chk = QCheckBox("Enable renaming")
        self.rename_chk.setChecked(bool(self.state.encroachment_rename_enabled))
        self.rename_chk.toggled.connect(self._on_rename_toggled)
        rename_layout.addWidget(self.rename_chk)

        template_row = QHBoxLayout()
        template_row.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        template_row.addWidget(self.template_combo, 1)
        edit_btn = QPushButton("Edit Templates…")
        edit_btn.clicked.connect(self._open_template_editor)
        template_row.addWidget(edit_btn)
        rename_layout.addLayout(template_row)

        self.template_preview = QLabel("")
        self.template_preview.setWordWrap(True)
        rename_layout.addWidget(self.template_preview)

        manual_row = QHBoxLayout()
        self.client_label = QLabel("Client Abbreviation:")
        manual_row.addWidget(self.client_label)
        self.client_edit = QLineEdit(self.state.encroachment_client_abbr)
        self.client_edit.textChanged.connect(self._on_manual_changed)
        manual_row.addWidget(self.client_edit)
        self.client_required = RequiredMarker()
        manual_row.addWidget(self.client_required)
        self.start_index_label = QLabel("Start Index:")
        manual_row.addWidget(self.start_index_label)
        self.start_index_spin = QSpinBox()
        self.start_index_spin.setRange(1, 10_000_000)
        self.start_index_spin.setValue(max(1, int(self.state.encroachment_start_index)))
        self.start_index_spin.valueChanged.connect(self._on_manual_changed)
        manual_row.addWidget(self.start_index_spin)
        rename_layout.addLayout(manual_row)

        self.rename_note = QLabel("")
        self.rename_note.setWordWrap(True)
        self.rename_note.setStyleSheet("color: #777777;")
        rename_layout.addWidget(self.rename_note)
        layout.addWidget(rename_group)

        actions_row = QHBoxLayout()
        self.run_btn = QPushButton("Run Encroachment")
        self.run_btn.clicked.connect(self._run_encroachment)
        self.run_btn.setMinimumHeight(36)
        actions_row.addWidget(self.run_btn)
        self.view_log_btn = QPushButton("View log…")
        self.view_log_btn.setEnabled(False)
        self.view_log_btn.clicked.connect(self._view_log)
        actions_row.addWidget(self.view_log_btn)
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

        self._refresh_templates()
        self.refresh_summary()

    def refresh_summary(self) -> None:
        self.inputs_list.clear()
        for p in self.state.inputs:
            self.inputs_list.addItem(str(p))
        self._update_output_default()
        self.rename_chk.setChecked(bool(self.state.encroachment_rename_enabled))
        self.client_edit.setText(self.state.encroachment_client_abbr)
        self.start_index_spin.setValue(max(1, int(self.state.encroachment_start_index)))
        self._sync_template_selection()
        self._update_rename_state()

    def _on_paths_dropped(self, paths: list[str]) -> None:
        self._add_inputs([Path(p) for p in paths])

    def _add_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select input folder", str(Path.home()))
        if selected:
            self._add_inputs([Path(selected)])

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select input files", str(Path.home()))
        if files:
            self._add_inputs([Path(p) for p in files])

    def _add_inputs(self, paths: list[Path]) -> None:
        updated = list(self.state.inputs)
        for p in paths:
            if p not in updated:
                updated.append(p)
        self.state.inputs = updated
        self._output_auto = self.state.encroachment_output_base is None
        self.refresh_summary()

    def _clear_inputs(self) -> None:
        self.state.inputs = []
        self.refresh_summary()

    def _update_output_default(self) -> None:
        if not self.state.inputs:
            if self._output_auto:
                self._set_output_text("")
                self.state.encroachment_output_base = None
            return
        if self._output_auto:
            default = default_encroachment_base(self.state.inputs)
            if default:
                self._set_output_text(str(default))
                self.state.encroachment_output_base = default

    def _on_output_changed(self, text: str) -> None:
        value = text.strip()
        if value:
            self.state.encroachment_output_base = Path(value)
            self._output_auto = False
        else:
            self.state.encroachment_output_base = None
        self._set_output_text(value)

    def _select_output_folder(self) -> None:
        start_dir = str(self.state.encroachment_output_base or default_encroachment_base(self.state.inputs) or Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select output folder", start_dir)
        if selected:
            self._set_output_text(selected)
            self.state.encroachment_output_base = Path(selected)
            self._output_auto = False

    def _on_rename_toggled(self, enabled: bool) -> None:
        self.state.encroachment_rename_enabled = enabled
        self._update_rename_state()

    def _on_template_changed(self, _idx: int) -> None:
        template_id = self.template_combo.currentData()
        self.state.encroachment_template_id = template_id
        if template_id:
            tmpl = self.controller.template_manager.templates.get(template_id)
            if tmpl:
                self.start_index_spin.setValue(max(1, int(tmpl.start_index)))
        self._update_rename_state()

    def _on_manual_changed(self) -> None:
        self.state.encroachment_client_abbr = self.client_edit.text().strip()
        self.state.encroachment_start_index = max(1, int(self.start_index_spin.value()))
        self._update_rename_state()

    def _update_rename_state(self) -> None:
        enabled = self.rename_chk.isChecked()
        self.template_combo.setEnabled(enabled)
        template_selected = bool(self.template_combo.currentData())
        if not enabled:
            self.rename_note.setText("Renaming is disabled.")
            self.template_preview.setText("")
            self._set_manual_visible(False)
            return
        if template_selected:
            self._set_manual_visible(False)
            self.rename_note.setText("Template selected; manual fields are ignored.")
            self._update_template_preview()
        else:
            self._set_manual_visible(True)
            self.rename_note.setText("No template selected. Provide Client Abbreviation and Start Index.")
            self._update_template_preview(manual=True)

    def _refresh_templates(self) -> None:
        self.template_combo.clear()
        self.template_combo.addItem("— No template —", userData=None)
        for t in self.controller.template_manager.list_templates():
            self.template_combo.addItem(t.name, userData=t.id)
        self._update_template_preview()

    def _sync_template_selection(self) -> None:
        current = self.state.encroachment_template_id
        if current is None:
            self.template_combo.setCurrentIndex(0)
            return
        for i in range(self.template_combo.count()):
            if self.template_combo.itemData(i) == current:
                self.template_combo.setCurrentIndex(i)
                return
        self._update_template_preview()

    def _open_template_editor(self) -> None:
        dlg = TemplateEditorDialog(self.controller.template_manager, parent=self)
        dlg.templates_changed.connect(self._on_templates_changed)
        if dlg.exec():
            self._refresh_templates()
            self._sync_template_selection()

    def _on_templates_changed(self) -> None:
        current = self.state.encroachment_template_id
        self._refresh_templates()
        self.state.encroachment_template_id = current
        self._sync_template_selection()
        self._update_template_preview()

    def _update_template_preview(self, manual: bool = False) -> None:
        if not self.rename_chk.isChecked():
            self.template_preview.setText("")
            return
        if manual:
            abbr = self.client_edit.text().strip() or "CLIENT"
            index = max(1, int(self.start_index_spin.value()))
            tmpl = RenameTemplate(
                id="manual_preview",
                name="Manual",
                client=abbr,
                pattern="{client}_{index:04d}",
                description="Manual preview",
                start_index=index,
            )
            try:
                example = render_filename(
                    template=tmpl,
                    index=index,
                    ppm=12.3,
                    lat=1.2345,
                    lon=2.3456,
                    orig="IMG_0001",
                )
                self.template_preview.setText(f"Preview: {example}.jpg")
            except Exception as exc:
                self.template_preview.setText(f"Preview error: {exc}")
            return
        template_id = self.template_combo.currentData()
        if not template_id:
            self.template_preview.setText("Preview: (select a template or enter manual fields)")
            return
        tmpl = self.controller.template_manager.templates.get(template_id)
        if not tmpl:
            self.template_preview.setText("")
            return
        index = max(1, int(self.start_index_spin.value()))
        try:
            example = render_filename(
                template=tmpl,
                index=index,
                ppm=12.3,
                lat=1.2345,
                lon=2.3456,
                orig="IMG_0001",
            )
            self.template_preview.setText(f"Preview: {example}.jpg")
        except Exception as exc:
            self.template_preview.setText(f"Preview error: {exc}")

    def _set_output_text(self, text: str) -> None:
        self.output_edit.blockSignals(True)
        self.output_edit.setText(text)
        self.output_edit.setToolTip(text)
        if text:
            self.output_edit.setCursorPosition(len(text))
        self.output_edit.blockSignals(False)

    def _set_manual_visible(self, visible: bool) -> None:
        self.client_label.setVisible(visible)
        self.client_edit.setVisible(visible)
        self.start_index_label.setVisible(visible)
        self.start_index_spin.setVisible(visible)
        if not visible:
            self.client_required.setVisible(False)

    def _run_encroachment(self) -> None:
        if not self.state.inputs:
            QMessageBox.information(self, "No inputs", "Add input folders or files before running.")
            return
        if not self.state.encroachment_output_base:
            QMessageBox.warning(self, "Output required", "Select an output folder.")
            return
        if self.rename_chk.isChecked():
            if not self.template_combo.currentData():
                if not self.client_edit.text().strip():
                    QMessageBox.warning(self, "Client Abbreviation required", "Enter a Client Abbreviation or select a template.")
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

        self.progress.setVisible(True)
        self.run_btn.setEnabled(False)
        self.status_label.setText("Running encroachment job...")
        job = self.controller.start_job_from_mode_state(self.state, self.progress)
        self._last_job_id = job.id if job else None
        self._last_run_folder = job.run_folder if job else None
        self._update_view_log_button()

    def _log_path(self) -> Path | None:
        if not self._last_run_folder:
            return None
        return self._last_run_folder / "run_log.txt"

    def _update_view_log_button(self) -> None:
        path = self._log_path()
        self.view_log_btn.setEnabled(bool(path and path.exists()))

    def _view_log(self) -> None:
        path = self._log_path()
        if not path or not path.exists():
            QMessageBox.information(self, "Log not available", "Run log not available yet.")
            return
        dlg = LogViewerDialog(path, parent=self)
        dlg.exec()

    def _on_jobs_changed(self) -> None:
        if not self._last_job_id:
            return
        job = next((j for j in self.controller.jobs if j.id == self._last_job_id), None)
        if not job:
            return
        if self._last_run_folder is None:
            self._last_run_folder = job.run_folder
            self._update_view_log_button()
        if job.state.stage in ("DONE", "FAILED", "CANCELLED"):
            self.run_btn.setEnabled(True)
            if job.state.stage == "DONE":
                self.status_label.setText("Completed successfully.")
            elif job.state.stage == "CANCELLED":
                self.status_label.setText("Cancelled.")
            else:
                msg = job.state.message or "Job failed."
                self.status_label.setText(f"Failed: {msg}")
            self._update_view_log_button()
