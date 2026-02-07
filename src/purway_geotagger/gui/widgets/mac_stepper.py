from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget


class MacStepper(QWidget):
    step_up = Signal()
    step_down = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("cssClass", "wind_stepper")
        self.setFixedWidth(18)
        self.setFixedHeight(30)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.up_btn = self._make_button("\u25B4", "up")
        self.up_btn.clicked.connect(self.step_up.emit)
        layout.addWidget(self.up_btn)

        self.down_btn = self._make_button("\u25BE", "down")
        self.down_btn.clicked.connect(self.step_down.emit)
        layout.addWidget(self.down_btn)

    def _make_button(self, text: str, pos: str) -> QToolButton:
        btn = QToolButton()
        btn.setProperty("cssClass", "wind_stepper_btn")
        btn.setProperty("stepPos", pos)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setAutoRepeat(True)
        btn.setAutoRepeatDelay(260)
        btn.setAutoRepeatInterval(55)
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        return btn
