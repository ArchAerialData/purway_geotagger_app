from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QStyle


class StickyNavRow(QWidget):
    back_requested = Signal()
    home_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.back_btn = QToolButton()
        self.back_btn.setProperty("cssClass", "sticky_nav")
        self.back_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.back_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.back_btn.setText("Previous Page")
        self.back_btn.clicked.connect(self.back_requested.emit)

        self.home_btn = QToolButton()
        self.home_btn.setProperty("cssClass", "sticky_nav")
        self.home_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.home_btn.setIcon(self.style().standardIcon(QStyle.SP_DirHomeIcon))
        self.home_btn.setText("Home")
        self.home_btn.clicked.connect(self.home_requested.emit)

        layout.addWidget(self.back_btn)
        layout.addWidget(self.home_btn)
