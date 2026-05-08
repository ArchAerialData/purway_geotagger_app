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
    task.target_lat = 28.2
    task.target_lon = -97.3
    task.distance = 12.5
    task.altitude = 40.0
    task.source_file_name = "source.jpg"
    task.source_csv = "methane.csv"
    task.join_method = "FILENAME"
    task.join_delta_seconds = 0.0
    task.payload_model = "Purway Model II"
    task.geotagger_version = "0.1.0"
    task.geotagger_run_id = "run-1"
    task.csv_status = "SUCCESS"
    task.err_code = "0"
    task.snr = 18.5
    task.reliability = 0.97
    task.flight_status = "IN_AIR"
    task.dis_code = "D7"
    task.home_distance = 120.0
    task.speed = 8.2
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
    assert row["XMP-ArchAerial:TargetLatitude"] == "28.2"
    assert row["XMP-ArchAerial:TargetLongitude"] == "-97.3"
    assert row["XMP-ArchAerial:Distance"] == "12.5"
    assert row["XMP-ArchAerial:Altitude"] == "40.0"
    assert row["XMP-ArchAerial:SourceFileName"] == "source.jpg"
    assert row["XMP-ArchAerial:SourceCSV"] == "methane.csv"
    assert row["XMP-ArchAerial:JoinMethod"] == "FILENAME"
    assert row["XMP-ArchAerial:JoinDeltaSeconds"] == "0.0"
    assert row["XMP-ArchAerial:PayloadModel"] == "Purway Model II"
    assert row["XMP-ArchAerial:GeotaggerVersion"] == "0.1.0"
    assert row["XMP-ArchAerial:GeotaggerRunId"] == "run-1"
    assert row["XMP-ArchAerial:Status"] == "SUCCESS"
    assert row["XMP-ArchAerial:ErrCode"] == "0"
    assert row["XMP-ArchAerial:SNR"] == "18.5"
    assert row["XMP-ArchAerial:Reliability"] == "0.97"
    assert row["XMP-ArchAerial:FlightStatus"] == "IN_AIR"
    assert row["XMP-ArchAerial:DisCode"] == "D7"
    assert row["XMP-ArchAerial:HomeDistance"] == "120.0"
    assert row["XMP-ArchAerial:Speed"] == "8.2"
    assert row["XMP-ArchAerial:RelativeAltitude"] == "25.0"
    assert row["XMP-ArchAerial:UAVYaw"] == "180.5"
    assert row["XMP-ArchAerial:CaptureTime"] == "2023-01-01 12:00:00"
