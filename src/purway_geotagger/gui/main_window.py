from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import os
from PySide6.QtCore import Qt, Slot, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QCheckBox, QSpinBox, QLineEdit, QProgressBar, QTableView,
    QMessageBox, QComboBox, QListWidget, QToolButton,
    QStyle, QApplication, QStackedWidget, QButtonGroup, QFrame,
    QSplitter, QFormLayout, QHeaderView, QMenu
)


from PySide6.QtGui import QIcon, QPixmap
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.utils import resource_path


from purway_geotagger.core.modes import RunMode
from purway_geotagger.gui.widgets.drop_zone import DropZone
from purway_geotagger.gui.models.job_table_model import JobTableModel
from purway_geotagger.gui.models.jobs_filter_proxy_model import JobsFilterProxyModel
from purway_geotagger.gui.controllers import JobController
from purway_geotagger.gui.mode_state import ModeState
from purway_geotagger.gui.pages.home_page import HomePage
from purway_geotagger.gui.pages.methane_page import MethanePage
from purway_geotagger.gui.pages.encroachment_page import EncroachmentPage
from purway_geotagger.gui.pages.combined_wizard import CombinedWizard
from purway_geotagger.gui.pages.help_page import HelpPage
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
        self.resize(1100, 900)
        self.setMinimumSize(900, 750)

        self.controller = JobController(settings=settings)
        self.controller.jobs_changed.connect(self._on_jobs_changed)

        self._mode_states = {
            RunMode.METHANE: ModeState(mode=RunMode.METHANE),
            RunMode.ENCROACHMENT: ModeState(mode=RunMode.ENCROACHMENT),
            RunMode.COMBINED: ModeState(mode=RunMode.COMBINED),
        }
        for state in self._mode_states.values():
            state.methane_generate_kmz = True
        self._last_mode = self._parse_last_mode(self.settings.last_mode)
        self._mode_pages: dict[RunMode, QWidget] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ----- Main Stack for Tabs -----
        self.main_stack = QStackedWidget()

        # ----- Header with Inline Nav -----
        header_widget = QWidget()
        header_widget.setObjectName("mainHeader")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(24, 12, 24, 12)
        header_layout.setSpacing(24)
        
        # 1. Logo
        self.logo_label = QLabel()
        self.logo_label.setScaledContents(True)
        self.logo_label.setFixedHeight(90)
        # Explicit alignment
        header_layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 2. Navigation Buttons (acting as tabs)
        # Wrap in a container widget to enforce vertical centering in the main header layout
        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        def _create_nav_btn(text: str, index: int) -> QPushButton:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            # Basic styling for nav buttons
            btn.setProperty("cssClass", "nav_btn")

            self.nav_group.addButton(btn, index)
            # Use lambda with default arg to capture index correctly
            btn.clicked.connect(lambda checked=False, idx=index: self.main_stack.setCurrentIndex(idx))
            nav_layout.addWidget(btn)
            return btn

        self.btn_run = _create_nav_btn("Run", 0)
        self.btn_jobs = _create_nav_btn("Jobs", 1)
        self.btn_templates = _create_nav_btn("Templates", 2)
        self.btn_help = _create_nav_btn("Help", 3)
        self.btn_run.setChecked(True)

        # Add the container with Center alignment
        header_layout.addWidget(nav_container, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addStretch(1)
        
        # 4. Version / Status
        self.version_label = QLabel("v1.0.0")
        self.version_label.setProperty("cssClass", "subtitle")
        header_layout.addWidget(self.version_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 5. Settings Button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setProperty("cssClass", "nav_btn")
        self.settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # 3. Theme Toggle
        self.theme_toggle = ThemeToggle(self.settings.ui_theme)
        self.theme_toggle.theme_changed.connect(self._on_theme_changed)
        header_layout.addWidget(self.theme_toggle, alignment=Qt.AlignmentFlag.AlignVCenter)

        
        layout.addWidget(header_widget)
        layout.addWidget(self.main_stack, 1) # Give stack stretch factor 1

        # Re-apply theme to ensure logo is set
        self._on_theme_changed(self.settings.ui_theme)
        
        # Set App Icon
        icon_path = resource_path("assets/aallc_logos/AALLC_CircleLogo_2023_V3_White.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))



        # ----- Tab 1: Run (Home + Modes) -----
        run_tab = QWidget()
        run_layout = QVBoxLayout(run_tab)
        # Add some padding to the content area since we removed global margins
        run_layout.setContentsMargins(20, 20, 20, 20) 
        self.main_stack.addWidget(run_tab)

        self.run_stack = QStackedWidget()
        run_layout.addWidget(self.run_stack, 1)

        self.home_page = HomePage()

        self.home_page.set_last_mode(self._last_mode)
        self.home_page.mode_selected.connect(self._on_mode_selected)

        self.methane_page = MethanePage(self._mode_states[RunMode.METHANE], self.controller)
        self.encroachment_page = EncroachmentPage(self._mode_states[RunMode.ENCROACHMENT], self.controller)
        self.combined_page = CombinedWizard(self._mode_states[RunMode.COMBINED], self.controller)

        self.methane_page.back_requested.connect(self._show_home)
        self.methane_page.home_requested.connect(self._show_home)
        self.methane_page.run_another_requested.connect(self._reset_all_modes_and_home)
        self.encroachment_page.back_requested.connect(self._show_home)
        self.encroachment_page.home_requested.connect(self._show_home)
        self.encroachment_page.run_another_requested.connect(self._reset_all_modes_and_home)
        self.combined_page.home_requested.connect(self._show_home)
        self.combined_page.run_another_requested.connect(self._reset_all_modes_and_home)

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

        # Footer with Global Progress Bar
        self.progress = QProgressBar()
        self.progress.setObjectName("globalProgress")
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(40) 
        self.progress.setVisible(False)
        
        layout.addWidget(self.progress, 0) # Give footer stretch factor 0

        # ----- Tab 2: Jobs -----
        jobs_tab = QWidget()
        jobs_layout = QVBoxLayout(jobs_tab)
        jobs_layout.setContentsMargins(20, 20, 20, 20)
        jobs_layout.setSpacing(12)
        self.main_stack.addWidget(jobs_tab)

        jobs_intro = QFrame()
        jobs_intro.setProperty("cssClass", "card")
        jobs_intro_layout = QVBoxLayout(jobs_intro)
        jobs_intro_layout.setContentsMargins(16, 16, 16, 16)
        jobs_intro_layout.setSpacing(10)
        jobs_title = QLabel("Recent Jobs")
        jobs_title.setProperty("cssClass", "h2")
        jobs_subtitle = QLabel("Simple view by default. Use filters and toggles for deeper diagnostics.")
        jobs_subtitle.setProperty("cssClass", "subtitle")
        jobs_subtitle.setWordWrap(True)
        jobs_intro_layout.addWidget(jobs_title)
        jobs_intro_layout.addWidget(jobs_subtitle)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        self.jobs_status_group = QButtonGroup(self)
        self.jobs_status_group.setExclusive(True)
        self._jobs_filter_keys: dict[QToolButton, str] = {}

        def _make_filter_chip(text: str, key: str, checked: bool = False) -> QToolButton:
            btn = QToolButton()
            btn.setText(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("cssClass", "chip")
            btn.setAutoRaise(False)
            btn.setChecked(checked)
            self.jobs_status_group.addButton(btn)
            self._jobs_filter_keys[btn] = key
            return btn

        controls_row.addWidget(_make_filter_chip("All", "all", checked=True))
        controls_row.addWidget(_make_filter_chip("Running", "running"))
        controls_row.addWidget(_make_filter_chip("Failed", "failed"))
        controls_row.addWidget(_make_filter_chip("Completed", "completed"))

        self.jobs_search_edit = QLineEdit()
        self.jobs_search_edit.setPlaceholderText("Search job name, mode, path, or message")
        controls_row.addWidget(self.jobs_search_edit, 1)

        self.jobs_show_all_chk = QCheckBox("Show all history")
        controls_row.addWidget(self.jobs_show_all_chk)
        self.jobs_advanced_chk = QCheckBox("Show advanced columns")
        controls_row.addWidget(self.jobs_advanced_chk)
        self.jobs_details_toggle = QCheckBox("Show details panel")
        controls_row.addWidget(self.jobs_details_toggle)
        jobs_intro_layout.addLayout(controls_row)
        jobs_layout.addWidget(jobs_intro)

        jobs_splitter = QSplitter(Qt.Horizontal)
        jobs_splitter.setChildrenCollapsible(False)

        jobs_left = QWidget()
        jobs_left_layout = QVBoxLayout(jobs_left)
        jobs_left_layout.setContentsMargins(0, 0, 0, 0)
        jobs_left_layout.setSpacing(8)

        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setSectionsMovable(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

        self.model = JobTableModel(self.controller)
        self.jobs_proxy = JobsFilterProxyModel(self)
        self.jobs_proxy.setSourceModel(self.model)
        self.jobs_proxy.set_recent_limit(20)
        self.table.setModel(self.jobs_proxy)
        self.table.sortByColumn(0, Qt.DescendingOrder)
        self.table.selectionModel().selectionChanged.connect(self._update_action_buttons)
        jobs_left_layout.addWidget(self.table, 1)

        self.jobs_empty_label = QLabel("No jobs yet. Start a run from the Run tab.")
        self.jobs_empty_label.setProperty("cssClass", "muted")
        self.jobs_empty_label.setVisible(False)
        jobs_left_layout.addWidget(self.jobs_empty_label)

        act_row = QHBoxLayout()
        act_row.setSpacing(8)
        self.view_report_btn = QPushButton("View Report")
        self.view_report_btn.clicked.connect(self._view_selected_report)
        self.view_report_btn.setProperty("cssClass", "primary")
        self.open_out_btn = QPushButton("Open Output")
        self.open_out_btn.clicked.connect(self._open_selected_output)
        self.open_out_btn.setProperty("cssClass", "open_file")
        self.jobs_more_btn = QToolButton()
        self.jobs_more_btn.setText("More")
        self.jobs_more_btn.setPopupMode(QToolButton.InstantPopup)
        self.jobs_more_btn.setCursor(Qt.PointingHandCursor)
        self.jobs_more_btn.setProperty("cssClass", "chip")
        self.jobs_more_menu = QMenu(self.jobs_more_btn)
        self.cancel_action = self.jobs_more_menu.addAction("Cancel selected job")
        self.cancel_action.triggered.connect(self._cancel_selected)
        self.rerun_failed_action = self.jobs_more_menu.addAction("Re-run failed only")
        self.rerun_failed_action.triggered.connect(self._rerun_failed)
        self.export_manifest_action = self.jobs_more_menu.addAction("Export manifest.csv")
        self.export_manifest_action.triggered.connect(self._export_selected_manifest)
        self.jobs_more_btn.setMenu(self.jobs_more_menu)

        act_row.addWidget(self.view_report_btn)
        act_row.addWidget(self.open_out_btn)
        act_row.addWidget(self.jobs_more_btn)
        act_row.addStretch(1)
        jobs_left_layout.addLayout(act_row)
        jobs_splitter.addWidget(jobs_left)

        self.jobs_detail_panel = QFrame()
        self.jobs_detail_panel.setProperty("cssClass", "card")
        jobs_detail_layout = QVBoxLayout(self.jobs_detail_panel)
        jobs_detail_layout.setContentsMargins(16, 16, 16, 16)
        jobs_detail_layout.setSpacing(12)
        detail_title = QLabel("Job Details")
        detail_title.setProperty("cssClass", "label_strong")
        jobs_detail_layout.addWidget(detail_title)
        self.jobs_detail_status_badge = QLabel("No selection")
        self.jobs_detail_status_badge.setProperty("cssClass", "status_badge")
        self.jobs_detail_status_badge.setProperty("status", "idle")
        jobs_detail_layout.addWidget(self.jobs_detail_status_badge, alignment=Qt.AlignmentFlag.AlignLeft)
        self.jobs_detail_hint = QLabel("Select a job to view detailed metrics.")
        self.jobs_detail_hint.setWordWrap(True)
        self.jobs_detail_hint.setProperty("cssClass", "muted")
        jobs_detail_layout.addWidget(self.jobs_detail_hint)
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        self.jobs_detail_values: dict[str, QLabel] = {}
        for key, label in (
            ("name", "Job"),
            ("started", "Started"),
            ("mode", "Mode"),
            ("progress", "Progress"),
            ("inputs", "Inputs"),
            ("scanned", "Scanned"),
            ("matched", "Matched"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("output", "Output Folder"),
            ("message", "Message"),
        ):
            value = QLabel("—")
            value.setWordWrap(True)
            value.setProperty("cssClass", "subtitle")
            self.jobs_detail_values[key] = value
            form.addRow(label + ":", value)
        jobs_detail_layout.addLayout(form)
        jobs_detail_layout.addStretch(1)
        self.jobs_detail_panel.setVisible(False)
        jobs_splitter.addWidget(self.jobs_detail_panel)
        jobs_splitter.setStretchFactor(0, 4)
        jobs_splitter.setStretchFactor(1, 2)

        jobs_layout.addWidget(jobs_splitter, 1)

        self.jobs_status_group.buttonClicked.connect(self._on_jobs_status_filter_changed)
        self.jobs_search_edit.textChanged.connect(self._on_jobs_search_changed)
        self.jobs_show_all_chk.toggled.connect(self._on_jobs_show_all_toggled)
        self.jobs_advanced_chk.toggled.connect(self._on_jobs_advanced_toggled)
        self.jobs_details_toggle.toggled.connect(self._set_jobs_details_visible)
        self._on_jobs_advanced_toggled(False)

        # ----- Tab 3: Templates -----
        templates_tab = QWidget()
        templates_layout = QVBoxLayout(templates_tab)
        templates_layout.setContentsMargins(20, 20, 20, 20)
        self.main_stack.addWidget(templates_tab)

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

        # ----- Tab 4: Help -----
        self.help_page = HelpPage()
        
        # Link action buttons inside Help Page if we add them, 
        # but for now it's just content. 
        # If we wanted to keep the "Start Now" buttons we could add them to HelpPage
        # or wrapping widget here. For now, the clean doc is better.
        
        self.main_stack.addWidget(self.help_page)


        self._refresh_templates()
        self._update_jobs_empty_state()
        self._update_action_buttons()
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

    def _reset_all_modes_and_home(self) -> None:
        self.methane_page.reset_for_new_run()
        self.encroachment_page.reset_for_new_run()
        self.combined_page.reset_for_new_run()
        self.progress.setVisible(False)
        self.progress.setValue(0)
        self._show_home()

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
        idx = sel[0]
        model = self.table.model()
        if isinstance(model, QSortFilterProxyModel):
            idx = model.mapToSource(idx)
        row = idx.row()
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
        if hasattr(self, "jobs_proxy"):
            self.jobs_proxy.invalidate()
        self._update_action_buttons()
        self._update_jobs_empty_state()

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
            self.view_report_btn.setEnabled(False)
            self.open_out_btn.setEnabled(False)
            self.cancel_action.setEnabled(False)
            self.export_manifest_action.setEnabled(False)
            self.rerun_failed_action.setEnabled(False)
            self._update_jobs_detail_panel(None)
            return
        stage = job.state.stage
        can_cancel = stage not in ("DONE", "FAILED", "CANCELLED")
        self.cancel_action.setEnabled(can_cancel)

        has_run_folder = job.run_folder is not None
        manifest = self.controller.export_manifest_path(job)
        self.view_report_btn.setEnabled(has_run_folder)
        self.open_out_btn.setEnabled(has_run_folder)
        self.export_manifest_action.setEnabled(manifest is not None)
        self.rerun_failed_action.setEnabled(manifest is not None)
        self._update_jobs_detail_panel(job)

    def _on_jobs_status_filter_changed(self, _btn: QToolButton) -> None:
        btn = self.jobs_status_group.checkedButton()
        key = self._jobs_filter_keys.get(btn, "all") if btn else "all"
        self.jobs_proxy.set_status_filter(key)
        self._update_jobs_empty_state()
        self._update_action_buttons()

    def _on_jobs_search_changed(self, text: str) -> None:
        self.jobs_proxy.set_search_text(text)
        self._update_jobs_empty_state()
        self._update_action_buttons()

    def _on_jobs_show_all_toggled(self, enabled: bool) -> None:
        self.jobs_proxy.set_show_all_history(enabled)
        self._update_jobs_empty_state()
        self._update_action_buttons()

    def _on_jobs_advanced_toggled(self, enabled: bool) -> None:
        basic_columns = {0, 1, 2, 3, 4, 5}
        for col in range(self.model.columnCount()):
            self.table.setColumnHidden(col, not (enabled or col in basic_columns))
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.resizeColumnsToContents()

    def _set_jobs_details_visible(self, enabled: bool) -> None:
        self.jobs_detail_panel.setVisible(enabled)
        if enabled:
            self._update_jobs_detail_panel(self._selected_job())

    def _update_jobs_empty_state(self) -> None:
        if not self.controller.jobs:
            self.jobs_empty_label.setText("No jobs yet. Start a run from the Run tab.")
            self.jobs_empty_label.setVisible(True)
            return
        if self.jobs_proxy.rowCount() == 0:
            self.jobs_empty_label.setText("No jobs match the current filters.")
            self.jobs_empty_label.setVisible(True)
            return
        self.jobs_empty_label.setVisible(False)

    def _update_jobs_detail_panel(self, job) -> None:
        if not self.jobs_detail_panel.isVisible():
            return
        if job is None:
            self.jobs_detail_status_badge.setText("No selection")
            self.jobs_detail_status_badge.setProperty("status", "idle")
            self.jobs_detail_hint.setVisible(True)
            for value in self.jobs_detail_values.values():
                value.setText("—")
            self._refresh_jobs_badge_style()
            return

        st = job.state
        stage = (st.stage or "").upper()
        stage_text, stage_key = {
            "DONE": ("Completed", "done"),
            "FAILED": ("Failed", "failed"),
            "CANCELLED": ("Cancelled", "cancelled"),
            "QUEUED": ("Queued", "queued"),
            "PENDING": ("Pending", "queued"),
        }.get(stage, (st.stage.title() if st.stage else "Running", "running"))
        self.jobs_detail_status_badge.setText(stage_text)
        self.jobs_detail_status_badge.setProperty("status", stage_key)
        self.jobs_detail_hint.setVisible(False)

        self.jobs_detail_values["name"].setText(job.name)
        self.jobs_detail_values["started"].setText(self._job_started_label(job))
        self.jobs_detail_values["mode"].setText(self._job_mode_label(job))
        self.jobs_detail_values["progress"].setText(f"{max(0, int(st.progress))}%")
        self.jobs_detail_values["inputs"].setText(str(len(job.inputs)))
        self.jobs_detail_values["scanned"].setText(f"{st.scanned_photos} photos / {st.scanned_csvs} CSVs")
        self.jobs_detail_values["matched"].setText(str(st.matched))
        self.jobs_detail_values["success"].setText(str(st.success))
        self.jobs_detail_values["failed"].setText(str(st.failed))
        self.jobs_detail_values["output"].setText(str(job.run_folder or ""))
        self.jobs_detail_values["message"].setText(st.message or "—")
        self._refresh_jobs_badge_style()

    def _refresh_jobs_badge_style(self) -> None:
        self.jobs_detail_status_badge.style().unpolish(self.jobs_detail_status_badge)
        self.jobs_detail_status_badge.style().polish(self.jobs_detail_status_badge)
        self.jobs_detail_status_badge.update()

    def _job_mode_label(self, job) -> str:
        mode = getattr(job.options, "run_mode", None)
        if mode is None:
            return "Custom"
        return {
            "methane": "Methane",
            "encroachment": "Encroachment",
            "combined": "Combined",
        }.get(mode.value, mode.value.title())

    def _job_started_label(self, job) -> str:
        if not job.run_folder:
            return "—"
        name = job.run_folder.name
        prefix = "PurwayGeotagger_"
        if not name.startswith(prefix):
            return "—"
        stamp = name[len(prefix):]
        try:
            dt = datetime.strptime(stamp, "%Y%m%d_%H%M%S")
        except ValueError:
            return "—"
        return dt.strftime("%Y-%m-%d %H:%M:%S")

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
        self.progress.setVisible(True)
        new_job = self.controller.rerun_failed_only(job, self.progress)
        if not new_job:
            self.progress.setVisible(False)
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
        if hasattr(self, "theme_toggle"):
            self.theme_toggle.set_theme(theme)
            self.theme_toggle.refresh_icons()
        
        # Update Logo
        is_dark = (theme or "light").strip().lower() == "dark"
        fname = "ArchAerial_Logo_White_NoWebsite.png" if is_dark else "ArchAerial_Black&Transparent.png"
        logo_path = resource_path(f"assets/aallc_logos/{fname}")
        
        if logo_path.exists():

            pix = QPixmap(str(logo_path))
            # Scale proportionally to fixed height
            if not pix.isNull():
                aspect = pix.width() / pix.height()
                target_h = 90
                target_w = int(target_h * aspect)
                self.logo_label.setFixedWidth(target_w)
                self.logo_label.setPixmap(pix)
        else:
            self.logo_label.clear()


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
