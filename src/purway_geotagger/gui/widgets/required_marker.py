from __future__ import annotations

from PySide6.QtWidgets import QLabel


class RequiredMarker(QLabel):
    def __init__(self, text: str = "input required", parent=None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setVisible(False)
        self.setProperty("cssClass", "error")

    def show_required(self, show: bool = True) -> None:
        self.setVisible(show)
