"""Exercise real Qt wheel, keyboard and mouse events in an isolated application."""

from pathlib import Path
import os
import subprocess
import sys


PRELUDE = """
from PySide6.QtCore import QPoint, QPointF, Qt, QDate, QTime
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import *
from purway_geotagger.gui.input_wheel_guard import install_input_wheel_guard

app = QApplication([])
guard = install_input_wheel_guard(app)
assert install_input_wheel_guard(app) is guard

def wheel(widget, delta=-120, pixel=False):
    position = QPointF(widget.rect().center())
    event = QWheelEvent(position, widget.mapToGlobal(position),
        QPoint(0, delta) if pixel else QPoint(),
        QPoint() if pixel else QPoint(0, delta),
        Qt.NoButton, Qt.NoModifier,
        Qt.ScrollUpdate if pixel else Qt.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)

def value(widget):
    if isinstance(widget, QComboBox):
        return widget.currentIndex(), widget.currentText()
    if isinstance(widget, QAbstractSpinBox):
        return widget.text()
    return widget.value()
"""


def run_ui(script: str) -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-B", "-c", PRELUDE + script],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src"), "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_wheel_never_edits_focused_or_unfocused_inputs_and_preserves_page_scroll():
    run_ui("""
scroll = QScrollArea()
scroll.resize(420, 250)
body = QWidget()
layout = QVBoxLayout(body)
controls = [QSpinBox(), QDoubleSpinBox(), QDateEdit(), QTimeEdit(),
            QDateTimeEdit(), QComboBox(), QComboBox(), QSlider(), QDial()]
controls[0].setValue(50)
controls[1].setValue(25.5)
controls[2].setDate(QDate(2026, 9, 25))
controls[3].setTime(QTime(12, 30))
controls[5].addItems(['AM', 'PM'])
controls[6].addItems(['One', 'Two'])
controls[6].setEditable(True)
for control in controls:
    layout.addWidget(control)
body.setMinimumHeight(1200)
scroll.setWidget(body)
scroll.show()
app.processEvents()
for control in controls:
    for focused in (False, True):
        control.setFocus() if focused else control.clearFocus()
        before = value(control)
        for target in [control] + control.findChildren(QLineEdit):
            for pixel in (False, True):
                for delta in (-120, 120):
                    scroll.verticalScrollBar().setValue(400)
                    wheel(target, delta, pixel)
                    assert value(control) == before, type(control)
                    if not pixel:
                        assert scroll.verticalScrollBar().value() != 400, type(control)
# Wheel over page and scrollbar still scrolls normally.
for target in (scroll.viewport(), scroll.verticalScrollBar()):
    scroll.verticalScrollBar().setValue(400)
    wheel(target)
    assert scroll.verticalScrollBar().value() > 400
# Dropdown popup remains scrollable without changing the selected value.
combo = controls[5]
combo.addItems([str(i) for i in range(100)])
combo.showPopup()
app.processEvents()
before = value(combo)
wheel(combo.view().viewport())
assert combo.view().verticalScrollBar().value() > 0
assert value(combo) == before
combo.hidePopup()
# Calendar wheel cannot change the month/year/date; calendar arrows still work.
calendar = QCalendarWidget()
calendar.setSelectedDate(QDate(2026, 9, 25))
calendar.show()
app.processEvents()
before = calendar.selectedDate(), calendar.monthShown(), calendar.yearShown()
wheel(calendar.findChild(QAbstractItemView).viewport())
assert (calendar.selectedDate(), calendar.monthShown(), calendar.yearShown()) == before
QTest.mouseClick(calendar.findChild(QToolButton, 'qt_calendar_nextmonth'), Qt.LeftButton)
assert calendar.monthShown() == 10
""")


def test_typing_keyboard_and_clicked_arrows_still_edit_values():
    run_ui("""
from purway_geotagger.gui.widgets.mac_stepper import MacStepper
from purway_geotagger.gui.widgets.editable_time import EditableTime
window = QWidget()
layout = QVBoxLayout(window)
spin = QSpinBox()
spin.setRange(0, 5000)
spin.setValue(1000)
layout.addWidget(spin)
stepper = MacStepper()
stepper.step_up.connect(spin.stepUp)
stepper.step_down.connect(spin.stepDown)
layout.addWidget(stepper)
combo = QComboBox()
combo.addItems(['AM', 'PM'])
layout.addWidget(combo)
time = EditableTime('09:30', combo)
layout.addWidget(time)
window.show()
app.processEvents()
spin.setFocus()
spin.selectAll()
QTest.keyClicks(spin, '1500')
QTest.keyClick(spin, Qt.Key_Return)
assert spin.value() == 1500
QTest.keyClick(spin, Qt.Key_Up)
assert spin.value() == 1501
option = QStyleOptionSpinBox()
spin.initStyleOption(option)
up = spin.style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxUp, spin)
QTest.mouseClick(spin, Qt.LeftButton, pos=up.center())
assert spin.value() == 1502
QTest.mouseClick(stepper.up_btn, Qt.LeftButton)
assert spin.value() == 1503
QTest.mouseClick(stepper.down_btn, Qt.LeftButton)
assert spin.value() == 1502
QTest.keyClick(combo, Qt.Key_Down)
assert combo.currentText() == 'PM'
time.setFocus()
time.selectAll()
QTest.keyClick(time, Qt.Key_Backspace)
QTest.keyClicks(time, '15:30')
assert time.time_24h() == '15:30'
wheel(time)
wheel(combo)
assert time.time_24h() == '15:30'
""")


def test_all_actual_modes_and_dialogs_are_protected():
    run_ui("""
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.main_window import MainWindow
from purway_geotagger.gui.pages.wind_data_page import WindDataPage
from purway_geotagger.gui.widgets.settings_dialog import SettingsDialog
from purway_geotagger.gui.widgets.wind_autofill_dialog import WindAutofillDialog
settings = AppSettings()
settings.save = lambda: None
window = MainWindow(settings)
roots = [window.methane_page, window.encroachment_page, window.combined_page,
         WindDataPage(settings), SettingsDialog(settings),
         WindAutofillDialog(start_time_24h='09:30', end_time_24h='15:30')]
for root in roots:
    controls = root.findChildren(QAbstractSpinBox) + root.findChildren(QComboBox)
    assert controls, type(root)
    for control in controls:
        before = value(control)
        for delta in (-120, 120):
            wheel(control, delta)
            assert value(control) == before, (type(root), type(control))
            for child in control.findChildren(QLineEdit):
                wheel(child, delta)
                assert value(control) == before, (type(root), type(control))
""")
