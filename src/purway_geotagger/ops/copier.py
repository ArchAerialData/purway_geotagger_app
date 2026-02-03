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
    copy_root: Path | None = None,
    use_subdir: bool = True,
    backup_root: Path | None = None,
    backup_rel_base: Path | None = None,
) -> dict[Path, Path]:
    """Prepare target photos.

    Returns mapping: source photo -> target photo.
    - overwrite=True: target is source (in-place). Optionally create .bak copy.
    - overwrite=False: copy photos into <run_folder>/GEOTAGGED/ preserving relative names only (flattened copy),
      then target is the copy path.
    """
    out: dict[Path, Path] = {}

    if overwrite:
        backup_dir = backup_root or (run_folder / "BACKUPS")
        for p in photos:
            if create_backup_on_overwrite:
                bak = _backup_target(p, backup_dir, backup_rel_base)
                if not bak.exists():
                    bak.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, bak)
            out[p] = p
        return out

    root = copy_root or run_folder
    geotagged_dir = ensure_dir(root / "GEOTAGGED") if use_subdir else ensure_dir(root)
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


def _backup_target(path: Path, backup_root: Path, backup_rel_base: Path | None) -> Path:
    suffix = path.suffix + ".bak"
    if backup_rel_base:
        try:
            rel = path.relative_to(backup_rel_base)
            candidate = backup_root / rel.parent / f"{path.stem}{suffix}"
            return _collision_safe(candidate)
        except ValueError:
            pass
    candidate = backup_root / f"{path.stem}{suffix}"
    return _collision_safe(candidate)
