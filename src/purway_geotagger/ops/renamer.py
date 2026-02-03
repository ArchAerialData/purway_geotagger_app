from __future__ import annotations

from pathlib import Path
from datetime import datetime
from collections import defaultdict

from purway_geotagger.core.job import Job
from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.templates.template_manager import render_filename
from purway_geotagger.util.timeparse import parse_photo_timestamp_from_name

def maybe_rename(job: Job, tasks: list[PhotoTask]) -> None:
    """Rename output photos in-place according to job template settings.

    Updates task.output_path.
    """
    opts = job.options
    if not opts.enable_renaming or not opts.rename_template:
        return

    ordered = _chronological_tasks(tasks)
    index = opts.start_index
    for t in ordered:
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


def _chronological_tasks(tasks: list[PhotoTask]) -> list[PhotoTask]:
    groups: dict[Path, list[PhotoTask]] = defaultdict(list)
    for t in tasks:
        if t.status != "SUCCESS":
            continue
        groups[t.src_path.parent].append(t)

    def task_time(task: PhotoTask) -> datetime | None:
        if task.datetime_original:
            try:
                return datetime.strptime(task.datetime_original, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass
        return parse_photo_timestamp_from_name(task.src_path.stem)

    def group_key(item: tuple[Path, list[PhotoTask]]):
        group = item[1]
        times = [task_time(t) for t in group]
        times = [t for t in times if t is not None]
        earliest = min(times) if times else datetime.max
        return (earliest, str(item[0]).lower())

    ordered: list[PhotoTask] = []
    for _, group in sorted(groups.items(), key=group_key):
        def sort_key(t: PhotoTask):
            ts = task_time(t)
            return (ts is None, ts or datetime.max, t.src_path.name.lower())
        ordered.extend(sorted(group, key=sort_key))
    return ordered

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
