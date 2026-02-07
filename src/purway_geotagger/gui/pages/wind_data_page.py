from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.wind_docx import (
    WindInputValidationError,
    WindReportMetadataRaw,
    build_wind_template_payload,
)
from purway_geotagger.core.wind_docx_writer import WindDocxWriterError, generate_wind_docx_report
from purway_geotagger.gui.pages.wind_data_logic import (
    build_live_preview_payload,
    compute_generate_availability,
    resolve_default_wind_template_path,
)
from purway_geotagger.gui.widgets.wind_entry_grid import WindEntryGrid
from purway_geotagger.util.platform import open_in_finder


class WindDataPage(QWidget):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._template_path = resolve_default_wind_template_path()
        self._last_output_docx: Path | None = None
        self._last_debug_json: Path | None = None
        self._last_validation_error: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(28, 24, 28, 24)
        self.content_layout.setSpacing(18)
        scroll.setWidget(content)
        root.addWidget(scroll)

        title = QLabel("Wind Data DOCX")
        title.setProperty("cssClass", "h1")
        self.content_layout.addWidget(title)

        subtitle = QLabel(
            "Enter Start/End wind observations, preview the final strings, then generate a DOCX from the production template."
        )
        subtitle.setProperty("cssClass", "subtitle")
        subtitle.setWordWrap(True)
        self.content_layout.addWidget(subtitle)

        self.content_layout.addWidget(self._build_report_info_card())
        self.content_layout.addWidget(self._build_inputs_card())
        self.content_layout.addWidget(self._build_preview_card())
        self.content_layout.addWidget(self._build_template_save_card())
        self.content_layout.addLayout(self._build_actions_row())

        self.validation_label = QLabel("")
        self.validation_label.setProperty("cssClass", "error")
        self.validation_label.setWordWrap(True)
        self.validation_label.setVisible(False)
        self.content_layout.addWidget(self.validation_label)

        self.status_label = QLabel("")
        self.status_label.setProperty("cssClass", "subtitle")
        self.status_label.setWordWrap(True)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addStretch(1)

        self._wire_signals()
        self.template_edit.setText(str(self._template_path))

        last_dir = (self.settings.last_output_dir or "").strip()
        if last_dir:
            self.output_dir_edit.setText(last_dir)

        self._refresh_preview()

    def _build_report_info_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("cssClass", "card")
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        title = QLabel("1) Report Info")
        title.setProperty("cssClass", "h2")
        layout.addWidget(title, 0, 0, 1, 4)

        client_lbl = QLabel("Client Name")
        client_lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(client_lbl, 1, 0)
        self.client_edit = QLineEdit()
        self.client_edit.setPlaceholderText("TargaResources")
        layout.addWidget(self.client_edit, 1, 1)

        system_lbl = QLabel("System Name")
        system_lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(system_lbl, 1, 2)
        self.system_edit = QLineEdit()
        self.system_edit.setPlaceholderText("KDB 20-IN")
        layout.addWidget(self.system_edit, 1, 3)

        date_lbl = QLabel("Date")
        date_lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(date_lbl, 2, 0)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy_MM_dd")
        self.date_edit.setDate(QDate.currentDate())
        layout.addWidget(self.date_edit, 2, 1)

        tz_lbl = QLabel("Time Zone")
        tz_lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(tz_lbl, 2, 2)
        self.timezone_edit = QLineEdit("CST")
        self.timezone_edit.setPlaceholderText("CST")
        layout.addWidget(self.timezone_edit, 2, 3)
        return card

    def _build_inputs_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("cssClass", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("2) Wind Inputs")
        title.setProperty("cssClass", "h2")
        layout.addWidget(title)

        note = QLabel(
            "Wind Direction is direct text. Speed/Gust/Temp are integer-only inputs."
        )
        note.setProperty("cssClass", "subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.entry_grid = WindEntryGrid()
        layout.addWidget(self.entry_grid)
        return card

    def _build_preview_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("cssClass", "card")
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        title = QLabel("3) Output Preview")
        title.setProperty("cssClass", "h2")
        layout.addWidget(title, 0, 0, 1, 3)

        time_heading = QLabel("Time")
        time_heading.setProperty("cssClass", "wind_preview_heading")
        layout.addWidget(time_heading, 1, 1)
        summary_heading = QLabel("Wind Summary")
        summary_heading.setProperty("cssClass", "wind_preview_heading")
        layout.addWidget(summary_heading, 1, 2)

        (
            start_row,
            self.start_time_preview,
            self.start_string_preview,
        ) = self._build_preview_row("Start")
        layout.addWidget(start_row, 2, 0, 1, 3)

        (
            end_row,
            self.end_time_preview,
            self.end_string_preview,
        ) = self._build_preview_row("End")
        layout.addWidget(end_row, 3, 0, 1, 3)
        return card

    def _build_preview_row(self, label_text: str) -> tuple[QFrame, QLabel, QLabel]:
        row = QFrame()
        row.setProperty("cssClass", "wind_preview_row")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 8, 12, 8)
        row_layout.setSpacing(14)

        label = QLabel(label_text)
        label.setProperty("cssClass", "wind_preview_title")
        label.setFixedWidth(54)

        time_value = QLabel("\u2014")
        time_value.setProperty("cssClass", "wind_preview_time")
        time_value.setFixedWidth(120)

        summary_value = QLabel("\u2014")
        summary_value.setProperty("cssClass", "wind_preview_string")
        summary_value.setWordWrap(True)

        row_layout.addWidget(label)
        row_layout.addWidget(time_value)
        row_layout.addWidget(summary_value, 1)
        return row, time_value, summary_value

    def _build_template_save_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("cssClass", "card")
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        title = QLabel("4) Template + Save")
        title.setProperty("cssClass", "h2")
        layout.addWidget(title, 0, 0, 1, 3)

        template_lbl = QLabel("Template")
        template_lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(template_lbl, 1, 0)
        self.template_edit = QLineEdit()
        self.template_edit.setReadOnly(True)
        layout.addWidget(self.template_edit, 1, 1)
        self.template_btn = QPushButton("Select Template…")
        self.template_btn.setProperty("cssClass", "primary")
        self.template_btn.clicked.connect(self._select_template)
        layout.addWidget(self.template_btn, 1, 2)

        output_lbl = QLabel("Output Folder")
        output_lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(output_lbl, 2, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.textChanged.connect(self._refresh_preview)
        layout.addWidget(self.output_dir_edit, 2, 1)
        self.output_btn = QPushButton("Select Output Folder…")
        self.output_btn.setProperty("cssClass", "primary")
        self.output_btn.clicked.connect(self._select_output_folder)
        layout.addWidget(self.output_btn, 2, 2)

        filename_lbl = QLabel("Output Filename")
        filename_lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(filename_lbl, 3, 0)
        self.filename_edit = QLineEdit()
        self.filename_edit.setReadOnly(True)
        layout.addWidget(self.filename_edit, 3, 1, 1, 2)
        return card

    def _build_actions_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.open_folder_btn = QPushButton("Open Output Folder")
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        layout.addWidget(self.open_folder_btn)

        self.open_docx_btn = QPushButton("Open Generated DOCX")
        self.open_docx_btn.setEnabled(False)
        self.open_docx_btn.clicked.connect(self._open_generated_docx)
        layout.addWidget(self.open_docx_btn)

        self.open_debug_btn = QPushButton("Open Debug JSON")
        self.open_debug_btn.setEnabled(False)
        self.open_debug_btn.clicked.connect(self._open_generated_debug)
        layout.addWidget(self.open_debug_btn)

        layout.addStretch(1)

        self.generate_btn = QPushButton("Generate Wind DOCX")
        self.generate_btn.setProperty("cssClass", "run")
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.clicked.connect(self._generate_docx)
        layout.addWidget(self.generate_btn)
        return layout

    def _wire_signals(self) -> None:
        self.client_edit.textChanged.connect(self._refresh_preview)
        self.system_edit.textChanged.connect(self._refresh_preview)
        self.date_edit.dateChanged.connect(self._refresh_preview)
        self.timezone_edit.textChanged.connect(self._refresh_preview)
        self.entry_grid.changed.connect(self._refresh_preview)

    def _build_metadata(self) -> WindReportMetadataRaw:
        return WindReportMetadataRaw(
            client_name=self.client_edit.text(),
            system_name=self.system_edit.text(),
            report_date=self.date_edit.date().toString("yyyy_MM_dd"),
            timezone=self.timezone_edit.text(),
        )

    def _refresh_preview(self) -> None:
        start_raw = self.entry_grid.start_row_raw()
        end_raw = self.entry_grid.end_row_raw()

        preview_payload = None
        try:
            preview_payload = build_live_preview_payload(start_raw, end_raw)
        except WindInputValidationError:
            preview_payload = None

        report = None
        validation_error = None
        try:
            report = build_wind_template_payload(
                self._build_metadata(),
                start_raw,
                end_raw,
            )
        except WindInputValidationError as exc:
            validation_error = str(exc)

        self._last_validation_error = validation_error
        if preview_payload is not None:
            self.start_time_preview.setText(preview_payload.s_time)
            self.start_string_preview.setText(preview_payload.s_string)
            self.end_time_preview.setText(preview_payload.e_time)
            self.end_string_preview.setText(preview_payload.e_string)
        else:
            self.start_time_preview.setText("\u2014")
            self.start_string_preview.setText("\u2014")
            self.end_time_preview.setText("\u2014")
            self.end_string_preview.setText("\u2014")

        if report is not None:
            self.filename_edit.setText(report.payload.output_filename())
        else:
            self.filename_edit.clear()

        self.validation_label.setVisible(bool(validation_error))
        self.validation_label.setText(validation_error or "")
        if validation_error:
            self._set_status("", css_class="subtitle")

        enabled, reason = compute_generate_availability(
            template_path=self._template_path,
            output_dir_text=self.output_dir_edit.text(),
            validation_error=validation_error,
        )
        self.generate_btn.setEnabled(enabled)
        self.open_folder_btn.setEnabled(bool(self.output_dir_edit.text().strip()))

        if reason and not validation_error:
            self._set_status(reason, css_class="subtitle")
        elif not reason and not self.status_label.text():
            self._set_status("", css_class="subtitle")

    def _select_template(self) -> None:
        start = str(self._template_path.parent if self._template_path else Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Wind DOCX Template",
            start,
            "Word Documents (*.docx)",
        )
        if path:
            self._template_path = Path(path)
            self.template_edit.setText(path)
            self._refresh_preview()

    def _select_output_folder(self) -> None:
        base = self.output_dir_edit.text().strip() or self.settings.last_output_dir or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Select Wind DOCX Output Folder", base)
        if chosen:
            self.output_dir_edit.setText(chosen)
            self.settings.last_output_dir = chosen
            self.settings.save()
            self._refresh_preview()

    def _generate_docx(self) -> None:
        try:
            report = build_wind_template_payload(
                self._build_metadata(),
                self.entry_grid.start_row_raw(),
                self.entry_grid.end_row_raw(),
            )
        except WindInputValidationError as exc:
            QMessageBox.warning(self, "Wind Data validation", str(exc))
            self._set_status(str(exc), css_class="status_error")
            return

        output_dir = Path(self.output_dir_edit.text().strip())
        try:
            render = generate_wind_docx_report(
                template_path=self._template_path,
                output_dir=output_dir,
                report=report,
            )
        except WindDocxWriterError as exc:
            QMessageBox.warning(self, "Wind DOCX generation failed", str(exc))
            self._set_status(str(exc), css_class="status_error")
            return

        self._last_output_docx = render.output_docx_path
        self._last_debug_json = render.debug_json_path
        self.open_docx_btn.setEnabled(True)
        self.open_debug_btn.setEnabled(True)

        self._set_status(
            f"Generated {render.output_docx_path.name} and {render.debug_json_path.name}.",
            css_class="status_success",
        )
        self._refresh_preview()

    def _open_output_folder(self) -> None:
        path_text = self.output_dir_edit.text().strip()
        if not path_text:
            return
        open_in_finder(Path(path_text))

    def _open_generated_docx(self) -> None:
        if self._last_output_docx:
            open_in_finder(self._last_output_docx)

    def _open_generated_debug(self) -> None:
        if self._last_debug_json:
            open_in_finder(self._last_debug_json)

    def _set_status(self, text: str, *, css_class: str) -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("cssClass", css_class)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.update()
