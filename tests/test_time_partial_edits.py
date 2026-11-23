from pathlib import Path
import os, subprocess, sys


def test_partial_time_edits_preserve_marker_in_page_and_autofill():
    root=Path(__file__).resolve().parents[1]
    script=r'''
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTime, Qt
from PySide6.QtTest import QTest
from purway_geotagger.gui.widgets.wind_entry_grid import WindEntryGrid
from purway_geotagger.gui.widgets.wind_autofill_dialog import WindAutofillDialog
app=QApplication([])
widgets=[WindEntryGrid(),WindAutofillDialog(start_time_24h='10:00',end_time_24h='13:00')]
for widget in widgets:
 widget.show()
 for row in ('start','end'):
  edit=getattr(widget,row+'_time_edit'); combo=getattr(widget,row+'_meridiem_combo')
  for canonical,expected in [('13:00','13:15'),('12:00','12:15'),('00:00','00:15'),('01:00','01:15')]:
   edit.setTime(QTime.fromString(canonical,'HH:mm'))
   edit.setSelection(edit.text().index(':')+1,2)
   QTest.keyClicks(edit,'15')
   assert edit.time_24h()==expected,(canonical,edit.time_24h())
  edit.setTime(QTime(13,0)); edit.setSelection(0,1); QTest.keyClicks(edit,'2')
  assert edit.time_24h()=='14:00'
  edit.setSelection(2,2); app.clipboard().setText('45'); edit.paste()
  assert edit.time_24h()=='14:45'
  for text,expected in [('09:30','09:30'),('15:30','15:30'),('1:15','01:15')]:
   edit.setTime(QTime(13,0)); edit.selectAll(); app.clipboard().setText(text); edit.paste()
   assert edit.time_24h()==expected,(text,edit.time_24h())
  edit.setTime(QTime(13,0)); edit.selectAll(); QTest.keyClick(edit,Qt.Key_Backspace); QTest.keyClicks(edit,'09:30')
  assert edit.time_24h()=='09:30'
  edit.setTime(QTime(13,0)); edit.setSelection(2,2); QTest.keyClick(edit,Qt.Key_Delete)
  assert not edit.is_valid(); QTest.keyClicks(edit,'15'); assert edit.time_24h()=='13:15'
  combo.setCurrentText('AM'); assert edit.time_24h()=='01:15'
  edit.selectAll(); QTest.keyClicks(edit,'3:30 PM'); assert edit.time_24h()=='15:30'
 widget.close()
'''
    result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True,timeout=35,
        env=dict(os.environ,PYTHONPATH=str(root/'src'),QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode==0,result.stderr+result.stdout
