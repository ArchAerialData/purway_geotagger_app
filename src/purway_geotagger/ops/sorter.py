from __future__ import annotations

from pathlib import Path
import shutil

from purway_geotagger.core.job import Job
from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.util.paths import ensure_dir

def sort_into_ppm_bins(job: Job, tasks: list[PhotoTask]) -> None:
    """Copy output JPGs into PPM bin folders.

    Policy (skeleton):
    - Creates COPIES into BY_PPM/ bins so the primary output location remains unchanged.
    - Future enhancement: allow Move instead of Copy.
    """
    edges = sorted(job.options.ppm_bin_edges)
    bins_root = ensure_dir(job.run_folder / "BY_PPM")

    for t in tasks:
        if t.status != "SUCCESS":
            continue
        ppm = float(t.ppm or 0.0)
        folder_name = _bin_folder_name(ppm, edges)
        dst_dir = ensure_dir(bins_root / folder_name)
        dst = dst_dir / t.output_path.name
        dst = _collision_safe(dst)
        shutil.copy2(t.output_path, dst)

def _bin_folder_name(ppm: float, edges: list[int]) -> str:
    if not edges:
        return "UNSPECIFIED"
    edges = sorted(edges)
    for i in range(len(edges) - 1):
        lo = edges[i]
        hi = edges[i+1] - 1
        if lo <= ppm <= hi:
            return f"{lo:04d}-{hi:04d}ppm"
    if ppm >= edges[-1]:
        return f"{edges[-1]:04d}+ppm"
    return f"LT{edges[0]:04d}ppm"

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
