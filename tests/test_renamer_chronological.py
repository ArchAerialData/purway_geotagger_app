from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.ops.renamer import maybe_rename
from purway_geotagger.templates.models import RenameTemplate


def _job_options(run_folder: Path) -> JobOptions:
    return JobOptions(
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
        enable_renaming=True,
        rename_template=RenameTemplate(
            id="t",
            name="t",
            client="C",
            pattern="X{index:02d}",
            description="",
        ),
        start_index=1,
    )


def test_chronological_rename_keeps_missing_in_group(tmp_path: Path) -> None:
    run_folder = tmp_path / "run"
    run_folder.mkdir()

    folder_a = tmp_path / "A"
    folder_b = tmp_path / "B"
    folder_a.mkdir()
    folder_b.mkdir()

    a1 = folder_a / "a1.jpg"
    a2 = folder_a / "a2.jpg"
    b1 = folder_b / "b1.jpg"
    for p in (a1, a2, b1):
        p.write_text("x", encoding="utf-8")

    job = Job(id="1", name="job", inputs=[], options=_job_options(run_folder))

    t1 = PhotoTask(src_path=a1, work_path=a1, output_path=a1, matched=True, status="SUCCESS")
    t1.datetime_original = "2026:01:01 10:00:00"
    t2 = PhotoTask(src_path=a2, work_path=a2, output_path=a2, matched=True, status="SUCCESS")
    t2.datetime_original = None
    t3 = PhotoTask(src_path=b1, work_path=b1, output_path=b1, matched=True, status="SUCCESS")
    t3.datetime_original = "2026:01:01 11:00:00"

    maybe_rename(job, [t1, t2, t3])

    def idx(task: PhotoTask) -> int:
        stem = task.output_path.stem
        return int(stem.replace("X", ""))

    assert idx(t1) == 1
    assert idx(t2) == 2
    assert idx(t3) == 3
