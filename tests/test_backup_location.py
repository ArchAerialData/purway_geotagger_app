from __future__ import annotations

from pathlib import Path

from purway_geotagger.ops.copier import ensure_target_photos


def test_backups_written_under_run_folder(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    nested = input_root / "sub"
    nested.mkdir(parents=True)
    photo = nested / "a.jpg"
    photo.write_text("x", encoding="utf-8")

    run_folder = tmp_path / "run"
    backup_root = run_folder / "BACKUPS"

    mapping = ensure_target_photos(
        photos=[photo],
        run_folder=run_folder,
        overwrite=True,
        create_backup_on_overwrite=True,
        backup_root=backup_root,
        backup_rel_base=input_root,
    )

    assert mapping[photo] == photo
    backup_path = backup_root / "sub" / "a.jpg.bak"
    assert backup_path.exists()
    assert not photo.with_suffix(photo.suffix + ".bak").exists()
