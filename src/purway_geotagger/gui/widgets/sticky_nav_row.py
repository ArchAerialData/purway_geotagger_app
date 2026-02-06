from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QSize, Signal, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPalette
from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QSizePolicy


class StickyNavRow(QWidget):
    back_requested = Signal()
    home_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.back_btn = self._build_nav_button("Back")
        self.back_btn.clicked.connect(self.back_requested.emit)

        self.home_btn = self._build_nav_button("Home")
        self.home_btn.clicked.connect(self.home_requested.emit)

        layout.addWidget(self.back_btn)
        layout.addWidget(self.home_btn)

        self._refresh_icons()

    def _build_nav_button(self, text: str) -> QToolButton:
        btn = QToolButton()
        btn.setProperty("cssClass", "sticky_nav")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setText(text)
        btn.setIconSize(_ICON_SIZE)
        btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        return btn

    def _refresh_icons(self) -> None:
        fg = self.palette().color(QPalette.Text)
        self.back_btn.setIcon(QIcon(_back_icon_pixmap(fg)))
        self.home_btn.setIcon(QIcon(_home_icon_pixmap(fg)))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange, QEvent.StyleChange):
            self._refresh_icons()


_ICON_SIZE = QSize(14, 14)


def _base_pixmap() -> QPixmap:
    pm = QPixmap(_ICON_SIZE)
    pm.fill(Qt.transparent)
    return pm


def _back_icon_pixmap(color: QColor) -> QPixmap:
    pm = _base_pixmap()
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(color)
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(QPointF(11.5, 7.0), QPointF(3.5, 7.0))
    painter.drawLine(QPointF(6.8, 3.5), QPointF(3.5, 7.0))
    painter.drawLine(QPointF(6.8, 10.5), QPointF(3.5, 7.0))
    painter.end()
    return pm


def _home_icon_pixmap(color: QColor) -> QPixmap:
    pm = _base_pixmap()
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(color)
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawLine(QPointF(2.5, 7.0), QPointF(7.0, 2.7))
    painter.drawLine(QPointF(7.0, 2.7), QPointF(11.5, 7.0))
    painter.drawLine(QPointF(3.5, 6.7), QPointF(3.5, 11.2))
    painter.drawLine(QPointF(10.5, 6.7), QPointF(10.5, 11.2))
    painter.drawLine(QPointF(3.5, 11.2), QPointF(10.5, 11.2))
    painter.drawLine(QPointF(6.2, 11.2), QPointF(6.2, 8.8))
    painter.drawLine(QPointF(7.8, 11.2), QPointF(7.8, 8.8))
    painter.drawLine(QPointF(6.2, 8.8), QPointF(7.8, 8.8))
    painter.end()
    return pm
