from __future__ import annotations

import math

from PySide6.QtCore import Signal, Qt, QPointF, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor, QPen, QPalette
from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QButtonGroup


class ThemeToggle(QWidget):
    theme_changed = Signal(str)

    def __init__(self, theme: str = "light", parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.sun_btn = QToolButton()
        self.sun_btn.setText("")
        self.sun_btn.setToolTip("Light mode")
        self.moon_btn = QToolButton()
        self.moon_btn.setText("")
        self.moon_btn.setToolTip("Dark mode")

        for btn in (self.sun_btn, self.moon_btn):
            btn.setCheckable(True)
            btn.setAutoRaise(True)
            btn.setProperty("themeToggle", True)
            btn.setIconSize(_ICON_SIZE)
            btn.setMinimumSize(_ICON_SIZE.width() + 18, _ICON_SIZE.height() + 10)

        group = QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(self.sun_btn)
        group.addButton(self.moon_btn)

        layout.addWidget(self.sun_btn)
        layout.addWidget(self.moon_btn)

        self.sun_btn.clicked.connect(lambda: self._emit("light"))
        self.moon_btn.clicked.connect(lambda: self._emit("dark"))

        self.refresh_icons()
        self.set_theme(theme)

    def set_theme(self, theme: str) -> None:
        mode = (theme or "light").strip().lower()
        if mode == "dark":
            self.moon_btn.setChecked(True)
        else:
            self.sun_btn.setChecked(True)
        self.refresh_icons()

    def refresh_icons(self) -> None:
        palette = self.palette()
        fg = palette.color(QPalette.Text)
        bg = palette.color(QPalette.Window)
        self.sun_btn.setIcon(QIcon(_sun_pixmap(fg, bg)))
        self.moon_btn.setIcon(QIcon(_moon_pixmap(fg, bg)))

    def _emit(self, theme: str) -> None:
        self.theme_changed.emit(theme)


_ICON_SIZE = QSize(18, 18)


def _sun_pixmap(fg: QColor, bg: QColor) -> QPixmap:
    size = _ICON_SIZE.width()
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    center = QPointF(size / 2.0, size / 2.0)
    radius = size * 0.28

    painter.setBrush(fg)
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(center, radius, radius)

    pen = QPen(fg)
    pen.setWidthF(1.4)
    painter.setPen(pen)
    ray_in = size * 0.38
    ray_out = size * 0.48
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = center.x() + ray_in * math.cos(rad)
        y1 = center.y() + ray_in * math.sin(rad)
        x2 = center.x() + ray_out * math.cos(rad)
        y2 = center.y() + ray_out * math.sin(rad)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    painter.end()
    return pm


def _moon_pixmap(fg: QColor, bg: QColor) -> QPixmap:
    size = _ICON_SIZE.width()
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    center = QPointF(size / 2.0, size / 2.0)
    radius = size * 0.34

    painter.setBrush(fg)
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(center, radius, radius)

    painter.setBrush(bg)
    offset = QPointF(size * 0.10, 0)
    painter.drawEllipse(center + offset, radius, radius)
    painter.end()
    return pm
