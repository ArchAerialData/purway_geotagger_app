from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.ops.copier import ensure_target_photos
from purway_geotagger.ops.flattener import maybe_flatten
from purway_geotagger.ops.renamer import maybe_rename
from purway_geotagger.ops.sorter import _bin_folder_name
from purway_geotagger.templates.models import RenameTemplate


def _job_options(run_folder: Path, overwrite: bool, cleanup: bool) -> JobOptions:
    return JobOptions(
        output_root=run_folder,
        overwrite_originals=overwrite,
        create_backup_on_overwrite=True,
        flatten=True,
        cleanup_empty_dirs=cleanup,
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


def test_copy_collision_safe(tmp_path: Path) -> None:
    run_folder = tmp_path / "run"
    src1 = tmp_path / "a" / "IMG_0001.jpg"
    src2 = tmp_path / "b" / "IMG_0001.jpg"
    src1.parent.mkdir()
    src2.parent.mkdir()
    src1.write_text("x", encoding="utf-8")
    src2.write_text("x", encoding="utf-8")

    target_map = ensure_target_photos(
        photos=[src1, src2],
        run_folder=run_folder,
        overwrite=False,
        create_backup_on_overwrite=True,
    )

    targets = list(target_map.values())
    assert targets[0].name != targets[1].name
    assert any("_dup" in p.stem for p in targets)


def test_rename_collision_safe(tmp_path: Path) -> None:
    run_folder = tmp_path / "run"
    run_folder.mkdir()
    p1 = run_folder / "a.jpg"
    p2 = run_folder / "b.jpg"
    p1.write_text("x", encoding="utf-8")
    p2.write_text("x", encoding="utf-8")

    template = RenameTemplate(
        id="t",
        name="t",
        client="CLIENT",
        pattern="SAME",
        description="",
    )

    job = Job(
        id="1",
        name="job",
        inputs=[],
        options=JobOptions(
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
            rename_template=template,
            start_index=1,
        ),
    )

    t1 = PhotoTask(src_path=p1, work_path=p1, output_path=p1, matched=True, status="SUCCESS")
    t2 = PhotoTask(src_path=p2, work_path=p2, output_path=p2, matched=True, status="SUCCESS")
    maybe_rename(job, [t1, t2])

    assert t1.output_path.name.startswith("SAME")
    assert t2.output_path.name.startswith("SAME")
    assert t1.output_path.name != t2.output_path.name


def test_bin_edges() -> None:
    edges = [0, 1000]
    assert _bin_folder_name(0, edges) == "0000-0999ppm"
    assert _bin_folder_name(999, edges) == "0000-0999ppm"
    assert _bin_folder_name(1000, edges) == "1000+ppm"


def test_flatten_cleanup_copy_mode_scoped(tmp_path: Path) -> None:
    run_folder = tmp_path / "run"
    nested = run_folder / "GEOTAGGED" / "sub"
    nested.mkdir(parents=True)
    photo = nested / "a.jpg"
    photo.write_text("x", encoding="utf-8")

    external = tmp_path / "external"
    external.mkdir()

    job = Job(
        id="1",
        name="job",
        inputs=[external],
        options=_job_options(run_folder, overwrite=False, cleanup=True),
    )
    job.run_folder = run_folder

    t = PhotoTask(src_path=photo, work_path=photo, output_path=photo, matched=True, status="SUCCESS")
    maybe_flatten(job, [t])

    assert (run_folder / "JPG_FLAT" / "a.jpg").exists()
    assert not nested.exists()
    assert external.exists()


def test_flatten_cleanup_overwrite_mode_scoped(tmp_path: Path) -> None:
    run_folder = tmp_path / "run"
    run_folder.mkdir()
    input_root = tmp_path / "input"
    nested = input_root / "sub"
    nested.mkdir(parents=True)
    photo = nested / "a.jpg"
    photo.write_text("x", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()

    job = Job(
        id="1",
        name="job",
        inputs=[input_root],
        options=_job_options(run_folder, overwrite=True, cleanup=True),
    )
    job.run_folder = run_folder

    t = PhotoTask(src_path=photo, work_path=photo, output_path=photo, matched=True, status="SUCCESS")
    maybe_flatten(job, [t])

    assert (run_folder / "JPG_FLAT" / "a.jpg").exists()
    assert not nested.exists()
    assert input_root.exists()
    assert outside.exists()
