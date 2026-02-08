from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from PySide6.QtCore import QTime, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QTimeEdit,
    QWidget,
)

from purway_geotagger.gui.pages.wind_data_logic import to_24h_time_string
from purway_geotagger.gui.widgets.mac_stepper import MacStepper
from purway_geotagger.core.wind_docx import (
    MAX_GUST_MPH,
    MAX_TEMP_F,
    MAX_WIND_SPEED_MPH,
    MIN_TEMP_F,
    WindRowRaw,
)
from purway_geotagger.core.wind_weather_autofill import WindAutofillRow


@dataclass(frozen=True)
class AutofillApplySummary:
    start_applied_fields: tuple[str, ...]
    end_applied_fields: tuple[str, ...]


class WindEntryGrid(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._time_normalization_active = False
        self._typed_time_text: dict[QTimeEdit, str] = {}

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        headers = ("", "Time", "AM/PM", "Direction", "Speed (mph)", "Gust (mph)", "Temp (F)")
        for col, text in enumerate(headers):
            lbl = QLabel(text)
            lbl.setProperty("cssClass", "label_strong" if col else "subtitle")
            if col:
                lbl.setAlignment(Qt.AlignCenter)
                layout.addWidget(lbl, 0, col, alignment=Qt.AlignHCenter)
            else:
                layout.addWidget(lbl, 0, col)

        self.start_time_edit = self._make_time_edit(QTime(10, 0))
        self.start_time_field = self._with_stepper(self.start_time_edit)
        self.start_meridiem_combo = self._make_meridiem_combo("AM")
        self.start_direction_edit = self._make_direction_edit("SW")
        self.start_speed_spin = self._make_spin_box(0, MAX_WIND_SPEED_MPH)
        self.start_speed_field = self._with_stepper(self.start_speed_spin)
        self.start_gust_spin = self._make_spin_box(0, MAX_GUST_MPH)
        self.start_gust_field = self._with_stepper(self.start_gust_spin)
        self.start_temp_spin = self._make_spin_box(MIN_TEMP_F, MAX_TEMP_F)
        self.start_temp_spin.setValue(50)
        self.start_temp_field = self._with_stepper(self.start_temp_spin)

        self.end_time_edit = self._make_time_edit(QTime(1, 0))
        self.end_time_field = self._with_stepper(self.end_time_edit)
        self.end_meridiem_combo = self._make_meridiem_combo("PM")
        self.end_direction_edit = self._make_direction_edit("SW")
        self.end_speed_spin = self._make_spin_box(0, MAX_WIND_SPEED_MPH)
        self.end_speed_field = self._with_stepper(self.end_speed_spin)
        self.end_gust_spin = self._make_spin_box(0, MAX_GUST_MPH)
        self.end_gust_field = self._with_stepper(self.end_gust_spin)
        self.end_temp_spin = self._make_spin_box(MIN_TEMP_F, MAX_TEMP_F)
        self.end_temp_spin.setValue(50)
        self.end_temp_field = self._with_stepper(self.end_temp_spin)

        self._add_row(
            layout,
            row=1,
            label="Start",
            time_field=self.start_time_field,
            meridiem_combo=self.start_meridiem_combo,
            direction_edit=self.start_direction_edit,
            speed_field=self.start_speed_field,
            gust_field=self.start_gust_field,
            temp_field=self.start_temp_field,
        )
        self._add_row(
            layout,
            row=2,
            label="End",
            time_field=self.end_time_field,
            meridiem_combo=self.end_meridiem_combo,
            direction_edit=self.end_direction_edit,
            speed_field=self.end_speed_field,
            gust_field=self.end_gust_field,
            temp_field=self.end_temp_field,
        )

        self._wire_time_normalization(self.start_time_edit, self.start_meridiem_combo)
        self._wire_time_normalization(self.end_time_edit, self.end_meridiem_combo)

        for widget in (
            self.start_time_edit,
            self.start_meridiem_combo,
            self.start_direction_edit,
            self.start_speed_spin,
            self.start_gust_spin,
            self.start_temp_spin,
            self.end_time_edit,
            self.end_meridiem_combo,
            self.end_direction_edit,
            self.end_speed_spin,
            self.end_gust_spin,
            self.end_temp_spin,
        ):
            self._wire_change_signal(widget)

    def start_row_raw(self) -> WindRowRaw:
        return WindRowRaw(
            time_value=self._time_value(self.start_time_edit, self.start_meridiem_combo),
            wind_direction=self.start_direction_edit.text(),
            wind_speed_mph=self.start_speed_spin.value(),
            gust_mph=self.start_gust_spin.value(),
            temp_f=self.start_temp_spin.value(),
        )

    def end_row_raw(self) -> WindRowRaw:
        return WindRowRaw(
            time_value=self._time_value(self.end_time_edit, self.end_meridiem_combo),
            wind_direction=self.end_direction_edit.text(),
            wind_speed_mph=self.end_speed_spin.value(),
            gust_mph=self.end_gust_spin.value(),
            temp_f=self.end_temp_spin.value(),
        )

    def _wire_change_signal(self, widget: QWidget) -> None:
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(lambda _text: self.changed.emit())
            return
        if isinstance(widget, QSpinBox):
            widget.valueChanged.connect(lambda _value: self.changed.emit())
            return
        if isinstance(widget, QTimeEdit):
            widget.timeChanged.connect(lambda _value: self.changed.emit())
            return
        if isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(lambda _value: self.changed.emit())

    def _wire_time_normalization(self, time_edit: QTimeEdit, meridiem_combo: QComboBox) -> None:
        line = time_edit.lineEdit()
        if line is not None:
            line.textEdited.connect(
                lambda text, edit=time_edit: self._remember_typed_time_text(edit, text)
            )
        time_edit.timeChanged.connect(
            lambda _value: self._normalize_time_overflow(time_edit, meridiem_combo)
        )
        time_edit.editingFinished.connect(
            lambda: self._normalize_typed_time_overflow(time_edit, meridiem_combo)
        )

    def _remember_typed_time_text(self, time_edit: QTimeEdit, text: str) -> None:
        self._typed_time_text[time_edit] = text

    def _normalize_typed_time_overflow(self, time_edit: QTimeEdit, meridiem_combo: QComboBox) -> None:
        typed = self._typed_time_text.pop(time_edit, "").strip()
        if not typed:
            return
        parsed = self._parse_typed_time(typed, default_minute=time_edit.time().minute())
        if parsed is None:
            return
        hour, minute = parsed
        if hour == 0:
            self._apply_time_and_meridiem(
                time_edit, meridiem_combo, normalized_hour=12, minute=minute, meridiem="AM"
            )
            return
        if hour > 12:
            normalized_hour = 12 if hour >= 24 else ((hour - 1) % 12) + 1
            self._apply_time_and_meridiem(
                time_edit, meridiem_combo, normalized_hour=normalized_hour, minute=minute, meridiem="PM"
            )

    def _normalize_time_overflow(self, time_edit: QTimeEdit, meridiem_combo: QComboBox) -> None:
        if self._time_normalization_active:
            return

        raw_time = time_edit.time()
        hour = raw_time.hour()
        minute = raw_time.minute()
        if hour == 0:
            normalized_hour = 12
            normalized_meridiem = "AM"
        elif hour > 12:
            normalized_hour = ((hour - 1) % 12) + 1
            normalized_meridiem = "PM"
        else:
            return
        self._apply_time_and_meridiem(
            time_edit,
            meridiem_combo,
            normalized_hour=normalized_hour,
            minute=minute,
            meridiem=normalized_meridiem,
        )

    def _apply_time_and_meridiem(
        self,
        time_edit: QTimeEdit,
        meridiem_combo: QComboBox,
        *,
        normalized_hour: int,
        minute: int,
        meridiem: str,
    ) -> None:
        self._time_normalization_active = True
        try:
            if meridiem_combo.currentText() != meridiem:
                meridiem_combo.setCurrentText(meridiem)
            time_edit.setTime(QTime(normalized_hour, minute))
        finally:
            self._time_normalization_active = False

    def _parse_typed_time(self, text: str, *, default_minute: int) -> tuple[int, int] | None:
        cleaned = (text or "").strip()
        if not cleaned:
            return None
        parts = cleaned.split(":", maxsplit=1)
        hour_digits = "".join(ch for ch in parts[0] if ch.isdigit())
        if not hour_digits:
            return None
        hour = int(hour_digits)
        minute = default_minute
        if len(parts) == 2:
            minute_digits = "".join(ch for ch in parts[1] if ch.isdigit())
            if minute_digits:
                minute = max(0, min(int(minute_digits[:2]), 59))
        return hour, minute

    def _time_value(self, time_edit: QTimeEdit, meridiem_combo: QComboBox) -> str:
        raw_time = time_edit.time()
        hour_12 = raw_time.hour() % 12 or 12
        return to_24h_time_string(
            hour_12=hour_12,
            minute=raw_time.minute(),
            meridiem=meridiem_combo.currentText(),
        )

    def start_time_24h_text(self) -> str:
        return self._time_value(self.start_time_edit, self.start_meridiem_combo)

    def end_time_24h_text(self) -> str:
        return self._time_value(self.end_time_edit, self.end_meridiem_combo)

    def start_time_display_text(self) -> str:
        return f"{self.start_time_edit.time().toString('h:mm')} {self.start_meridiem_combo.currentText()}"

    def end_time_display_text(self) -> str:
        return f"{self.end_time_edit.time().toString('h:mm')} {self.end_meridiem_combo.currentText()}"

    def set_times_from_24h(self, *, start_time_24h: str, end_time_24h: str) -> None:
        self._set_single_time_from_24h(
            time_edit=self.start_time_edit,
            meridiem_combo=self.start_meridiem_combo,
            value=start_time_24h,
            fallback="10:00",
        )
        self._set_single_time_from_24h(
            time_edit=self.end_time_edit,
            meridiem_combo=self.end_meridiem_combo,
            value=end_time_24h,
            fallback="13:00",
        )
        self.changed.emit()

    def apply_autofill_rows(self, *, start: WindAutofillRow, end: WindAutofillRow) -> AutofillApplySummary:
        start_applied = self._apply_single_row(
            row=start,
            direction_edit=self.start_direction_edit,
            speed_spin=self.start_speed_spin,
            gust_spin=self.start_gust_spin,
            temp_spin=self.start_temp_spin,
        )
        end_applied = self._apply_single_row(
            row=end,
            direction_edit=self.end_direction_edit,
            speed_spin=self.end_speed_spin,
            gust_spin=self.end_gust_spin,
            temp_spin=self.end_temp_spin,
        )
        self.changed.emit()
        return AutofillApplySummary(
            start_applied_fields=tuple(start_applied),
            end_applied_fields=tuple(end_applied),
        )

    def _apply_single_row(
        self,
        *,
        row: WindAutofillRow,
        direction_edit: QLineEdit,
        speed_spin: QSpinBox,
        gust_spin: QSpinBox,
        temp_spin: QSpinBox,
    ) -> list[str]:
        applied_fields: list[str] = []
        if row.direction is not None:
            direction_edit.setText(row.direction)
            applied_fields.append("direction")
        if row.speed_mph is not None:
            speed_spin.setValue(row.speed_mph)
            applied_fields.append("speed")
        if row.gust_mph is not None:
            gust_spin.setValue(row.gust_mph)
            applied_fields.append("gust")
        if row.temp_f is not None:
            temp_spin.setValue(row.temp_f)
            applied_fields.append("temp")
        return applied_fields

    def _set_single_time_from_24h(
        self,
        *,
        time_edit: QTimeEdit,
        meridiem_combo: QComboBox,
        value: str,
        fallback: str,
    ) -> None:
        hour_24, minute = self._parse_24h_time(value, fallback=fallback)
        meridiem = "PM" if hour_24 >= 12 else "AM"
        hour_12 = hour_24 % 12 or 12
        self._apply_time_and_meridiem(
            time_edit,
            meridiem_combo,
            normalized_hour=hour_12,
            minute=minute,
            meridiem=meridiem,
        )

    def _parse_24h_time(self, value: str, *, fallback: str) -> tuple[int, int]:
        text = (value or "").strip()
        try:
            parsed = datetime.strptime(text, "%H:%M")
            return parsed.hour, parsed.minute
        except ValueError:
            parsed_fallback = datetime.strptime(fallback, "%H:%M")
            return parsed_fallback.hour, parsed_fallback.minute

    def _add_row(
        self,
        layout: QGridLayout,
        *,
        row: int,
        label: str,
        time_field: QWidget,
        meridiem_combo: QComboBox,
        direction_edit: QLineEdit,
        speed_field: QWidget,
        gust_field: QWidget,
        temp_field: QWidget,
    ) -> None:
        badge = QLabel(label)
        badge.setProperty("cssClass", "wind_row_badge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        badge.setMinimumWidth(60)

        layout.addWidget(badge, row, 0)
        layout.addWidget(time_field, row, 1, alignment=Qt.AlignHCenter)
        layout.addWidget(meridiem_combo, row, 2, alignment=Qt.AlignHCenter)
        layout.addWidget(direction_edit, row, 3, alignment=Qt.AlignHCenter)
        layout.addWidget(speed_field, row, 4, alignment=Qt.AlignHCenter)
        layout.addWidget(gust_field, row, 5, alignment=Qt.AlignHCenter)
        layout.addWidget(temp_field, row, 6, alignment=Qt.AlignHCenter)

    def _make_time_edit(self, value: QTime) -> QTimeEdit:
        edit = QTimeEdit()
        edit.setDisplayFormat("h:mm")
        edit.setTime(value)
        edit.setCalendarPopup(False)
        edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        edit.setFixedWidth(84)
        return edit

    def _make_meridiem_combo(self, default_value: str) -> QComboBox:
        combo = QComboBox()
        combo.addItems(["AM", "PM"])
        combo.setCurrentText(default_value)
        combo.setFixedWidth(86)
        return combo

    def _make_direction_edit(self, placeholder: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMaxLength(8)
        edit.setFixedWidth(154)
        return edit

    def _make_spin_box(self, min_value: int, max_value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        spin.setFixedWidth(80)
        return spin

    def _with_stepper(self, editor: QAbstractSpinBox) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(editor)

        stepper = MacStepper()
        stepper.step_up.connect(lambda: editor.stepBy(1))
        stepper.step_down.connect(lambda: editor.stepBy(-1))
        layout.addWidget(stepper)
        return container
