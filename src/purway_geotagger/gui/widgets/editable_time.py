"""A clearable time entry that formats completed input without spin-box constraints."""
from __future__ import annotations

import re

from PySide6.QtCore import QSignalBlocker, QTime, Qt, Signal
from PySide6.QtWidgets import QComboBox, QLineEdit


def parse_time_entry(text: str) -> QTime | None:
    """Bare entries are 24-hour time; an explicit AM/PM suffix is 12-hour time."""
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*(AM|PM)?\s*", text, re.IGNORECASE)
    if not match:
        match = re.fullmatch(r"\s*(\d{2})(\d{2})\s*(AM|PM)?\s*", text, re.IGNORECASE)
    if not match:
        return None
    hour, minute = int(match[1]), int(match[2])
    marker = (match[3] or "").upper()
    if minute > 59 or (marker and not 1 <= hour <= 12) or (not marker and hour > 23):
        return None
    if marker:
        hour = hour % 12 + (12 if marker == "PM" else 0)
    return QTime(hour, minute)


class EditableTime(QLineEdit):
    validityChanged = Signal(bool)
    valueChanged = Signal()

    def __init__(self, default_24h: str, meridiem: QComboBox, parent=None) -> None:
        super().__init__(parent)
        self._meridiem = meridiem
        self._formatted_text: str | None = None
        self._formatting = False
        self.setPlaceholderText("HH:MM")
        self.setAccessibleName("Time (12 or 24 hour input)")
        self.setMinimumWidth(120)
        self.setClearButtonEnabled(True)
        self.setToolTip("Select all and replace the time. Examples: 09:30, 15:30, 1530, or 3:30 PM.")
        self.textChanged.connect(self._text_changed)
        self.textEdited.connect(self._format_complete_entry)
        self.editingFinished.connect(self.commit)
        self.setTime(QTime.fromString(default_24h, "HH:mm"))

    def _text_changed(self, _text: str) -> None:
        if self._formatting:
            return
        if self.text() != self._formatted_text:
            self._formatted_text = None
        self.validityChanged.emit(self.is_valid())
        self.valueChanged.emit()

    def _format_complete_entry(self, _text: str) -> None:
        self.commit()

    def is_valid(self) -> bool:
        return self._formatted_text == self.text() or parse_time_entry(self.text()) is not None

    def commit(self) -> bool:
        if self._formatted_text == self.text():
            return True
        parsed = parse_time_entry(self.text())
        if parsed is None:
            return False  # Never restore an old value or silently clamp invalid input.
        self.setTime(parsed)
        return True

    def setTime(self, value: QTime) -> None:
        if not value.isValid():
            self.clear()
            return
        self._formatting = True
        try:
            # Publish the new time and marker together, so live report previews
            # never observe an old time paired with a newly selected AM/PM.
            with QSignalBlocker(self._meridiem):
                self._meridiem.setCurrentText("PM" if value.hour() >= 12 else "AM")
            self._formatted_text = f"{value.hour() % 12 or 12}:{value.minute():02d}"
            self.setText(self._formatted_text)
        finally:
            self._formatting = False
        self.validityChanged.emit(True)
        self.valueChanged.emit()

    def time_24h(self) -> str:
        # Reading live previews must not rewrite a field or move its cursor.
        if self._formatted_text != self.text():
            parsed = parse_time_entry(self.text())
            if parsed is not None:
                return parsed.toString("HH:mm")
            raise ValueError("Enter a complete time, such as 09:30 or 15:30.")
        hour, minute = map(int, self.text().split(":"))
        hour = hour % 12 + (12 if self._meridiem.currentText() == "PM" else 0)
        return f"{hour:02d}:{minute:02d}"

    def time(self) -> QTime:
        """Current displayed 12-hour clock value (AM/PM lives in the adjacent combo)."""
        if not self.commit():
            return QTime()
        return QTime.fromString(self.text(), "h:mm")

    def stepBy(self, steps: int) -> None:
        if not self.commit():
            return
        position = self.cursorPosition()
        seconds = 60 if position > self.text().index(":") else 3600
        self.setTime(QTime.fromString(self.time_24h(), "HH:mm").addSecs(steps * seconds))
        self.setCursorPosition(position)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.commit()
            event.accept()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.stepBy(1 if event.key() == Qt.Key_Up else -1)
            event.accept()
        else:
            super().keyPressEvent(event)
