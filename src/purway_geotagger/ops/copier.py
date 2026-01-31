from __future__ import annotations

from pathlib import Path
import shutil
from typing import Iterable

from purway_geotagger.util.paths import ensure_dir

def ensure_target_photos(
    photos: list[Path],
    run_folder: Path,
    overwrite: bool,
    create_backup_on_overwrite: bool,
) -> dict[Path, Path]:
    """Prepare target photos.

    Returns mapping: source photo -> target photo.
    - overwrite=True: target is source (in-place). Optionally create .bak copy.
    - overwrite=False: copy photos into <run_folder>/GEOTAGGED/ preserving relative names only (flattened copy),
      then target is the copy path.
    """
    out: dict[Path, Path] = {}

    if overwrite:
        for p in photos:
            if create_backup_on_overwrite:
                bak = p.with_suffix(p.suffix + ".bak")
                if not bak.exists():
                    shutil.copy2(p, bak)
            out[p] = p
        return out

    geotagged_dir = ensure_dir(run_folder / "GEOTAGGED")
    for p in photos:
        # Default copy behavior: keep original filename, collision-safe
        tgt = geotagged_dir / p.name
        tgt = _collision_safe(tgt)
        shutil.copy2(p, tgt)
        out[p] = tgt

    return out

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
