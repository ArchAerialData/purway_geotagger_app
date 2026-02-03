from __future__ import annotations

from pathlib import Path
import shutil
import os
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QCheckBox, QSpinBox, QLineEdit, QProgressBar, QTableView,
    QMessageBox, QComboBox, QTabWidget, QGroupBox, QListWidget, QToolButton,
    QStyle, QApplication, QStackedWidget
)

from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.modes import RunMode
from purway_geotagger.gui.widgets.drop_zone import DropZone
from purway_geotagger.gui.models.job_table_model import JobTableModel
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
from purway_geotagger.gui.pages import HomePage, MethanePage, EncroachmentPage, CombinedWizard
from purway_geotagger.gui.widgets.template_editor import TemplateEditorDialog
from purway_geotagger.gui.widgets.theme_toggle import ThemeToggle
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog
from purway_geotagger.gui.widgets.preview_dialog import PreviewDialog
from purway_geotagger.gui.widgets.schema_dialog import SchemaDialog
from purway_geotagger.gui.widgets.run_report_view import RunReportDialog
from purway_geotagger.gui.workers import PreviewWorker
from purway_geotagger.gui.theme import apply_theme
from purway_geotagger.exif.exiftool_writer import is_exiftool_available

class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.setWindowTitle("Purway Geotagger")
        self.resize(980, 680)
        self.setMinimumSize(780, 560)

        self.controller = JobController(settings=settings)
        self.controller.jobs_changed.connect(self._on_jobs_changed)

        self._mode_states = {
            RunMode.METHANE: ModeState(mode=RunMode.METHANE),
            RunMode.ENCROACHMENT: ModeState(mode=RunMode.ENCROACHMENT),
            RunMode.COMBINED: ModeState(mode=RunMode.COMBINED),
        }
        self._last_mode = self._parse_last_mode(self.settings.last_mode)
        self._mode_pages: dict[RunMode, QWidget] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.theme_toggle = ThemeToggle(self.settings.ui_theme)
        self.theme_toggle.theme_changed.connect(self._on_theme_changed)
        tabs.setCornerWidget(self.theme_toggle, Qt.TopRightCorner)

        # ----- Run tab (home + modes) -----
        run_tab = QWidget()
        run_layout = QVBoxLayout(run_tab)
        tabs.addTab(run_tab, "Run")

        self.run_stack = QStackedWidget()
        run_layout.addWidget(self.run_stack, 1)

        self.home_page = HomePage()
        self.home_page.set_last_mode(self._last_mode)
        self.home_page.mode_selected.connect(self._on_mode_selected)

        self.methane_page = MethanePage(self._mode_states[RunMode.METHANE], self.controller)
        self.encroachment_page = EncroachmentPage(self._mode_states[RunMode.ENCROACHMENT], self.controller)
        self.combined_page = CombinedWizard(self._mode_states[RunMode.COMBINED], self.controller)

        self.methane_page.back_requested.connect(self._show_home)
        self.encroachment_page.back_requested.connect(self._show_home)
        self.combined_page.back_requested.connect(self._show_home)

        self.run_stack.addWidget(self.home_page)
        self.run_stack.addWidget(self.methane_page)
        self.run_stack.addWidget(self.encroachment_page)
        self.run_stack.addWidget(self.combined_page)
        self._mode_pages = {
            RunMode.METHANE: self.methane_page,
            RunMode.ENCROACHMENT: self.encroachment_page,
            RunMode.COMBINED: self.combined_page,
        }

        self.run_stack.setCurrentWidget(self.home_page)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
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
        self.view_report_btn = QPushButton("View run report")
        self.view_report_btn.clicked.connect(self._view_selected_report)
        self.view_report_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        act_row.addWidget(self.cancel_btn)
        act_row.addWidget(self.open_out_btn)
        act_row.addWidget(self.rerun_failed_btn)
        act_row.addWidget(self.export_manifest_btn)
        act_row.addWidget(self.view_report_btn)
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
            "1) Open the Run tab and select a report type.\n"
            "2) Add inputs and configure options for that mode.\n"
            "3) Confirm settings and run.\n\n"
            "Templates are managed under the Templates tab."
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

    def _on_mode_selected(self, mode: RunMode) -> None:
        self._show_mode(mode)

    def _show_mode(self, mode: RunMode) -> None:
        page = self._mode_pages.get(mode)
        if not page:
            return
        self._set_last_mode(mode)
        refresh = getattr(page, "refresh_summary", None)
        if callable(refresh):
            refresh()
        self.run_stack.setCurrentWidget(page)

    def _show_home(self) -> None:
        self.run_stack.setCurrentWidget(self.home_page)
        self.home_page.set_last_mode(self._last_mode)

    def _set_last_mode(self, mode: RunMode) -> None:
        self._last_mode = mode
        self.settings.last_mode = mode.value
        self.settings.save()
        self.home_page.set_last_mode(mode)

    def _parse_last_mode(self, value: str) -> RunMode | None:
        if not value:
            return None
        try:
            return RunMode(value)
        except ValueError:
            return None

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
            if hasattr(self, "cleanup_chk"):
                self.cleanup_chk.setChecked(self.settings.cleanup_empty_dirs_default)
            if hasattr(self, "write_xmp_chk"):
                self.write_xmp_chk.setChecked(self.settings.write_xmp_default)
            if self.settings.exiftool_path:
                os.environ["PURWAY_EXIFTOOL_PATH"] = self.settings.exiftool_path
            else:
                os.environ.pop("PURWAY_EXIFTOOL_PATH", None)
            app = QApplication.instance()
            if app:
                apply_theme(app, self.settings.ui_theme)
            if hasattr(self, "theme_toggle"):
                self.theme_toggle.set_theme(self.settings.ui_theme)

    def _open_template_editor(self) -> None:
        dlg = TemplateEditorDialog(self.controller.template_manager, parent=self)
        if dlg.exec():
            self._refresh_templates()

    def _refresh_templates(self) -> None:
        if hasattr(self, "template_combo"):
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
            self.view_report_btn.setEnabled(False)
            return
        stage = job.state.stage
        can_cancel = stage not in ("DONE", "FAILED", "CANCELLED")
        self.cancel_btn.setEnabled(can_cancel)

        has_run_folder = job.run_folder is not None
        manifest = self.controller.export_manifest_path(job)
        self.open_out_btn.setEnabled(has_run_folder)
        self.export_manifest_btn.setEnabled(manifest is not None)
        self.rerun_failed_btn.setEnabled(manifest is not None)
        self.view_report_btn.setEnabled(has_run_folder)

    def _view_selected_report(self) -> None:
        job = self._selected_job()
        if not job or not job.run_folder:
            QMessageBox.information(self, "Run report not available", "Run report is not available yet.")
            return
        dlg = RunReportDialog(job.run_folder, parent=self)
        dlg.exec()

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
        if not hasattr(self, "rename_chk") or not hasattr(self, "template_combo"):
            return
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
            template_id = self.template_combo.currentData()
            tmpl = self.controller.template_manager.templates.get(template_id)
            if tmpl:
                value = max(1, int(tmpl.start_index))
                self.start_index_spin.setValue(min(value, self.start_index_spin.maximum()))

    def _on_theme_changed(self, theme: str) -> None:
        self.settings.ui_theme = theme
        self.settings.save()
        app = QApplication.instance()
        if app:
            apply_theme(app, theme)
        self.theme_toggle.refresh_icons()

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
        if not hasattr(self, "run_btn"):
            return
        has_inputs = len(self.controller.inputs) > 0
        self.run_btn.setEnabled(has_inputs)
        advanced_enabled = bool(getattr(self, "advanced_group", None) and self.advanced_group.isChecked())
        if hasattr(self, "preview_btn"):
            self.preview_btn.setEnabled(has_inputs and advanced_enabled)
        if hasattr(self, "schema_btn"):
            self.schema_btn.setEnabled(has_inputs and advanced_enabled)
