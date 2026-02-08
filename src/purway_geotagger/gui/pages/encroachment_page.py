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
    QLineEdit,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QMessageBox,
    QProgressBar,
    QFrame,
    QSizePolicy,
    QScrollArea,
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
from purway_geotagger.gui.widgets.run_report_view import RunReportDialog
from purway_geotagger.gui.widgets.sticky_nav_row import StickyNavRow


class EncroachmentPage(QWidget):
    back_requested = Signal()
    home_requested = Signal()
    run_another_requested = Signal()

    def __init__(self, state: ModeState, controller: JobController, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.controller = controller
        self._output_auto = True
        self._last_job_id: str | None = None
        self._last_run_folder: Path | None = None
        self.controller.jobs_changed.connect(self._on_jobs_changed)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        self._nav_layout = nav_layout
        nav_layout.setContentsMargins(40, 16, 40, 0)
        nav_layout.setSpacing(8)
        self.nav_row = StickyNavRow()
        self.nav_row.back_requested.connect(self.back_requested.emit)
        self.nav_row.home_requested.connect(self.home_requested.emit)
        self.nav_context = QLabel("Run / Encroachment")
        self.nav_context.setProperty("cssClass", "breadcrumb")
        nav_layout.addWidget(self.nav_row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        nav_layout.addWidget(self.nav_context, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        nav_layout.addStretch(1)
        main_layout.addWidget(nav_container)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(24)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        self._apply_responsive_spacing(self.width())

        title = QLabel("Encroachment Reports Only")
        title.setProperty("cssClass", "h1")
        self.content_layout.addWidget(title)

        # --- Section 1: Inputs ---
        input_card = QFrame()
        input_card.setProperty("cssClass", "card")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(16)

        lbl_h2_in = QLabel("1) Add Inputs")
        lbl_h2_in.setProperty("cssClass", "h2")
        input_layout.addWidget(lbl_h2_in)

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
        
        self.content_layout.addWidget(input_card)

        # --- Section 2: Output ---
        output_card = QFrame()
        output_card.setProperty("cssClass", "card")
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(20, 20, 20, 20)
        output_layout.setSpacing(16)

        lbl_h2_out = QLabel("2) Output Folder (required)")
        lbl_h2_out.setProperty("cssClass", "h2")
        output_layout.addWidget(lbl_h2_out)

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
        
        output_help = QLabel("Defaults to Encroachment_Output under the common input root.")
        output_help.setProperty("cssClass", "subtitle")
        output_help.setWordWrap(True)
        output_layout.addWidget(output_help)

        self.exif_note = QLabel(
            "EXIF note: Encroachment runs write metadata to copied JPGs in the selected output "
            "folder. Source JPGs remain unchanged."
        )
        self.exif_note.setProperty("cssClass", "subtitle")
        self.exif_note.setWordWrap(True)
        output_layout.addWidget(self.exif_note)
        
        self.content_layout.addWidget(output_card)

        # --- Section 3: Renaming ---
        rename_card = QFrame()
        rename_card.setProperty("cssClass", "card")
        rename_layout = QVBoxLayout(rename_card)
        rename_layout.setContentsMargins(20, 20, 20, 20)
        rename_layout.setSpacing(16)

        lbl_h2_rename = QLabel("3) Renaming (optional)")
        lbl_h2_rename.setProperty("cssClass", "h2")
        rename_layout.addWidget(lbl_h2_rename)

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
        # We can rely on cssClass subtitle, which is already grey. 
        # But if we want it distinctly lighter, subtitle should be fine.
        rename_layout.addWidget(self.rename_note)

        self.rename_scope_note = QLabel(
            "Renaming scope: applies only to copied encroachment JPGs in the selected output "
            "folder. Source files and methane outputs are not renamed."
        )
        self.rename_scope_note.setProperty("cssClass", "subtitle")
        self.rename_scope_note.setWordWrap(True)
        rename_layout.addWidget(self.rename_scope_note)

        self.rename_order_note = QLabel(
            "Index/order: files are grouped by source folder and processed chronologically "
            "(EXIF DateTimeOriginal, then filename timestamp fallback), then by filename. "
            "Start Index increments sequentially."
        )
        self.rename_order_note.setProperty("cssClass", "subtitle")
        self.rename_order_note.setWordWrap(True)
        rename_layout.addWidget(self.rename_order_note)
        
        self.content_layout.addWidget(rename_card)

        # --- A ctions ---
        actions_row = QHBoxLayout()
        self.view_log_btn = QPushButton("View log…")
        self.view_log_btn.setEnabled(False)
        self.view_log_btn.clicked.connect(self._view_log)
        actions_row.addWidget(self.view_log_btn)
        self.view_outputs_btn = QPushButton("View output files…")
        self.view_outputs_btn.setVisible(False)
        self.view_outputs_btn.setEnabled(False)
        self.view_outputs_btn.clicked.connect(self._view_outputs)
        actions_row.addWidget(self.view_outputs_btn)

        actions_row.addStretch(1)

        self.run_another_btn = QPushButton("Run another folder")
        self.run_another_btn.setVisible(False)
        self.run_another_btn.clicked.connect(self._run_another)
        actions_row.addWidget(self.run_another_btn)

        self.run_btn = QPushButton("Run Encroachment")
        self.run_btn.setProperty("cssClass", "run")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._run_encroachment)
        self.run_btn.setMinimumHeight(44)
        actions_row.addWidget(self.run_btn)
        self.content_layout.addLayout(actions_row)

        self.run_help = QLabel(
            "What happens when I click Run? JPGs are copied to the output folder, EXIF metadata "
            "is written on the copies, optional renaming is applied, and run artifacts are saved."
        )
        self.run_help.setProperty("cssClass", "subtitle")
        self.run_help.setWordWrap(True)
        self.content_layout.addWidget(self.run_help)

        
        self.status_label = QLabel("")
        self.status_label.setProperty("cssClass", "subtitle")
        self.status_label.setWordWrap(True)
        self.content_layout.addWidget(self.status_label)

        self.content_layout.addStretch(1)

        self._refresh_templates()
        self.refresh_summary()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_spacing(event.size().width())

    def _apply_responsive_spacing(self, width: int) -> None:
        # CHG-007: align nav/content rhythm across common macOS laptop widths.
        if width >= 1500:
            side, nav_top, content_top, content_bottom, gap = 48, 16, 34, 32, 24
        elif width >= 1200:
            side, nav_top, content_top, content_bottom, gap = 36, 14, 28, 28, 22
        elif width >= 1000:
            side, nav_top, content_top, content_bottom, gap = 28, 12, 22, 24, 20
        else:
            side, nav_top, content_top, content_bottom, gap = 20, 10, 18, 20, 18
        self._nav_layout.setContentsMargins(side, nav_top, side, 0)
        self.content_layout.setContentsMargins(side, content_top, side, content_bottom)
        self.content_layout.setSpacing(gap)
        self.nav_context.setVisible(width >= 980)

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

    def reset_for_new_run(self) -> None:
        self._last_job_id = None
        self._last_run_folder = None
        self.status_label.setText("")
        self.run_another_btn.setVisible(False)
        self.view_outputs_btn.setVisible(False)
        self.state.inputs = []
        self.state.encroachment_output_base = None
        self.state.encroachment_rename_enabled = False
        self.state.encroachment_template_id = None
        self.state.encroachment_client_abbr = ""
        self.state.encroachment_start_index = 1
        self._output_auto = True
        self.refresh_summary()
        self._update_view_log_buttons()
        self._update_view_outputs_button()

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

        if not self._confirm_run(
            "Encroachment mode copies JPGs to the output folder, writes EXIF on the copies, "
            "and may rename copied files only.\n\nContinue?",
            "confirm_encroachment",
            "Confirm encroachment run",
        ):
            return

        progress_bar = self.window().progress if hasattr(self.window(), "progress") else None
        if progress_bar:
            progress_bar.setVisible(True)
        self.run_btn.setEnabled(False)
        self.run_another_btn.setVisible(False)
        self.view_outputs_btn.setVisible(False)
        self.status_label.setText("Running encroachment job...")
        job = self.controller.start_job_from_mode_state(self.state, progress_bar)
        self._last_job_id = job.id if job else None
        self._last_run_folder = job.run_folder if job else None
        self._update_view_log_buttons()
        self._update_view_outputs_button()

    def _log_path(self) -> Path | None:
        if not self._last_run_folder:
            return None
        return self._last_run_folder / "run_log.txt"

    def _summary_path(self) -> Path | None:
        if not self._last_run_folder:
            return None
        return self._last_run_folder / "run_summary.json"

    def _update_view_log_buttons(self) -> None:
        path = self._log_path()
        self.view_log_btn.setEnabled(bool(path and path.exists()))

    def _update_view_outputs_button(self) -> None:
        path = self._summary_path()
        self.view_outputs_btn.setEnabled(bool(path and path.exists()))

    def _view_log(self) -> None:
        if not self._last_run_folder:
            QMessageBox.information(self, "Log not available", "Run log not available yet.")
            return
        dlg = RunReportDialog(self._last_run_folder, parent=self)
        dlg.exec()

    def _view_outputs(self) -> None:
        if not self._last_run_folder:
            QMessageBox.information(self, "Outputs not available", "Run outputs not available yet.")
            return
        dlg = RunReportDialog(self._last_run_folder, parent=self)
        dlg.exec()

    def _on_jobs_changed(self) -> None:
        if not self._last_job_id:
            return
        job = next((j for j in self.controller.jobs if j.id == self._last_job_id), None)
        if not job:
            return
        if self._last_run_folder is None:
            self._last_run_folder = job.run_folder
            self._update_view_log_buttons()
            self._update_view_outputs_button()
        if job.state.stage in ("DONE", "FAILED", "CANCELLED"):
            self.run_btn.setEnabled(True)
            self.run_another_btn.setVisible(True)
            self.view_outputs_btn.setVisible(True)
            if job.state.stage == "DONE":
                self.status_label.setText("Completed successfully.")
            elif job.state.stage == "CANCELLED":
                self.status_label.setText("Cancelled.")
            else:
                msg = job.state.message or "Job failed."
                self.status_label.setText(f"Failed: {msg}")
                self._show_failure_popup(msg)
            self._update_view_log_buttons()
            self._update_view_outputs_button()

    def _show_failure_popup(self, message: str) -> None:
        if not message:
            message = "Job failed."
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Encroachment run failed")
        msg.setText(message)
        view_btn = msg.addButton("View Log", QMessageBox.AcceptRole)
        msg.addButton(QMessageBox.Ok)
        msg.exec()
        if msg.clickedButton() == view_btn:
            self._view_log()

    def _confirm_run(self, message: str, setting_attr: str, title: str) -> bool:
        settings = self.controller.settings
        if not getattr(settings, setting_attr, True):
            return True
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle(title)
        msg.setText(message)
        checkbox = QCheckBox("Don't show again")
        msg.setCheckBox(checkbox)
        yes_btn = msg.addButton("Yes", QMessageBox.AcceptRole)
        msg.addButton("No", QMessageBox.RejectRole)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            if checkbox.isChecked():
                setattr(settings, setting_attr, False)
                settings.save()
            return True
        return False

    def _run_another(self) -> None:
        self.run_another_requested.emit()
        main = self.window()
        progress = getattr(main, "progress", None)
        if progress is not None:
            progress.setValue(0)
            progress.setVisible(False)
        self.home_requested.emit()
