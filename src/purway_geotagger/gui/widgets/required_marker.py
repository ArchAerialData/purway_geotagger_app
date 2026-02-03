from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QLabel


class RequiredMarker(QLabel):
    def __init__(self, text: str = "input required", parent=None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setVisible(False)
        self.setStyleSheet(_style(self.palette()))

    def show_required(self, show: bool = True) -> None:
        self.setVisible(show)


def _style(palette: QPalette) -> str:
    color = "#c62828"
    return f"color: {color}; font-weight: 600;"
