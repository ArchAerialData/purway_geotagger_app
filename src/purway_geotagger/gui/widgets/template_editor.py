from __future__ import annotations

import re

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QFormLayout,
    QGroupBox,
)

from purway_geotagger.templates.models import RenameTemplate
from purway_geotagger.templates.template_manager import TemplateManager, render_filename


class TemplateEditorDialog(QDialog):
    templates_changed = Signal()

    def __init__(self, manager: TemplateManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Template Editor")
        self.resize(720, 460)

        self._editing_template_id: str | None = None
        self._current_description: str = ""

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        layout.addLayout(row)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_select)
        row.addWidget(self.list_widget, 1)

        right = QVBoxLayout()
        row.addLayout(right, 2)

        form = QFormLayout()
        self.client_name_edit = QLineEdit()
        self.client_abbr_edit = QLineEdit()
        self.start_index_edit = QLineEdit("0001")
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("Optional, e.g. _{date} or _AREA")

        form.addRow("Client Name", self.client_name_edit)
        form.addRow("Client Abbreviation", self.client_abbr_edit)
        form.addRow("Starting Index", self.start_index_edit)
        form.addRow("Additional fields/suffix (optional)", self.suffix_edit)
        right.addLayout(form)

        tokens_help = QLabel("Tokens for suffix: {date} {time} {ppm} {lat} {lon} {orig}")
        tokens_help.setWordWrap(True)
        right.addWidget(tokens_help)

        preview_box = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_box)
        self.pattern_preview = QLabel()
        self.pattern_preview.setWordWrap(True)
        self.example_preview = QLabel()
        self.example_preview.setWordWrap(True)
        preview_layout.addWidget(QLabel("Pattern"))
        preview_layout.addWidget(self.pattern_preview)
        preview_layout.addWidget(QLabel("Example"))
        preview_layout.addWidget(self.example_preview)
        right.addWidget(preview_box)
        right.addStretch(1)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("New")
        self.save_btn = QPushButton("Save")
        self.delete_btn = QPushButton("Delete")
        self.close_btn = QPushButton("Close")
        btn_row.addWidget(self.new_btn)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        self.new_btn.clicked.connect(self._new_template)
        self.save_btn.clicked.connect(self._save_template)
        self.delete_btn.clicked.connect(self._delete_template)
        self.close_btn.clicked.connect(self.accept)

        self.client_name_edit.textChanged.connect(self._update_preview)
        self.client_abbr_edit.textChanged.connect(self._update_preview)
        self.start_index_edit.textChanged.connect(self._update_preview)
        self.suffix_edit.textChanged.connect(self._update_preview)

        self._refresh_list()
        self._update_preview()

    def _refresh_list(self) -> None:
        self.list_widget.clear()
        for t in self.manager.list_templates():
            label = f"{t.name} ({t.client})"
            self.list_widget.addItem(label)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _current_template(self) -> RenameTemplate | None:
        row = self.list_widget.currentRow()
        templates = self.manager.list_templates()
        if row < 0 or row >= len(templates):
            return None
        return templates[row]

    def _on_select(self, _row: int) -> None:
        t = self._current_template()
        if not t:
            return
        self._editing_template_id = t.id
        self._current_description = t.description
        self.client_name_edit.setText(t.name)
        self.client_abbr_edit.setText(t.client)
        start_text, suffix = _extract_fields_from_pattern(t.pattern, t.start_index)
        self.start_index_edit.setText(start_text)
        self.suffix_edit.setText(suffix)
        self._update_preview()

    def _new_template(self) -> None:
        self.list_widget.clearSelection()
        self._editing_template_id = None
        self._current_description = ""
        self.client_name_edit.clear()
        self.client_abbr_edit.clear()
        self.start_index_edit.setText("0001")
        self.suffix_edit.clear()
        self.client_name_edit.setFocus()
        self._update_preview()

    def _save_template(self) -> None:
        name = self.client_name_edit.text().strip()
        abbr = self.client_abbr_edit.text().strip()
        suffix = self.suffix_edit.text().strip()
        start_index, width = _parse_start_index(self.start_index_edit.text())

        if not name:
            QMessageBox.warning(self, "Validation", "Client Name is required.")
            return
        if not abbr:
            QMessageBox.warning(self, "Validation", "Client Abbreviation is required.")
            return
        if start_index < 1:
            QMessageBox.warning(self, "Validation", "Starting Index must be 1 or greater.")
            return

        tid = self._editing_template_id or _slugify(name)
        if not tid:
            QMessageBox.warning(self, "Validation", "Template ID is required.")
            return

        pattern = _build_pattern(width, suffix)
        tmpl = RenameTemplate(
            id=tid,
            name=name,
            client=abbr,
            pattern=pattern,
            description=self._current_description,
            start_index=start_index,
        )

        try:
            render_filename(
                template=tmpl,
                index=start_index,
                ppm=10.0,
                lat=1.2345,
                lon=2.3456,
                orig="IMG_0001",
            )
        except Exception as e:
            QMessageBox.warning(self, "Pattern error", str(e))
            return

        self.manager.upsert(tmpl)
        self._refresh_list()
        self._select_template_id(tid)
        self.templates_changed.emit()

    def _delete_template(self) -> None:
        t = self._current_template()
        if not t:
            return
        resp = QMessageBox.question(self, "Delete template", f"Delete template '{t.name}'?", QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        self.manager.delete(t.id)
        self._refresh_list()
        self.templates_changed.emit()

    def _select_template_id(self, tid: str) -> None:
        templates = self.manager.list_templates()
        for i, t in enumerate(templates):
            if t.id == tid:
                self.list_widget.setCurrentRow(i)
                return

    def _update_preview(self) -> None:
        suffix = self.suffix_edit.text().strip()
        start_index, width = _parse_start_index(self.start_index_edit.text())
        pattern = _build_pattern(width, suffix)
        self.pattern_preview.setText(pattern)

        name = self.client_name_edit.text().strip() or "Client"
        abbr = self.client_abbr_edit.text().strip() or "CLIENT"
        tmpl = RenameTemplate(
            id="preview",
            name=name,
            client=abbr,
            pattern=pattern,
            description=self._current_description,
            start_index=start_index,
        )
        try:
            example = render_filename(
                template=tmpl,
                index=start_index,
                ppm=12.3,
                lat=1.2345,
                lon=2.3456,
                orig="IMG_0001",
            )
            self.example_preview.setText(f"{example}.jpg")
        except Exception as e:
            self.example_preview.setText(f"Pattern error: {e}")


def _build_pattern(width: int, suffix: str) -> str:
    index_token = "{index}" if width == 1 else f"{{index:0{width}d}}"
    suffix = suffix.strip()
    return f"{{client}}_{index_token}{suffix}"


def _parse_start_index(text: str) -> tuple[int, int]:
    raw = text.strip() or "0001"
    digits = re.sub(r"\D", "", raw) or "1"
    start_index = int(digits)
    width = max(1, len(digits))
    return start_index, width


def _extract_fields_from_pattern(pattern: str, start_index: int) -> tuple[str, str]:
    match = re.match(r"^\{client\}_\{index(?::0?(\d+)d)?\}(.*)$", pattern)
    if not match:
        return str(max(1, start_index)).zfill(4), ""
    width = int(match.group(1) or 1)
    suffix = match.group(2) or ""
    index_value = max(1, start_index)
    start_text = str(index_value).zfill(width) if width > 1 else str(index_value)
    return start_text, suffix


def _slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s
