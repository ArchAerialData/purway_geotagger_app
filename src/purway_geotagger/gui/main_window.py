from __future__ import annotations

from pathlib import Path
import shutil
import os
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QCheckBox, QSpinBox, QLineEdit, QProgressBar, QTableView,
    QMessageBox, QComboBox, QTabWidget, QGroupBox, QListWidget, QToolButton,
    QStyle
)

from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.widgets.drop_zone import DropZone
from purway_geotagger.gui.models.job_table_model import JobTableModel
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.widgets.template_editor import TemplateEditorDialog
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog
from purway_geotagger.gui.widgets.preview_dialog import PreviewDialog
from purway_geotagger.gui.widgets.schema_dialog import SchemaDialog
from purway_geotagger.gui.workers import PreviewWorker
from purway_geotagger.exif.exiftool_writer import is_exiftool_available

class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.setWindowTitle("Purway Geotagger")

        self.controller = JobController(settings=settings)
        self.controller.jobs_changed.connect(self._on_jobs_changed)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ----- Run tab -----
        run_tab = QWidget()
        run_layout = QVBoxLayout(run_tab)
        tabs.addTab(run_tab, "Run")

        input_group = QGroupBox("1) Add Inputs")
        input_layout = QVBoxLayout(input_group)
        input_layout.addWidget(QLabel("Drag & drop folders/files below (parent folder or many folders supported):"))
        self.drop_zone = DropZone()
        self.drop_zone.paths_dropped.connect(self._on_paths_dropped)
        input_layout.addWidget(self.drop_zone)
        run_layout.addWidget(input_group)

        out_group = QGroupBox("2) Output Folder")
        out_row = QHBoxLayout(out_group)
        self.out_dir_edit = QLineEdit(self.settings.last_output_dir)
        self.out_browse_btn = QPushButton("Select Output Folder…")
        self.out_browse_btn.clicked.connect(self._select_output_folder)
        out_row.addWidget(QLabel("Output:"))
        out_row.addWidget(self.out_dir_edit, 1)
        out_row.addWidget(self.out_browse_btn)
        out_row.addWidget(self._help_btn("Choose where processed files and logs will be saved."))
        run_layout.addWidget(out_group)

        basic_group = QGroupBox("3) Basic Options")
        basic_row = QHBoxLayout(basic_group)
        self.overwrite_chk = QCheckBox("Overwrite originals")
        self.overwrite_chk.setChecked(self.settings.overwrite_originals_default)
        self.overwrite_chk.setToolTip("Writes metadata into original JPGs in place.")
        self.dry_run_chk = QCheckBox("Dry run (no EXIF write)")
        self.dry_run_chk.setChecked(self.settings.dry_run_default)
        self.dry_run_chk.setToolTip("Match only; do not write EXIF/XMP.")
        basic_row.addWidget(self.overwrite_chk)
        basic_row.addWidget(self.dry_run_chk)
        basic_row.addWidget(self._help_btn("Tip: Most pilots can leave Basic Options unchecked and just press Run."))
        run_layout.addWidget(basic_group)

        self.advanced_group = QGroupBox("Advanced options (optional)")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        self.advanced_group.toggled.connect(self._on_advanced_toggled)
        adv_layout = QVBoxLayout(self.advanced_group)
        self.advanced_container = QWidget()
        adv_container_layout = QVBoxLayout(self.advanced_container)

        adv_row1 = QHBoxLayout()
        self.flatten_chk = QCheckBox("Flatten to single folder")
        self.flatten_chk.setChecked(self.settings.flatten_default)
        self.flatten_chk.setToolTip("Move all successful JPGs into JPG_FLAT.")
        self.flatten_chk.toggled.connect(self._on_flatten_toggle)
        self.cleanup_chk = QCheckBox("Cleanup empty dirs")
        self.cleanup_chk.setChecked(self.settings.cleanup_empty_dirs_default)
        self.cleanup_chk.setEnabled(self.flatten_chk.isChecked())
        self.cleanup_chk.setToolTip("Removes empty folders after flattening (scoped safely).")
        self.sort_chk = QCheckBox("Sort by PPM bins")
        self.sort_chk.setChecked(self.settings.sort_by_ppm_default)
        self.sort_chk.setToolTip("Copies output JPGs into PPM bin folders.")
        adv_row1.addWidget(self.flatten_chk)
        adv_row1.addWidget(self.cleanup_chk)
        adv_row1.addWidget(self.sort_chk)
        adv_container_layout.addLayout(adv_row1)

        adv_row2 = QHBoxLayout()
        self.write_xmp_chk = QCheckBox("Write XMP")
        self.write_xmp_chk.setChecked(self.settings.write_xmp_default)
        self.write_xmp_chk.setToolTip("Also write XMP GPS/Description tags.")
        adv_row2.addWidget(self.write_xmp_chk)
        adv_container_layout.addLayout(adv_row2)

        rename_row = QHBoxLayout()
        self.rename_chk = QCheckBox("Enable renaming")
        self.rename_chk.setChecked(False)
        self.rename_chk.setToolTip("Rename output JPGs using a template.")
        self.rename_chk.toggled.connect(self._on_rename_toggle)
        self.template_combo = QComboBox()
        self.template_combo.setEnabled(False)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self._template_user_selected = False
        self.template_combo.setToolTip("Select a rename template.")
        self.start_index_spin = QSpinBox()
        self.start_index_spin.setMinimum(1)
        self.start_index_spin.setMaximum(10_000_000)
        self.start_index_spin.setValue(1)
        self.start_index_spin.setEnabled(False)
        self.start_index_spin.setToolTip("Starting index for rename templates.")
        rename_row.addWidget(self.rename_chk)
        rename_row.addWidget(QLabel("Template:"))
        rename_row.addWidget(self.template_combo, 1)
        rename_row.addWidget(QLabel("Start index:"))
        rename_row.addWidget(self.start_index_spin)
        adv_container_layout.addLayout(rename_row)

        payload_row = QHBoxLayout()
        self.payload_edit = QLineEdit()
        self.payload_edit.setToolTip("Optional string stored in ImageDescription for downstream use.")
        payload_row.addWidget(QLabel("Purway payload (optional):"))
        payload_row.addWidget(self.payload_edit, 1)
        adv_container_layout.addLayout(payload_row)

        tools_row = QHBoxLayout()
        self.preview_btn = QPushButton("Preview matches")
        self.preview_btn.clicked.connect(self._preview_matches)
        self.preview_btn.setToolTip("Preview up to 20 matches before running.")
        self.preview_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogHelpButton))
        self.schema_btn = QPushButton("CSV schema")
        self.schema_btn.clicked.connect(self._show_schema)
        self.schema_btn.setToolTip("Show detected CSV columns and matches.")
        self.schema_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.settings_btn = QPushButton("Settings…")
        self.settings_btn.clicked.connect(self._open_settings)
        self.settings_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        tools_row.addWidget(self.preview_btn)
        tools_row.addWidget(self.schema_btn)
        tools_row.addWidget(self.settings_btn)
        adv_container_layout.addLayout(tools_row)

        adv_layout.addWidget(self.advanced_container)
        self.advanced_container.setVisible(False)
        run_layout.addWidget(self.advanced_group)

        run_actions = QHBoxLayout()
        self.run_btn = QPushButton("Run Job")
        self.run_btn.clicked.connect(self._run_job)
        self._style_primary_button(self.run_btn)
        self.clear_btn = QPushButton("Clear Inputs")
        self.clear_btn.clicked.connect(self._clear_inputs)
        run_actions.addWidget(self.run_btn)
        run_actions.addWidget(self.clear_btn)
        run_layout.addLayout(run_actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        run_layout.addWidget(self.progress)

        # ----- Jobs tab -----
        jobs_tab = QWidget()
        jobs_layout = QVBoxLayout(jobs_tab)
        tabs.addTab(jobs_tab, "Jobs")

        self.table = QTableView()
        self.model = JobTableModel(self.controller)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        jobs_layout.addWidget(self.table, 1)
        self.table.selectionModel().selectionChanged.connect(self._update_action_buttons)

        act_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel selected job")
        self.cancel_btn.clicked.connect(self._cancel_selected)
        self.cancel_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.open_out_btn = QPushButton("Open output folder")
        self.open_out_btn.clicked.connect(self._open_selected_output)
        self.open_out_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.rerun_failed_btn = QPushButton("Re-run failed only")
        self.rerun_failed_btn.clicked.connect(self._rerun_failed)
        self.rerun_failed_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.export_manifest_btn = QPushButton("Export manifest.csv")
        self.export_manifest_btn.clicked.connect(self._export_selected_manifest)
        self.export_manifest_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        act_row.addWidget(self.cancel_btn)
        act_row.addWidget(self.open_out_btn)
        act_row.addWidget(self.rerun_failed_btn)
        act_row.addWidget(self.export_manifest_btn)
        jobs_layout.addLayout(act_row)

        # ----- Templates tab -----
        templates_tab = QWidget()
        templates_layout = QVBoxLayout(templates_tab)
        tabs.addTab(templates_tab, "Templates")

        templates_layout.addWidget(QLabel("Templates are used when renaming is enabled on the Run tab."))
        self.templates_list = QListWidget()
        templates_layout.addWidget(self.templates_list, 1)
        tmpl_btn_row = QHBoxLayout()
        self.template_manage_btn = QPushButton("Open Template Editor…")
        self.template_manage_btn.clicked.connect(self._open_template_editor)
        self.template_refresh_btn = QPushButton("Refresh list")
        self.template_refresh_btn.clicked.connect(self._refresh_templates)
        tmpl_btn_row.addWidget(self.template_manage_btn)
        tmpl_btn_row.addWidget(self.template_refresh_btn)
        templates_layout.addLayout(tmpl_btn_row)

        # ----- Help tab -----
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        tabs.addTab(help_tab, "Help")

        help_text = QLabel(
            "Quick start:\n"
            "1) Drag & drop your Purway output folders.\n"
            "2) Choose an output folder.\n"
            "3) Click Run Job.\n\n"
            "Advanced options are optional. Use Preview if you want to validate a few matches first."
        )
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)

        help_actions = QHBoxLayout()
        self.help_run_btn = QPushButton("Go to Run tab")
        self.help_run_btn.clicked.connect(lambda: tabs.setCurrentIndex(0))
        self.help_jobs_btn = QPushButton("Go to Jobs tab")
        self.help_jobs_btn.clicked.connect(lambda: tabs.setCurrentIndex(1))
        help_actions.addWidget(self.help_run_btn)
        help_actions.addWidget(self.help_jobs_btn)
        help_layout.addLayout(help_actions)

        self._refresh_templates()
        self._update_inputs_state()

    @Slot(list)
    def _on_paths_dropped(self, paths: list[str]) -> None:
        self.controller.add_inputs([Path(p) for p in paths])
        self._auto_select_template()
        self._update_inputs_state()

    def _select_output_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output folder", self.out_dir_edit.text() or str(Path.home()))
        if d:
            self.out_dir_edit.setText(d)
            self.settings.last_output_dir = d

    def _clear_inputs(self) -> None:
        self.controller.clear_inputs()
        self._update_inputs_state()

    def _run_job(self) -> None:
        out = self.out_dir_edit.text().strip()
        if not out:
            QMessageBox.warning(self, "Output required", "Select an output folder.")
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
                self._open_settings()
            return
        if self.overwrite_chk.isChecked():
            msg = "You are about to overwrite original JPG files in place. This cannot be undone."
            if self.cleanup_chk.isChecked():
                msg += "\n\nCleanup of empty source folders is enabled and may remove empty directories under your selected input roots."
            msg += "\n\nContinue?"
            resp = QMessageBox.question(self, "Confirm overwrite originals", msg, QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return

        self.controller.start_job(
            output_root=Path(out),
            overwrite_originals=self.overwrite_chk.isChecked(),
            flatten=self.flatten_chk.isChecked(),
            cleanup_empty_dirs=self.cleanup_chk.isChecked(),
            sort_by_ppm=self.sort_chk.isChecked(),
            dry_run=self.dry_run_chk.isChecked(),
            write_xmp=self.write_xmp_chk.isChecked(),
            enable_renaming=self.rename_chk.isChecked(),
            rename_template_id=self.template_combo.currentData() if self.rename_chk.isChecked() else None,
            start_index=int(self.start_index_spin.value()),
            purway_payload=self.payload_edit.text().strip(),
            progress_bar=self.progress,
        )

    def _selected_job(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        row = sel[0].row()
        if row < 0 or row >= len(self.controller.jobs):
            return None
        return self.controller.jobs[row]

    def _cancel_selected(self) -> None:
        job = self._selected_job()
        if job:
            self.controller.cancel_job(job)

    def _open_selected_output(self) -> None:
        job = self._selected_job()
        if job:
            self.controller.open_output_folder(job)

    @Slot()
    def _on_jobs_changed(self) -> None:
        self.model.layoutChanged.emit()
        self._update_action_buttons()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, parent=self)
        if dlg.exec():
            self.cleanup_chk.setChecked(self.settings.cleanup_empty_dirs_default)
            self.write_xmp_chk.setChecked(self.settings.write_xmp_default)
            if self.settings.exiftool_path:
                os.environ["PURWAY_EXIFTOOL_PATH"] = self.settings.exiftool_path
            else:
                os.environ.pop("PURWAY_EXIFTOOL_PATH", None)

    def _open_template_editor(self) -> None:
        dlg = TemplateEditorDialog(self.controller.template_manager, parent=self)
        if dlg.exec():
            self._refresh_templates()

    def _refresh_templates(self) -> None:
        self.template_combo.clear()
        for t in self.controller.template_manager.list_templates():
            self.template_combo.addItem(t.name, userData=t.id)
        if hasattr(self, "templates_list"):
            self.templates_list.clear()
            for t in self.controller.template_manager.list_templates():
                self.templates_list.addItem(f"{t.name} ({t.id}) — {t.pattern}")
        self._template_user_selected = False
        self._auto_select_template()

    def _on_rename_toggle(self, enabled: bool) -> None:
        self.template_combo.setEnabled(enabled)
        self.start_index_spin.setEnabled(enabled)
        if enabled:
            self._auto_select_template()

    def _export_selected_manifest(self) -> None:
        job = self._selected_job()
        if not job:
            return
        src = self.controller.export_manifest_path(job)
        if not src:
            QMessageBox.information(self, "Manifest not available", "manifest.csv is not available for this job yet.")
            return
        default_name = str(Path(job.run_folder) / "manifest.csv") if job.run_folder else str(src)
        dst, _ = QFileDialog.getSaveFileName(self, "Export manifest.csv", default_name, "CSV Files (*.csv)")
        if not dst:
            return
        shutil.copy2(src, dst)

    def _update_action_buttons(self) -> None:
        job = self._selected_job()
        if not job:
            self.cancel_btn.setEnabled(False)
            self.open_out_btn.setEnabled(False)
            self.export_manifest_btn.setEnabled(False)
            self.rerun_failed_btn.setEnabled(False)
            return
        stage = job.state.stage
        can_cancel = stage not in ("DONE", "FAILED", "CANCELLED")
        self.cancel_btn.setEnabled(can_cancel)

        done = stage == "DONE"
        self.open_out_btn.setEnabled(done)
        manifest = self.controller.export_manifest_path(job)
        self.export_manifest_btn.setEnabled(done and manifest is not None)
        self.rerun_failed_btn.setEnabled(done and manifest is not None)

    def _preview_matches(self) -> None:
        if not self.controller.inputs:
            QMessageBox.information(self, "No inputs", "Drop folders/files to preview.")
            return
        self.preview_btn.setEnabled(False)
        worker = PreviewWorker(
            inputs=self.controller.inputs.copy(),
            max_rows=20,
            max_join_delta_seconds=self.settings.max_join_delta_seconds,
        )
        worker.finished.connect(lambda result: self._show_preview_result(worker, result))
        worker.failed.connect(lambda err: self._show_preview_error(worker, err))
        worker.start()

    def _show_preview_result(self, worker: PreviewWorker, result) -> None:
        dlg = PreviewDialog(result, parent=self)
        dlg.exec()
        self.preview_btn.setEnabled(True)
        worker.quit()
        worker.wait()

    def _show_preview_error(self, worker: PreviewWorker, err: str) -> None:
        QMessageBox.warning(self, "Preview failed", err)
        self.preview_btn.setEnabled(True)
        worker.quit()
        worker.wait()

    def _show_schema(self) -> None:
        if not self.controller.inputs:
            QMessageBox.information(self, "No inputs", "Drop folders/files to inspect.")
            return
        worker = PreviewWorker(
            inputs=self.controller.inputs.copy(),
            max_rows=0,
            max_join_delta_seconds=self.settings.max_join_delta_seconds,
        )
        worker.finished.connect(lambda result: self._show_schema_result(worker, result))
        worker.failed.connect(lambda err: self._show_preview_error(worker, err))
        worker.start()

    def _show_schema_result(self, worker: PreviewWorker, result) -> None:
        dlg = SchemaDialog(result.schemas, parent=self)
        dlg.exec()
        worker.quit()
        worker.wait()

    def _rerun_failed(self) -> None:
        job = self._selected_job()
        if not job:
            return
        new_job = self.controller.rerun_failed_only(job, self.progress)
        if not new_job:
            QMessageBox.information(self, "No failed photos", "No failed photos found to re-run.")

    def _auto_select_template(self) -> None:
        if not self.rename_chk.isChecked() or self._template_user_selected:
            return
        suggested = self.controller.suggest_template_id(self.controller.inputs)
        if suggested is None:
            return
        for i in range(self.template_combo.count()):
            if self.template_combo.itemData(i) == suggested:
                self.template_combo.setCurrentIndex(i)
                break

    def _on_template_changed(self, _idx: int) -> None:
        if self.template_combo.isEnabled():
            self._template_user_selected = True

    def _help_btn(self, text: str) -> QToolButton:
        btn = QToolButton()
        btn.setText("?")
        btn.setToolTip(text)
        btn.setAutoRaise(True)
        btn.setFixedSize(18, 18)
        return btn

    def _style_primary_button(self, btn: QPushButton) -> None:
        f = btn.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 2)
        btn.setFont(f)
        btn.setMinimumHeight(36)
        btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        btn.setDefault(True)

    def _on_advanced_toggled(self, enabled: bool) -> None:
        self.advanced_container.setVisible(enabled)
        self._update_inputs_state()

    def _on_flatten_toggle(self, enabled: bool) -> None:
        self.cleanup_chk.setEnabled(enabled)
        if not enabled:
            self.cleanup_chk.setChecked(False)

    def _update_inputs_state(self) -> None:
        has_inputs = len(self.controller.inputs) > 0
        self.run_btn.setEnabled(has_inputs)
        self.preview_btn.setEnabled(has_inputs and self.advanced_group.isChecked())
        self.schema_btn.setEnabled(has_inputs and self.advanced_group.isChecked())
