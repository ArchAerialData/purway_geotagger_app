from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QDate, QPoint, Qt, QTimer, QTime, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from purway_geotagger.core.wind_weather_autofill import LocationSuggestion
from purway_geotagger.gui.widgets.mac_stepper import MacStepper


class WindAutofillDialog(QDialog):
    search_requested = Signal(str)
    autofill_requested = Signal()

    def __init__(
        self,
        *,
        start_time_24h: str,
        end_time_24h: str,
        report_date: date | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._time_normalization_active = False
        self._typed_time_text: dict[QTimeEdit, str] = {}
        self.setWindowTitle("Autofill Wind/Temp Data")
        self.setModal(True)
        self.resize(640, 460)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Autofill Wind/Temp Data")
        title.setProperty("cssClass", "h2")
        root.addWidget(title)

        subtitle = QLabel(
            "Search by ZIP or City, State (U.S. only). Select a location, then autofill Start and End wind values."
        )
        subtitle.setProperty("cssClass", "subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        time_card = QGridLayout()
        time_card.setHorizontalSpacing(8)
        time_card.setVerticalSpacing(6)

        times_title = QLabel("Target Times")
        times_title.setProperty("cssClass", "label_strong")
        time_card.addWidget(times_title, 0, 0, 1, 4)

        report_date_label = QLabel("Report Date")
        report_date_label.setProperty("cssClass", "subtitle")
        time_card.addWidget(report_date_label, 1, 0)
        current_qdate = QDate.currentDate()
        jan_first_qdate = QDate(current_qdate.year(), 1, 1)
        requested_qdate = self._to_qdate(report_date) if report_date is not None else current_qdate
        clamped_report_date = self._clamp_qdate(
            requested_qdate,
            min_qdate=jan_first_qdate,
            max_qdate=current_qdate,
        )
        self._min_report_qdate = jan_first_qdate
        self._max_report_qdate = current_qdate
        self.report_date_edit = QDateEdit()
        self.report_date_edit.setCalendarPopup(True)
        self.report_date_edit.setDisplayFormat("yyyy_MM_dd")
        self.report_date_edit.setMinimumDate(jan_first_qdate)
        self.report_date_edit.setMaximumDate(current_qdate)
        self.report_date_edit.setDate(clamped_report_date)
        self.report_date_edit.hide()

        self.report_date_display = QLineEdit()
        self.report_date_display.setReadOnly(True)
        self.report_date_display.setProperty("cssClass", "date_picker_display")
        self.report_date_display.setFixedWidth(130)

        self.report_date_btn = QToolButton()
        self.report_date_btn.setText("Pick Date")
        self.report_date_btn.setProperty("cssClass", "date_picker_btn")
        self.report_date_btn.setCursor(Qt.PointingHandCursor)
        self.report_date_btn.clicked.connect(self._show_report_date_picker)

        date_row = QHBoxLayout()
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.setSpacing(6)
        date_row.addWidget(self.report_date_display)
        date_row.addWidget(self.report_date_btn)
        date_row.addStretch(1)
        date_widget = QWidget()
        date_widget.setLayout(date_row)
        time_card.addWidget(date_widget, 1, 1, 1, 2)

        self._report_date_menu = QMenu(self)
        self._report_date_menu.setProperty("cssClass", "calendar_menu")
        self._report_calendar = QCalendarWidget()
        self._report_calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self._report_calendar.setGridVisible(False)
        self._report_calendar.setNavigationBarVisible(True)
        self._report_calendar.setMinimumDate(self._min_report_qdate)
        self._report_calendar.setMaximumDate(self._max_report_qdate)
        self._report_calendar.clicked.connect(self._on_report_calendar_date_selected)
        self._report_calendar.activated.connect(self._on_report_calendar_date_selected)

        calendar_action = QWidgetAction(self._report_date_menu)
        calendar_action.setDefaultWidget(self._report_calendar)
        self._report_date_menu.addAction(calendar_action)
        self._set_report_date(clamped_report_date)

        start_label = QLabel("Start")
        start_label.setProperty("cssClass", "subtitle")
        time_card.addWidget(start_label, 2, 0)
        self.start_time_edit = self._make_time_edit(start_time_24h)
        self.start_time_field = self._with_stepper(self.start_time_edit)
        time_card.addWidget(self.start_time_field, 2, 1)
        self.start_meridiem_combo = self._make_meridiem_combo(start_time_24h)
        time_card.addWidget(self.start_meridiem_combo, 2, 2)

        end_label = QLabel("End")
        end_label.setProperty("cssClass", "subtitle")
        time_card.addWidget(end_label, 3, 0)
        self.end_time_edit = self._make_time_edit(end_time_24h)
        self.end_time_field = self._with_stepper(self.end_time_edit)
        time_card.addWidget(self.end_time_field, 3, 1)
        self.end_meridiem_combo = self._make_meridiem_combo(end_time_24h)
        time_card.addWidget(self.end_meridiem_combo, 3, 2)
        root.addLayout(time_card)

        self._wire_time_normalization(self.start_time_edit, self.start_meridiem_combo)
        self._wire_time_normalization(self.end_time_edit, self.end_meridiem_combo)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("ZIP or City, State (U.S. only)")
        search_row.addWidget(self.query_edit, 1)

        self.search_btn = QPushButton("Search")
        self.search_btn.setProperty("cssClass", "primary")
        self.search_btn.clicked.connect(self._emit_manual_search)
        search_row.addWidget(self.search_btn)
        root.addLayout(search_row)

        self.result_list = QListWidget()
        self.result_list.setSelectionMode(QListWidget.SingleSelection)
        self.result_list.itemDoubleClicked.connect(lambda _item: self.autofill_requested.emit())
        self.result_list.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(self.result_list, 1)

        self.status_label = QLabel("Type a location to begin search.")
        self.status_label.setProperty("cssClass", "subtitle")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        actions.addWidget(self.cancel_btn)

        self.autofill_btn = QPushButton("Use Selected Location")
        self.autofill_btn.setProperty("cssClass", "run")
        self.autofill_btn.setEnabled(False)
        self.autofill_btn.clicked.connect(self.autofill_requested.emit)
        actions.addWidget(self.autofill_btn)
        root.addLayout(actions)

        self._search_timer = QTimer(self)
        self._search_timer.setInterval(350)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._emit_search_from_timer)
        self.query_edit.textChanged.connect(self._on_query_text_changed)

    def current_query(self) -> str:
        return self.query_edit.text().strip()

    def selected_location(self) -> LocationSuggestion | None:
        item = self.result_list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.UserRole)
        return data if isinstance(data, LocationSuggestion) else None

    def selected_report_date(self) -> date:
        selected = self.report_date_edit.date()
        return date(selected.year(), selected.month(), selected.day())

    def selected_start_time_24h(self) -> str:
        return _to_24h_time_string(
            hour_12=self.start_time_edit.time().hour() % 12 or 12,
            minute=self.start_time_edit.time().minute(),
            meridiem=self.start_meridiem_combo.currentText(),
        )

    def selected_end_time_24h(self) -> str:
        return _to_24h_time_string(
            hour_12=self.end_time_edit.time().hour() % 12 or 12,
            minute=self.end_time_edit.time().minute(),
            meridiem=self.end_meridiem_combo.currentText(),
        )

    def set_suggestions(self, suggestions: list[LocationSuggestion]) -> None:
        had_query_focus = self.query_edit.hasFocus()
        self.result_list.clear()
        for suggestion in suggestions:
            item = QListWidgetItem(suggestion.display_name)
            item.setData(Qt.UserRole, suggestion)
            self.result_list.addItem(item)

        if suggestions:
            self.result_list.setCurrentRow(0)
            self.status_label.setText(f"Found {len(suggestions)} location suggestion(s).")
        else:
            self.status_label.setText("No locations found. Try ZIP or City, State.")
        self._on_selection_changed()
        if had_query_focus:
            self.query_edit.setFocus(Qt.OtherFocusReason)
            self.query_edit.end(False)

    def set_status(self, text: str, *, css_class: str = "subtitle") -> None:
        self.status_label.setProperty("cssClass", css_class)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.update()
        self.status_label.setText(text)

    def set_busy(
        self,
        busy: bool,
        *,
        message: str | None = None,
        allow_typing_when_busy: bool = False,
    ) -> None:
        lock_inputs = busy and not allow_typing_when_busy
        self.query_edit.setEnabled(not lock_inputs)
        self.search_btn.setEnabled(not lock_inputs)
        self.result_list.setEnabled(not lock_inputs)
        self.report_date_edit.setEnabled(not lock_inputs)
        self.report_date_display.setEnabled(not lock_inputs)
        self.report_date_btn.setEnabled(not lock_inputs)
        self.start_time_field.setEnabled(not lock_inputs)
        self.start_meridiem_combo.setEnabled(not lock_inputs)
        self.end_time_field.setEnabled(not lock_inputs)
        self.end_meridiem_combo.setEnabled(not lock_inputs)
        self.cancel_btn.setEnabled(not lock_inputs)
        if busy and allow_typing_when_busy:
            # Avoid submitting autofill against stale in-flight search results.
            self.autofill_btn.setEnabled(False)
        else:
            self.autofill_btn.setEnabled((not lock_inputs) and self.selected_location() is not None)
        if message:
            self.set_status(message, css_class="status_info")

    def _emit_manual_search(self) -> None:
        self._search_timer.stop()
        query = self.current_query()
        if query:
            self.search_requested.emit(query)

    def _emit_search_from_timer(self) -> None:
        query = self.current_query()
        if query:
            self.search_requested.emit(query)

    def _on_query_text_changed(self, _text: str) -> None:
        self._search_timer.start()

    def _on_selection_changed(self) -> None:
        self.autofill_btn.setEnabled(self.selected_location() is not None)

    def _make_time_edit(self, default_24h: str) -> QTimeEdit:
        hour_24, minute = self._parse_24h(default_24h)
        hour_12 = hour_24 % 12 or 12
        edit = QTimeEdit()
        edit.setDisplayFormat("h:mm")
        edit.setTime(datetime(2000, 1, 1, hour=hour_12, minute=minute).time())
        edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        edit.setFixedWidth(84)
        return edit

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

    def _make_meridiem_combo(self, default_24h: str) -> QComboBox:
        hour_24, _minute = self._parse_24h(default_24h)
        combo = QComboBox()
        combo.addItems(["AM", "PM"])
        combo.setCurrentText("PM" if hour_24 >= 12 else "AM")
        combo.setFixedWidth(86)
        return combo

    def _parse_24h(self, value: str) -> tuple[int, int]:
        text = (value or "").strip()
        try:
            parsed = datetime.strptime(text, "%H:%M")
            return parsed.hour, parsed.minute
        except ValueError:
            return 10, 0

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

    def _to_qdate(self, value: date) -> QDate:
        return QDate(value.year, value.month, value.day)

    def _clamp_qdate(self, value: QDate, *, min_qdate: QDate, max_qdate: QDate) -> QDate:
        if value < min_qdate:
            return min_qdate
        if value > max_qdate:
            return max_qdate
        return value

    def _set_report_date(self, value: QDate) -> None:
        clamped = self._clamp_qdate(
            value,
            min_qdate=self._min_report_qdate,
            max_qdate=self._max_report_qdate,
        )
        self.report_date_edit.setDate(clamped)
        self.report_date_display.setText(clamped.toString("yyyy_MM_dd"))
        self._report_calendar.setSelectedDate(clamped)

    def _show_report_date_picker(self) -> None:
        self._report_calendar.setSelectedDate(self.report_date_edit.date())
        popup_pos = self.report_date_btn.mapToGlobal(QPoint(0, self.report_date_btn.height() + 6))
        self._report_date_menu.popup(popup_pos)

    def _on_report_calendar_date_selected(self, value: QDate) -> None:
        self._set_report_date(value)
        self._report_date_menu.hide()


def _to_24h_time_string(*, hour_12: int, minute: int, meridiem: str) -> str:
    if hour_12 < 1 or hour_12 > 12:
        raise ValueError("hour_12 must be in range 1..12")
    if minute < 0 or minute > 59:
        raise ValueError("minute must be in range 0..59")
    marker = (meridiem or "").strip().upper()
    if marker not in {"AM", "PM"}:
        raise ValueError("meridiem must be AM or PM")

    hour_24 = hour_12 % 12
    if marker == "PM":
        hour_24 += 12
    return f"{hour_24:02d}:{minute:02d}"
