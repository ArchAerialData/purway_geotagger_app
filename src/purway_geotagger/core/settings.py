from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
from datetime import datetime
from appdirs import user_config_dir

DEFAULT_BIN_EDGES = [0, 1000]  # ppm
DEFAULT_MAX_JOIN_DELTA_SECONDS = 3

def _config_path() -> Path:
    cfg_dir = Path(user_config_dir(appname="PurwayGeotagger", appauthor=False))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "settings.json"

@dataclass
class AppSettings:
    """User-persistent settings.

    Stored in: ~/Library/Application Support/PurwayGeotagger/settings.json (macOS)
    """
    last_output_dir: str = ""
    overwrite_originals_default: bool = False
    create_backup_on_overwrite: bool = True
    flatten_default: bool = False
    cleanup_empty_dirs_default: bool = False
    sort_by_ppm_default: bool = True
    ppm_bin_edges: list[int] = field(default_factory=lambda: DEFAULT_BIN_EDGES.copy())
    max_join_delta_seconds: int = DEFAULT_MAX_JOIN_DELTA_SECONDS
    write_xmp_default: bool = True
    dry_run_default: bool = False
    exiftool_path: str = ""
    ui_theme: str = "light"
    last_mode: str = ""
    confirm_methane: bool = True
    confirm_encroachment: bool = True
    confirm_combined: bool = True

    @classmethod
    def load(cls) -> "AppSettings":
        p = _config_path()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return cls(**data)
        except Exception:
            # Fail safe: return defaults (do not crash pilots in field)
            return cls()

    def save(self) -> None:
        p = _config_path()
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @staticmethod
    def new_run_folder(output_root: Path) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return output_root / f"PurwayGeotagger_{stamp}"
