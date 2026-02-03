from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox, QPushButton

from purway_geotagger.util.platform import open_in_finder


class LogViewerDialog(QDialog):
    def __init__(self, log_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.log_path = log_path
        self.setWindowTitle("Run Log")
        self.resize(700, 500)

        layout = QVBoxLayout(self)
        path_label = QLabel(str(log_path))
        layout.addWidget(path_label)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText(_read_log(log_path))
        layout.addWidget(self.text, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        open_btn = QPushButton("Open in Finder")
        open_btn.clicked.connect(self._open_in_finder)
        buttons.addButton(open_btn, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _open_in_finder(self) -> None:
        open_in_finder(self.log_path)


def _read_log(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Unable to read log: {exc}"
