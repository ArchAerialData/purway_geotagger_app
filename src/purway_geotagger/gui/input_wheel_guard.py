"""Keep page scrolling from silently editing form values throughout the app."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QCalendarWidget,
    QComboBox,
    QScrollBar,
    QWidget,
)


def _value_control(widget: QWidget) -> QWidget | None:
    """Include editors' children, but do not cross into a popup's owner."""
    current = widget
    while current is not None:
        if isinstance(current, (QAbstractSpinBox, QComboBox, QCalendarWidget)):
            return current
        if isinstance(current, QAbstractSlider) and not isinstance(current, QScrollBar):
            return current
        if current.isWindow():
            break
        current = current.parentWidget()
    return None


class InputWheelGuard(QObject):
    """Block only wheel edits, irrespective of focus; preserve normal scrolling."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.Wheel or not isinstance(watched, QWidget):
            return False
        control = _value_control(watched)
        if control is None:
            return False

        # Forward to the containing page, including trackpad pixel deltas. Merely
        # swallowing the wheel would create dead spots in scrollable forms.
        parent = control.parentWidget() if not control.isWindow() else None
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea):
                viewport = parent.viewport()
                forwarded = QWheelEvent(
                    viewport.mapFromGlobal(event.globalPosition()),
                    event.globalPosition(),
                    event.pixelDelta(),
                    event.angleDelta(),
                    event.buttons(),
                    event.modifiers(),
                    event.phase(),
                    event.inverted(),
                    event.source(),
                    event.pointingDevice(),
                )
                QApplication.sendEvent(viewport, forwarded)
                if forwarded.isAccepted():
                    break
            if parent.isWindow():
                break
            parent = parent.parentWidget()

        # Consume the original even at scroll boundaries so it cannot reach a
        # value editor or scroll the page a second time through native bubbling.
        event.accept()
        return True


def install_input_wheel_guard(app: QApplication) -> InputWheelGuard:
    """Install once before creating windows; also covers dynamically opened dialogs."""
    guard = getattr(app, "_input_wheel_guard", None)
    if guard is None:
        guard = InputWheelGuard(app)
        app.installEventFilter(guard)
        app._input_wheel_guard = guard
    return guard
