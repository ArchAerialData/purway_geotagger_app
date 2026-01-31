from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.pipeline import run_job
from purway_geotagger.exif import exiftool_writer as exif_module


def test_payload_is_appended_to_description(tmp_path: Path, monkeypatch) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    jpg = input_dir / "IMG_0001.jpg"
    jpg.write_text("x", encoding="utf-8")

    csv_path = input_dir / "data.csv"
    csv_path.write_text(
        "Latitude,Longitude,PPM,Photo\n"
        "1.0,2.0,10,IMG_0001.jpg\n",
        encoding="utf-8",
        newline="\n",
    )

    run_folder = tmp_path / "PurwayGeotagger_TEST"
    opts = JobOptions(
        output_root=run_folder,
        overwrite_originals=False,
        create_backup_on_overwrite=True,
        flatten=False,
        cleanup_empty_dirs=False,
        sort_by_ppm=False,
        ppm_bin_edges=[0, 100, 500, 1000],
        write_xmp=True,
        dry_run=False,
        max_join_delta_seconds=3,
        purway_payload="PAYLOAD123",
        enable_renaming=False,
        rename_template=None,
        start_index=1,
    )

    def fake_write_tasks(self, tasks, work_dir, progress_cb, cancel_cb):
        matched = [t for t in tasks if t.matched]
        assert matched, "Expected at least one matched task"
        assert "purway_payload=PAYLOAD123" in matched[0].image_description
        return {t.output_path: exif_module.ExifWriteResult(success=True) for t in matched}

    monkeypatch.setattr(exif_module.ExifToolWriter, "write_tasks", fake_write_tasks)

    job = Job(id="1", name="job", inputs=[input_dir], options=opts)
    run_job(job, progress_cb=lambda *_: None, cancel_cb=lambda: False)
