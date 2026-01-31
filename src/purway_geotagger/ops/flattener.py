from __future__ import annotations

from pathlib import Path
import shutil

from purway_geotagger.core.job import Job
from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.util.paths import ensure_dir

def maybe_flatten(job: Job, tasks: list[PhotoTask]) -> None:
    """Move all SUCCESS photos into a single folder if enabled.

    Updates task.output_path.
    """
    if not job.options.flatten:
        return

    flat_dir = ensure_dir(job.run_folder / "JPG_FLAT")
    moved_parents: set[Path] = set()
    for t in tasks:
        if t.status != "SUCCESS":
            continue
        src = t.output_path
        moved_parents.add(src.parent)
        dst = flat_dir / src.name
        dst = _collision_safe(dst)
        shutil.move(str(src), str(dst))
        t.output_path = dst

    if job.options.cleanup_empty_dirs:
        _cleanup_empty_dirs(job, moved_parents)

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

def _cleanup_empty_dirs(job: Job, candidates: set[Path]) -> None:
    """Remove empty directories left behind after flatten.

    Scope rules:
    - Copy mode (overwrite_originals=False): only under job.run_folder.
    - Overwrite mode: only under user-selected input roots (directories only).
    """
    roots = _cleanup_roots(job)
    if not roots:
        return

    for parent in candidates:
        p = parent.resolve()
        for root in roots:
            if _is_within(p, root) and p != root:
                _prune_empty_upwards(p, root)
                break

def _cleanup_roots(job: Job) -> list[Path]:
    if job.options.overwrite_originals:
        roots = [p.resolve() for p in job.inputs if p.exists() and p.is_dir()]
        return roots
    if job.run_folder:
        return [job.run_folder.resolve()]
    return []

def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

def _prune_empty_upwards(start: Path, root: Path) -> None:
    cur = start
    while cur != root and _is_within(cur, root):
        try:
            if any(cur.iterdir()):
                break
            cur.rmdir()
        except FileNotFoundError:
            break
        except OSError:
            break
        cur = cur.parent
