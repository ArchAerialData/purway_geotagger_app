import pytest
import csv
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
from purway_geotagger.exif.exiftool_writer import ExifToolWriter
from purway_geotagger.core.photo_task import PhotoTask

@pytest.fixture
def writer():
    return ExifToolWriter(write_xmp=True, dry_run=False)

@patch("subprocess.run")
def test_write_tasks_uses_config(mock_run, writer, tmp_path):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    
    photo = tmp_path / "test.jpg"
    photo.write_bytes(b"fake jpeg")
    
    task = PhotoTask(src_path=photo, work_path=photo, output_path=photo)
    task.matched = True
    task.lat = 30.0
    task.lon = -90.0
    task.ppm = 500.5
    task.relative_altitude = 25.0
    task.pac = 20.02
    
    # We don't care about verification for this test
    with patch.object(writer, "_verify_written", return_value={photo: MagicMock(success=True)}):
        writer.write_tasks([task], tmp_path, progress_cb=lambda d, t: None, cancel_cb=lambda: False)
    
    # Verify subprocess.run was called with -config
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert "-config" in cmd
    # Just check that some element contains the config filename
    assert any("exiftool_config.txt" in c for c in cmd)
    assert any(c.startswith("-csv=") for c in cmd)

def test_write_import_csv_extended_fields(writer, tmp_path):
    csv_path = tmp_path / "import.csv"
    photo = tmp_path / "test.jpg"
    
    task = PhotoTask(src_path=photo, work_path=photo, output_path=photo)
    task.lat = 30.0
    task.lon = -90.0
    task.ppm = 1234.5
    task.pac = 49.38
    task.relative_altitude = 25.0
    task.uav_yaw = 180.5
    task.timestamp_raw = "2023-01-01 12:00:00"
    
    writer._write_import_csv(csv_path, [task])
    
    with csv_path.open("r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    assert len(rows) == 1
    row = rows[0]
    assert row["GPSLatitude"] == "30.0"
    assert row["GPSLongitude"] == "-90.0"
    assert row["XMP-ArchAerial:MethaneConcentration"] == "1234.5"
    assert row["XMP-ArchAerial:PAC"] == "49.38"
    assert row["XMP-ArchAerial:RelativeAltitude"] == "25.0"
    assert row["XMP-ArchAerial:UAVYaw"] == "180.5"
    assert row["XMP-ArchAerial:CaptureTime"] == "2023-01-01 12:00:00"
