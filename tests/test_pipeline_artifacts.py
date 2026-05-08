from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile

import pytest

from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.modes import RunMode
from purway_geotagger.core.pipeline import run_job
from purway_geotagger.util.errors import UserCancelledError


def test_run_job_writes_artifacts_on_cancel() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        run_folder = tmp_path / "PurwayGeotagger_TEST_RUN"

        opts = JobOptions(
            output_root=run_folder,
            overwrite_originals=False,
            create_backup_on_overwrite=True,
            flatten=False,
            cleanup_empty_dirs=False,
            sort_by_ppm=False,
            ppm_bin_edges=[0, 1000],
            write_xmp=True,
            dry_run=True,
            max_join_delta_seconds=3,
            purway_payload="",
            enable_renaming=False,
            rename_template=None,
            start_index=1,
        )

        job = Job(
            id="test",
            name="test",
            inputs=[],
            options=opts,
        )

        with pytest.raises(UserCancelledError):
            run_job(
                job=job,
                progress_cb=lambda _pct, _msg: None,
                cancel_cb=lambda: True,
            )

        assert (run_folder / "run_log.txt").exists()
        assert (run_folder / "run_config.json").exists()
        manifest = run_folder / "manifest.csv"
        assert manifest.exists()
        header = manifest.read_text(encoding="utf-8").splitlines()[0]
        assert "source_path" in header and "output_path" in header


def test_methane_mode_manifest_and_summary_include_metadata_counts(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    jpg = input_dir / "20260128_235719.jpg"
    jpg.write_text("x", encoding="utf-8")
    csv_path = input_dir / "methane.csv"
    csv_path.write_text(
        "time,methane_concentration,longitude,latitude,dest_longitude,dest_latitude,"
        "distance,altitude,file_name,status,err_code,SNR,reliability\n"
        "2026-01-28_23:57:19:149,1500,-97.2,28.1,-97.3,28.2,12.5,40,"
        "20260128_235719.jpg,SUCCESS,0,18.5,0.97\n",
        encoding="utf-8",
    )
    run_folder = tmp_path / "PurwayGeotagger_TEST_RUN"
    opts = JobOptions(
        output_root=run_folder,
        overwrite_originals=True,
        create_backup_on_overwrite=True,
        flatten=False,
        cleanup_empty_dirs=False,
        sort_by_ppm=False,
        ppm_bin_edges=[0, 1000],
        write_xmp=True,
        dry_run=True,
        max_join_delta_seconds=3,
        purway_payload="",
        enable_renaming=False,
        rename_template=None,
        start_index=1,
        run_mode=RunMode.METHANE,
        methane_generate_kmz=False,
    )
    job = Job(id="run-1", name="job", inputs=[input_dir], options=opts)

    run_job(job, progress_cb=lambda *_: None, cancel_cb=lambda: False)

    rows = list(csv.DictReader((run_folder / "manifest.csv").read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "SUCCESS"
    assert row["target_lat"] == "28.2"
    assert row["target_lon"] == "-97.3"
    assert row["distance"] == "12.5"
    assert row["source_file_name"] == "20260128_235719.jpg"
    assert row["source_csv"] == "methane.csv"
    assert row["payload_model"] == "Purway Model II"
    assert row["geotagger_run_id"] == "run-1"
    assert row["csv_status"] == "SUCCESS"

    summary = json.loads((run_folder / "run_summary.json").read_text(encoding="utf-8"))
    metadata = summary["methane_metadata"]
    assert metadata["schema_version"] == "wwm-methane-xmp-v1"
    assert metadata["target_coordinates_written"] == 1
    assert metadata["distance_written"] == 1
    assert metadata["invalid_target_distance_rows"] == 0
    assert metadata["join_method_counts"] == {"FILENAME": 1}


def test_methane_strict_fails_missing_target_but_encroachment_allows(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    jpg = input_dir / "a.jpg"
    jpg.write_text("x", encoding="utf-8")
    csv_path = input_dir / "methane.csv"
    csv_path.write_text(
        "methane_concentration,longitude,latitude,file_name\n"
        "1500,-97.2,28.1,a.jpg\n",
        encoding="utf-8",
    )

    methane_run = tmp_path / "methane_run"
    methane_opts = JobOptions(
        output_root=methane_run,
        overwrite_originals=True,
        create_backup_on_overwrite=True,
        flatten=False,
        cleanup_empty_dirs=False,
        sort_by_ppm=False,
        ppm_bin_edges=[0, 1000],
        write_xmp=True,
        dry_run=True,
        max_join_delta_seconds=3,
        purway_payload="",
        enable_renaming=False,
        rename_template=None,
        start_index=1,
        run_mode=RunMode.METHANE,
        methane_generate_kmz=False,
    )
    run_job(Job(id="methane", name="methane", inputs=[input_dir], options=methane_opts), lambda *_: None, lambda: False)
    methane_rows = list(csv.DictReader((methane_run / "manifest.csv").read_text(encoding="utf-8").splitlines()))
    assert methane_rows[0]["status"] == "FAILED"
    assert "target/distance" in methane_rows[0]["reason"]

    encroachment_run = tmp_path / "encroachment_run"
    encroachment_out = tmp_path / "encroachment_photos"
    encroachment_opts = JobOptions(
        output_root=encroachment_run,
        overwrite_originals=False,
        create_backup_on_overwrite=True,
        flatten=False,
        cleanup_empty_dirs=False,
        sort_by_ppm=False,
        ppm_bin_edges=[0, 1000],
        write_xmp=True,
        dry_run=True,
        max_join_delta_seconds=3,
        purway_payload="",
        enable_renaming=False,
        rename_template=None,
        start_index=1,
        run_mode=RunMode.ENCROACHMENT,
        output_photos_root=encroachment_out,
    )
    run_job(
        Job(id="encroachment", name="encroachment", inputs=[input_dir], options=encroachment_opts),
        lambda *_: None,
        lambda: False,
    )
    encroachment_rows = list(csv.DictReader((encroachment_run / "manifest.csv").read_text(encoding="utf-8").splitlines()))
    assert encroachment_rows[0]["status"] == "SUCCESS"
