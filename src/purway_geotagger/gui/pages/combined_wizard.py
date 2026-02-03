from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QListWidget,
    QFileDialog,
    QSpinBox,
    QCheckBox,
    QLineEdit,
    QComboBox,
    QScrollArea,
    QStackedWidget,
    QProgressBar,
    QFrame,
    QSizePolicy,
)


from purway_geotagger.core.modes import common_parent, default_methane_log_base, default_encroachment_base
from purway_geotagger.exif.exiftool_writer import is_exiftool_available
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
from purway_geotagger.gui.widgets.drop_zone import DropZone
from purway_geotagger.gui.widgets.required_marker import RequiredMarker
from purway_geotagger.gui.widgets.run_report_view import RunReportDialog
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog
from purway_geotagger.gui.widgets.template_editor import TemplateEditorDialog
from purway_geotagger.templates.models import RenameTemplate
from purway_geotagger.templates.template_manager import render_filename


class CombinedWizard(QWidget):
    back_requested = Signal()

    def __init__(self, state: ModeState, controller: JobController, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.controller = controller
        self._output_auto = True
        self._last_job_id: str | None = None
        self._last_run_folder: Path | None = None
        self._last_job_stage: str | None = None
        self.controller.jobs_changed.connect(self._on_jobs_changed)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QHBoxLayout()
        back_btn = QPushButton("Back to Home")
        back_btn.setProperty("cssClass", "ghost")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)
        self.step_label = QLabel("")
        self.step_label.setProperty("cssClass", "subtitle")
        header.addStretch(1)
        header.addWidget(self.step_label)
        layout.addLayout(header)

        title = QLabel("Methane + Encroachments")
        title.setProperty("cssClass", "h1")
        layout.addWidget(title)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.inputs_step = self._build_inputs_step()
        self.methane_step = self._build_methane_step()
        self.encroachment_step = self._build_encroachment_step()
        self.confirm_step = self._build_confirm_step()

        self.stack.addWidget(self.inputs_step)
        self.stack.addWidget(self.methane_step)
        self.stack.addWidget(self.encroachment_step)
        self.stack.addWidget(self.confirm_step)

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("Back")
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self._go_prev)
        self.next_btn = QPushButton("Next")
        self.next_btn.setProperty("cssClass", "primary")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self._go_next)
        nav.addWidget(self.prev_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        self.status_label = QLabel("")
        self.status_label.setProperty("cssClass", "subtitle")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self._refresh_templates()
        self.refresh_summary()
        self._update_step_ui()


    def refresh_summary(self) -> None:
        self.inputs_list.clear()
        for p in self.state.inputs:
            self.inputs_list.addItem(str(p))
        self.threshold_spin.setValue(max(1, int(self.state.methane_threshold)))
        self.kmz_chk.setChecked(bool(self.state.methane_generate_kmz))
        self._update_log_location()
        self._update_naming_preview()
        self._update_output_default()
        self._sync_template_selection()
        self._update_rename_state()
        if self.stack.currentWidget() == self.confirm_step:
            self._update_confirm_summary()

    def _build_inputs_step(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        step_header = QLabel("Step 1 - Select Input Files/Folders")
        step_header.setProperty("cssClass", "h2")
        layout.addWidget(step_header)

        input_card = QFrame()
        input_card.setProperty("cssClass", "card")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(16)

        input_layout.addWidget(QLabel("Drop Raw Data folders/files below:"))
        self.drop_zone = DropZone()
        self.drop_zone.paths_dropped.connect(self._on_paths_dropped)
        self.drop_zone.setMinimumHeight(120)
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
        self.inputs_required = RequiredMarker()
        input_layout.addWidget(self.inputs_required)

        layout.addWidget(input_card)
        # Removed addStretch to allow natural flow
        self.inputs_scroll = _wrap_scroll(content)
        return self.inputs_scroll



    def _build_methane_step(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        step_header = QLabel("Step 2 - Configure Methane Options")
        step_header.setProperty("cssClass", "h2")
        layout.addWidget(step_header)

        methane_card = QFrame()
        methane_card.setProperty("cssClass", "card")
        methane_layout = QVBoxLayout(methane_card)
        methane_layout.setContentsMargins(20, 20, 20, 20)
        methane_layout.setSpacing(16)
        
        methane_layout.addWidget(QLabel("2) Methane Options"))

        threshold_row = QHBoxLayout()
        threshold_lbl = QLabel("PPM threshold:")
        threshold_lbl.setProperty("cssClass", "subtitle")
        threshold_row.addWidget(threshold_lbl)
        
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 1_000_000)
        self.threshold_spin.setValue(max(1, int(self.state.methane_threshold)))
        self.threshold_spin.valueChanged.connect(self._on_threshold_changed)
        self.threshold_spin.setFixedWidth(100)
        threshold_row.addWidget(self.threshold_spin)
        
        unit_lbl = QLabel("PPM")
        unit_lbl.setProperty("cssClass", "subtitle")
        threshold_row.addWidget(unit_lbl)
        threshold_row.addStretch(1)
        methane_layout.addLayout(threshold_row)

        self.kmz_chk = QCheckBox("Generate KMZ from cleaned CSV (optional)")
        self.kmz_chk.setChecked(bool(self.state.methane_generate_kmz))
        self.kmz_chk.toggled.connect(self._on_kmz_toggled)
        methane_layout.addWidget(self.kmz_chk)

        self.cleaned_preview = QLabel()
        self.cleaned_preview.setProperty("cssClass", "subtitle")
        self.cleaned_preview.setWordWrap(True)
        self.kmz_preview = QLabel()
        self.kmz_preview.setProperty("cssClass", "subtitle")
        self.kmz_preview.setWordWrap(True)
        methane_layout.addWidget(self.cleaned_preview)
        methane_layout.addWidget(self.kmz_preview)
        
        layout.addWidget(methane_card)

        output_card = QFrame()
        output_card.setProperty("cssClass", "card")
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(20, 20, 20, 20)
        output_layout.setSpacing(16)
        
        output_layout.addWidget(QLabel("3) Methane Logs"))

        output_row = QHBoxLayout()
        log_lbl = QLabel("Logs saved to:")
        log_lbl.setProperty("cssClass", "subtitle")
        output_row.addWidget(log_lbl)
        
        self.log_location_edit = QLineEdit()
        self.log_location_edit.setReadOnly(True)
        output_row.addWidget(self.log_location_edit, 1)
        self.change_log_btn = QPushButton("Select Log Folder…")
        self.change_log_btn.clicked.connect(self._change_log_location)
        output_row.addWidget(self.change_log_btn)
        output_layout.addLayout(output_row)
        
        self.log_note = QLabel("")
        self.log_note.setProperty("cssClass", "subtitle")
        self.log_note.setWordWrap(True)
        output_layout.addWidget(self.log_note)
        
        layout.addWidget(output_card)

        # Removed addStretch
        self.methane_scroll = _wrap_scroll(content)
        return self.methane_scroll



    def _build_encroachment_step(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        step_header = QLabel("Step 3 - Configure Encroachment Options")
        step_header.setProperty("cssClass", "h2")
        layout.addWidget(step_header)

        output_card = QFrame()
        output_card.setProperty("cssClass", "card")
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(20, 20, 20, 20)
        output_layout.setSpacing(16)

        output_layout.addWidget(QLabel("4) Encroachment Output Folder (required)"))

        output_row = QHBoxLayout()
        out_lbl = QLabel("Encroachment output:")
        out_lbl.setProperty("cssClass", "subtitle")
        output_row.addWidget(out_lbl)
        
        self.output_edit = QLineEdit()
        self.output_edit.textChanged.connect(self._on_output_changed)
        output_row.addWidget(self.output_edit, 1)
        output_btn = QPushButton("Select Output Folder…")
        output_btn.clicked.connect(self._select_output_folder)
        output_row.addWidget(output_btn)
        output_layout.addLayout(output_row)
        
        self.output_required = RequiredMarker()
        output_layout.addWidget(self.output_required)
        
        output_help = QLabel("Defaults to Encroachment_Output under the common input root.")
        output_help.setProperty("cssClass", "subtitle")
        output_help.setWordWrap(True)
        output_layout.addWidget(output_help)
        
        layout.addWidget(output_card)

        rename_card = QFrame()
        rename_card.setProperty("cssClass", "card")
        rename_layout = QVBoxLayout(rename_card)
        rename_layout.setContentsMargins(20, 20, 20, 20)
        rename_layout.setSpacing(16)

        rename_layout.addWidget(QLabel("5) Renaming (optional)"))

        self.rename_chk = QCheckBox("Enable renaming")
        self.rename_chk.setChecked(bool(self.state.encroachment_rename_enabled))
        self.rename_chk.toggled.connect(self._on_rename_toggled)
        rename_layout.addWidget(self.rename_chk)

        template_row = QHBoxLayout()
        tmpl_lbl = QLabel("Template:")
        tmpl_lbl.setProperty("cssClass", "subtitle")
        template_row.addWidget(tmpl_lbl)
        
        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        template_row.addWidget(self.template_combo, 1)
        edit_btn = QPushButton("Edit Templates…")
        edit_btn.clicked.connect(self._open_template_editor)
        template_row.addWidget(edit_btn)
        rename_layout.addLayout(template_row)

        self.template_preview = QLabel("")
        self.template_preview.setProperty("cssClass", "subtitle")
        self.template_preview.setWordWrap(True)
        rename_layout.addWidget(self.template_preview)

        manual_row = QHBoxLayout()
        self.client_label = QLabel("Client Abbreviation:")
        self.client_label.setProperty("cssClass", "subtitle")
        manual_row.addWidget(self.client_label)
        
        self.client_edit = QLineEdit(self.state.encroachment_client_abbr)
        self.client_edit.textChanged.connect(self._on_manual_changed)
        manual_row.addWidget(self.client_edit)
        self.client_required = RequiredMarker()
        manual_row.addWidget(self.client_required)
        
        self.start_index_label = QLabel("Start Index:")
        self.start_index_label.setProperty("cssClass", "subtitle")
        manual_row.addWidget(self.start_index_label)
        
        self.start_index_spin = QSpinBox()
        self.start_index_spin.setRange(1, 10_000_000)
        self.start_index_spin.setValue(max(1, int(self.state.encroachment_start_index)))
        self.start_index_spin.valueChanged.connect(self._on_manual_changed)
        manual_row.addWidget(self.start_index_spin)
        rename_layout.addLayout(manual_row)

        self.rename_note = QLabel("")
        self.rename_note.setProperty("cssClass", "subtitle")
        self.rename_note.setWordWrap(True)
        rename_layout.addWidget(self.rename_note)
        
        layout.addWidget(rename_card)

        # Removed addStretch
        self.encroachment_scroll = _wrap_scroll(content)
        return self.encroachment_scroll



    def _build_confirm_step(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        step_header = QLabel("Step 4 - Confirm Settings & Run")
        step_header.setProperty("cssClass", "h2")
        layout.addWidget(step_header)

        summary_card = QFrame()
        summary_card.setProperty("cssClass", "card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(20, 20, 20, 20)
        summary_layout.setSpacing(16)
        
        summary_layout.addWidget(QLabel("Confirm settings"))

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.RichText)
        self.summary_label.setProperty("cssClass", "subtitle")
        summary_layout.addWidget(self.summary_label)
        
        layout.addWidget(summary_card)

        note = QLabel("Review the settings above, then click Run Combined to start.")
        note.setProperty("cssClass", "subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addWidget(note)

        # Removed addStretch
        self.confirm_scroll = _wrap_scroll(content)
        return self.confirm_scroll



    def _update_step_ui(self) -> None:
        idx = self.stack.currentIndex()
        self.step_label.setText(f"Step {idx + 1} of 4")
        self.prev_btn.setEnabled(idx > 0)
        if idx == 3:
            self.next_btn.setText("Run Combined")
            self.next_btn.setEnabled(True)
            self._update_confirm_summary()
        else:
            self.next_btn.setText("Next")
            self.next_btn.setEnabled(True)

    def _go_prev(self) -> None:
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_step_ui()

    def _go_next(self) -> None:
        if not self._validate_current_step():
            return
        idx = self.stack.currentIndex()
        if idx < 3:
            self.stack.setCurrentIndex(idx + 1)
            self._update_step_ui()
            return
        if idx == 3:
            self._run_combined()

    def _validate_current_step(self) -> bool:
        idx = self.stack.currentIndex()
        if idx == 0:
            missing = len(self.state.inputs) == 0
            self.inputs_required.show_required(missing)
            if missing:
                _scroll_to(self.inputs_scroll, self.inputs_required)
                return False
        elif idx == 2:
            missing_output = not self.state.encroachment_output_base
            self.output_required.show_required(missing_output)
            missing_client = False
            if self.rename_chk.isChecked() and not self.template_combo.currentData():
                missing_client = not self.client_edit.text().strip()
                self.client_required.show_required(missing_client)
            else:
                self.client_required.show_required(False)
            if missing_output:
                _scroll_to(self.encroachment_scroll, self.output_required)
                return False
            if missing_client:
                _scroll_to(self.encroachment_scroll, self.client_required)
                return False
        return True

    def _update_confirm_summary(self) -> None:
        inputs = self.state.inputs
        input_list = "<br/>".join(f"• {p}" for p in inputs) if inputs else "• (none)"
        threshold = max(1, int(self.state.methane_threshold))
        log_base = default_methane_log_base(inputs) if self.state.methane_log_base is None else self.state.methane_log_base
        log_text = str(log_base) if log_base else "(not set)"
        kmz = "Enabled" if self.state.methane_generate_kmz else "Disabled"
        cleaned_name = f"*_Cleaned_{threshold}-PPM.csv"
        kmz_name = f"*_Cleaned_{threshold}-PPM.kmz"

        output = self.state.encroachment_output_base
        output_text = str(output) if output else "(not set)"
        renaming = "Enabled" if self.state.encroachment_rename_enabled else "Disabled"
        template_id = self.state.encroachment_template_id
        template_name = ""
        if template_id:
            tmpl = self.controller.template_manager.templates.get(template_id)
            template_name = tmpl.name if tmpl else template_id
        manual = self.state.encroachment_client_abbr or "(none)"
        start_index = max(1, int(self.state.encroachment_start_index))

        summary = (
            "<b>Inputs</b><br/>"
            f"{input_list}<br/><br/>"
            "<b>Methane</b><br/>"
            f"• PPM threshold: {threshold}<br/>"
            f"• KMZ: {kmz}<br/>"
            f"• Cleaned CSV name: {cleaned_name}<br/>"
            f"• KMZ name: {kmz_name}<br/>"
            f"• Methane logs: {log_text}<br/><br/>"
            "<b>Encroachment</b><br/>"
            f"• Output folder: {output_text}<br/>"
            f"• Renaming: {renaming}<br/>"
        )
        if self.state.encroachment_rename_enabled:
            if template_name:
                summary += f"• Template: {template_name}<br/>"
            else:
                summary += f"• Client Abbreviation: {manual}<br/>"
            summary += f"• Start Index: {start_index}<br/>"
        self.summary_label.setText(summary)

    def _validate_for_run(self) -> bool:
        missing_inputs = len(self.state.inputs) == 0
        if missing_inputs:
            self.inputs_required.show_required(True)
            self.stack.setCurrentIndex(0)
            self._update_step_ui()
            _scroll_to(self.inputs_scroll, self.inputs_required)
            return False

        missing_output = not self.state.encroachment_output_base
        missing_client = False
        if self.rename_chk.isChecked() and not self.template_combo.currentData():
            missing_client = not self.client_edit.text().strip()
            self.client_required.show_required(missing_client)
        else:
            self.client_required.show_required(False)

        if missing_output or missing_client:
            self.output_required.show_required(missing_output)
            self.stack.setCurrentIndex(2)
            self._update_step_ui()
            if missing_output:
                _scroll_to(self.encroachment_scroll, self.output_required)
            else:
                _scroll_to(self.encroachment_scroll, self.client_required)
            return False

        return True

    def _run_combined(self) -> None:
        if not self._validate_for_run():
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
            "Confirm combined run",
            "Combined mode writes EXIF metadata in-place for methane inputs and copies encroachment photos.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.progress.setVisible(True)
        self.next_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.status_label.setText("Running combined job...")
        job = self.controller.start_job_from_mode_state(self.state, self.progress)
        self._last_job_id = job.id if job else None
        self._last_run_folder = job.run_folder if job else None

    def _on_jobs_changed(self) -> None:
        if not self._last_job_id:
            return
        job = next((j for j in self.controller.jobs if j.id == self._last_job_id), None)
        if not job:
            return
        if self._last_run_folder is None:
            self._last_run_folder = job.run_folder
        if job.state.stage != self._last_job_stage:
            self._last_job_stage = job.state.stage
        if job.state.stage in ("DONE", "FAILED", "CANCELLED"):
            self.next_btn.setEnabled(True)
            self.prev_btn.setEnabled(True)
            if job.state.stage == "DONE":
                self.status_label.setText("Completed successfully.")
            elif job.state.stage == "CANCELLED":
                self.status_label.setText("Cancelled.")
            else:
                msg = job.state.message or "Job failed."
                self.status_label.setText(f"Failed: {msg}")
                self._show_failure_popup(msg)

    def _show_failure_popup(self, message: str) -> None:
        if not message:
            message = "Job failed."
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Combined run failed")
        msg.setText(message)
        view_btn = msg.addButton("View Log", QMessageBox.AcceptRole)
        msg.addButton(QMessageBox.Ok)
        msg.exec()
        if msg.clickedButton() == view_btn and self._last_run_folder:
            dlg = RunReportDialog(self._last_run_folder, parent=self)
            dlg.exec()

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
            self.client_required.show_required(False)
            self._set_manual_visible(False)
            return
        if template_selected:
            self._set_manual_visible(False)
            self.rename_note.setText("Template selected; manual fields are ignored.")
            self.client_required.show_required(False)
            self._update_template_preview()
        else:
            self.rename_note.setText("No template selected. Provide Client Abbreviation and Start Index.")
            self._set_manual_visible(True)
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


def _wrap_scroll(widget: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    scroll.setWidget(widget)
    return scroll




def _scroll_to(scroll: QScrollArea, child: QWidget) -> None:
    if scroll.widget() is None:
        return
    if scroll.widget().height() <= scroll.viewport().height():
        return
    scroll.ensureWidgetVisible(child, xMargin=0, yMargin=20)
