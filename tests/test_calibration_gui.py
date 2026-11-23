from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_calibration_controls_state_options_and_reset_in_both_themes(tmp_path):
    root=Path(__file__).resolve().parents[1]
    script=r'''
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.gui.main_window import MainWindow
from purway_geotagger.gui.widgets.run_report_view import format_run_summary
app=QApplication([])
settings=AppSettings()
settings.save=lambda:None
window=MainWindow(settings)
for theme in ('light','dark'):
    window._on_theme_changed(theme)
    for page in (window.methane_page,window.combined_page):
        page.reset_for_new_run()
        assert page.calibration_chk.isChecked() and page.state.methane_exclude_calibration
        page.calibration_chk.click()
        assert not page.state.methane_exclude_calibration
        page.state.inputs=[Path(sys.argv[1])]
        page.state.methane_log_base=Path(sys.argv[1])
        page.state.encroachment_output_base=Path(sys.argv[1])
        options=window.controller.build_job_options_from_mode_state(page.state)
        assert not options.methane_exclude_calibration
        page.refresh_summary()
        assert not page.calibration_chk.isChecked()
        page.reset_for_new_run()
        assert page.calibration_chk.isChecked() and page.state.methane_exclude_calibration
        app.processEvents()
summary=format_run_summary({'run_mode':'methane','settings':{'methane_threshold':1000,'methane_exclude_calibration':True},
'methane_outputs':[{'source_csv':'flight.xlsx','cleaned_status':'success','sheets':[{'header_row':3,'source_sheet':'Flight <A>',
'calibration_excluded':2,'pac_preserved':1,'pac_calculated':3,'pac_unavailable':1}],'warnings':['Altitude < 0']}]})
assert 'calibration 2' in summary and 'preserved 1' in summary and 'calculated 3' in summary
assert 'Flight &lt;A&gt;' in summary and 'Altitude &lt; 0' in summary
assert 'Mode' in format_run_summary({'run_mode':'methane','methane_outputs':[{'source_csv':'old.csv'}]})
window.close()
'''
    env=dict(os.environ,PYTHONPATH=str(root/'src'),QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path)],env=env,capture_output=True,text=True,timeout=40)
    assert result.returncode==0, result.stdout+result.stderr
    assert 'Traceback' not in result.stderr, result.stderr
