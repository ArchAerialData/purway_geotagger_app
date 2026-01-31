from __future__ import annotations

from pathlib import Path
import csv

from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.pipeline import run_job
from purway_geotagger.templates.models import RenameTemplate


def test_dry_run_pipeline_copy_rename_sort_flatten(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    jpg = input_dir / "IMG_0001.jpg"
    jpg.write_text("x", encoding="utf-8")

    csv_path = input_dir / "data.csv"
    csv_path.write_text(
        "Latitude,Longitude,PPM,Photo\n"
        "1.0,2.0,123,IMG_0001.jpg\n",
        encoding="utf-8",
        newline="\n",
    )

    run_folder = tmp_path / "PurwayGeotagger_TEST"

    template = RenameTemplate(
        id="t",
        name="t",
        client="ACME",
        pattern="{client}_{index:03d}_{ppm}ppm_{orig}",
        description="",
    )

    opts = JobOptions(
        output_root=run_folder,
        overwrite_originals=False,
        create_backup_on_overwrite=True,
        flatten=True,
        cleanup_empty_dirs=False,
        sort_by_ppm=True,
        ppm_bin_edges=[0, 1000],
        write_xmp=True,
        dry_run=True,
        max_join_delta_seconds=3,
        purway_payload="",
        enable_renaming=True,
        rename_template=template,
        start_index=1,
    )

    job = Job(id="1", name="job", inputs=[input_dir], options=opts)
    run_job(job, progress_cb=lambda *_: None, cancel_cb=lambda: False)

    assert jpg.exists()
    flat_dir = run_folder / "JPG_FLAT"
    assert flat_dir.exists()

    flat_files = list(flat_dir.glob("*.jpg"))
    assert len(flat_files) == 1
    flat_name = flat_files[0].name
    assert flat_name.startswith("ACME_001_123ppm_")

    bin_dir = run_folder / "BY_PPM" / "0000-0999ppm"
    assert bin_dir.exists()
    assert (bin_dir / flat_name).exists()

    manifest_path = run_folder / "manifest.csv"
    assert manifest_path.exists()
    rows = list(csv.DictReader(manifest_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    row = rows[0]
    assert row["source_path"].endswith("IMG_0001.jpg")
    assert row["status"] == "SUCCESS"
    assert row["exif_written"] == "NO"
    assert "JPG_FLAT" in row["output_path"]
