from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.job import Job
from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.templates.template_manager import render_filename

def maybe_rename(job: Job, tasks: list[PhotoTask]) -> None:
    """Rename output photos in-place according to job template settings.

    Updates task.output_path.
    """
    opts = job.options
    if not opts.enable_renaming or not opts.rename_template:
        return

    index = opts.start_index
    for t in tasks:
        if t.status != "SUCCESS":
            continue

        new_base = render_filename(
            template=opts.rename_template,
            index=index,
            ppm=t.ppm or 0.0,
            lat=t.lat or 0.0,
            lon=t.lon or 0.0,
            orig=t.output_path.stem,
        )
        index += 1
        new_path = t.output_path.with_name(new_base + t.output_path.suffix.lower())
        new_path = _collision_safe(new_path)
        t.output_path.rename(new_path)
        t.output_path = new_path

def _collision_safe(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suf = path.suffix
    parent = path.parent
    i = 1
    while True:
        cand = parent / f"{stem}_dup{i}{suf}"
        if not cand.exists():
            return cand
        i += 1
