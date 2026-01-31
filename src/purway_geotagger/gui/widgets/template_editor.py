from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QLabel,
    QMessageBox,
)

from purway_geotagger.templates.models import RenameTemplate
from purway_geotagger.templates.template_manager import TemplateManager, render_filename


class TemplateEditorDialog(QDialog):
    def __init__(self, manager: TemplateManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Template Editor")
        self.resize(640, 420)

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        layout.addLayout(row)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_select)
        row.addWidget(self.list_widget, 1)

        right = QVBoxLayout()
        row.addLayout(right, 2)

        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.client_edit = QLineEdit()
        self.pattern_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(80)

        right.addWidget(QLabel("ID"))
        right.addWidget(self.id_edit)
        right.addWidget(QLabel("Name"))
        right.addWidget(self.name_edit)
        right.addWidget(QLabel("Client"))
        right.addWidget(self.client_edit)
        right.addWidget(QLabel("Pattern"))
        right.addWidget(self.pattern_edit)
        right.addWidget(QLabel("Description"))
        right.addWidget(self.desc_edit)

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

        self._refresh_list()

    def _refresh_list(self) -> None:
        self.list_widget.clear()
        for t in self.manager.list_templates():
            self.list_widget.addItem(f"{t.name} ({t.id})")
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
        self.id_edit.setText(t.id)
        self.name_edit.setText(t.name)
        self.client_edit.setText(t.client)
        self.pattern_edit.setText(t.pattern)
        self.desc_edit.setPlainText(t.description)

    def _new_template(self) -> None:
        self.list_widget.clearSelection()
        self.id_edit.clear()
        self.name_edit.clear()
        self.client_edit.clear()
        self.pattern_edit.clear()
        self.desc_edit.clear()
        self.name_edit.setFocus()

    def _save_template(self) -> None:
        tid = self.id_edit.text().strip()
        name = self.name_edit.text().strip()
        client = self.client_edit.text().strip()
        pattern = self.pattern_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Validation", "Template name is required.")
            return
        if not tid:
            tid = _slugify(name)
        if not tid:
            QMessageBox.warning(self, "Validation", "Template ID is required.")
            return
        if not pattern:
            QMessageBox.warning(self, "Validation", "Template pattern is required.")
            return

        tmpl = RenameTemplate(
            id=tid,
            name=name,
            client=client or "CLIENT",
            pattern=pattern,
            description=desc,
        )

        try:
            render_filename(
                template=tmpl,
                index=1,
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

    def _delete_template(self) -> None:
        t = self._current_template()
        if not t:
            return
        resp = QMessageBox.question(self, "Delete template", f"Delete template '{t.name}'?", QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        self.manager.delete(t.id)
        self._refresh_list()

    def _select_template_id(self, tid: str) -> None:
        templates = self.manager.list_templates()
        for i, t in enumerate(templates):
            if t.id == tid:
                self.list_widget.setCurrentRow(i)
                return


def _slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s
