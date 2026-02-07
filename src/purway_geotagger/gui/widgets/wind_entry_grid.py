from __future__ import annotations

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


class WindEntryGrid(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

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

    def _time_value(self, time_edit: QTimeEdit, meridiem_combo: QComboBox) -> str:
        raw_time = time_edit.time()
        hour_12 = raw_time.hour() % 12 or 12
        return to_24h_time_string(
            hour_12=hour_12,
            minute=raw_time.minute(),
            meridiem=meridiem_combo.currentText(),
        )

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
