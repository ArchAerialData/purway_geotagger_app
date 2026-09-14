from pathlib import Path
import os
import subprocess
import sys


def test_gui_provenance_survives_manual_edits_and_docx_export(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo / "src"), "QT_QPA_PLATFORM": "offscreen",
           "PYTHONDONTWRITEBYTECODE": "1"}
    script = '''
import json, sys
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from zoneinfo import ZoneInfo
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.wind_weather_autofill import *
from purway_geotagger.gui.pages.wind_data_page import WindDataPage
app = QApplication([])
page = WindDataPage(AppSettings())
page.client_edit.setText("WeatherTest")
page.system_edit.setText("System1")
page.date_edit.setDate(QDate(2026,7,1))
page.output_dir_edit.setText(sys.argv[1])
page.entry_grid.set_times_from_24h(start_time_24h="13:00", end_time_24h="17:00")
location = LocationSuggestion("Houston","Houston, TX",29.7,-95.3,"America/Chicago")
request = WindAutofillRequest(location,date(2026,7,1),"13:00","17:00")
when = datetime(2026,7,1,18,tzinfo=timezone.utc)
source = WeatherFieldSource("NWS","observed",when,"KHOU","https://api.weather.gov/stations/KHOU/observations",10)
fields = {key:source for key in ("direction","speed_mph","gust_mph","temp_f")}
row = WindAutofillRow("S",10,20,70,when,when.astimezone(ZoneInfo(location.timezone_name)),"KHOU",source.source_url,(),fields)
result = WindAutofillResult(location,row,row,source.source_url,(),request)
page._on_autofill_success(result)
assert page.timezone_edit.text() == "CDT"
assert "4 observed" in page.source_details.summary.text()
assert "10.0 miles" in page.source_details.details.toPlainText()
page.entry_grid.start_speed_spin.setValue(15)
assert "1 manual" in page.source_details.summary.text()
page.date_edit.setDate(QDate(2026,7,2))
assert "context changed" in page.source_details.summary.text()
page.date_edit.setDate(QDate(2026,7,1))
page._generate_docx()
assert page._last_debug_json is not None
payload = json.loads(page._last_debug_json.read_text())
evidence = payload["weather_evidence"]
assert evidence["rows"]["start"]["speed_mph"]["status"] == "manual"
assert evidence["rows"]["start"]["speed_mph"]["value"] == 15
assert evidence["rows"]["start"]["speed_mph"]["source"]["station_id"] == "KHOU"
assert payload["normalized_metadata"]["timezone"] == "CDT"
with ZipFile(page._last_output_docx) as archive:
    root = ET.fromstring(archive.read("customXml/purway_wind_metadata.xml"))
    assert json.loads(root.find("weatherEvidence").text) == evidence
page.close()
print("weather export verified")
'''
    result = subprocess.run([sys.executable,"-B","-c",script,str(tmp_path)],cwd=repo,env=env,
                            capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "weather export verified" in result.stdout
