from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from purway_geotagger.templates.models import RenameTemplate
try:
    from appdirs import user_config_dir
except ModuleNotFoundError:  # pragma: no cover - only used in minimal test envs
    def user_config_dir(*_args, **_kwargs):
        raise ModuleNotFoundError("appdirs is required for user template storage.")

DEFAULT_TEMPLATES_PATH = Path(__file__).resolve().parents[3] / "config" / "default_templates.json"

def _user_templates_path() -> Path:
    cfg_dir = Path(user_config_dir(appname="PurwayGeotagger", appauthor=False))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "templates.json"

class TemplateManager:
    """Manages rename templates.

    Storage strategy:
    - Load defaults from config/default_templates.json (read-only)
    - Store user templates in user config dir (future enhancement)
    """

    def __init__(
        self,
        default_templates_path: Path | None = None,
        user_templates_path: Path | None = None,
    ) -> None:
        self.templates: dict[str, RenameTemplate] = {}
        self._default_templates: dict[str, RenameTemplate] = {}
        self._deleted_default_ids: set[str] = set()
        self.default_templates_path = default_templates_path or DEFAULT_TEMPLATES_PATH
        self.user_templates_path = user_templates_path or _user_templates_path()
        self.load_defaults()
        self.load_user_templates()

    def load_defaults(self) -> None:
        data = json.loads(self.default_templates_path.read_text(encoding="utf-8"))
        for t in data.get("templates", []):
            rt = RenameTemplate(**t)
            self.templates[rt.id] = rt
            self._default_templates[rt.id] = rt

    def load_user_templates(self) -> None:
        p = self.user_templates_path
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        deleted = data.get("deleted_default_ids", [])
        self._deleted_default_ids = set(deleted)
        for t in data.get("templates", []):
            rt = RenameTemplate(**t)
            self.templates[rt.id] = rt
        for tid in self._deleted_default_ids:
            self.templates.pop(tid, None)

    def list_templates(self) -> list[RenameTemplate]:
        return sorted(self.templates.values(), key=lambda t: t.name.lower())

    def upsert(self, t: RenameTemplate) -> None:
        self.templates[t.id] = t
        if t.id in self._deleted_default_ids:
            self._deleted_default_ids.remove(t.id)
        self.save_user_templates()

    def delete(self, template_id: str) -> None:
        if template_id in self._default_templates:
            self._deleted_default_ids.add(template_id)
        self.templates.pop(template_id, None)
        self.save_user_templates()

    def save_user_templates(self) -> None:
        out: list[dict[str, Any]] = []
        for tid, tmpl in self.templates.items():
            default = self._default_templates.get(tid)
            if default and asdict(default) == asdict(tmpl):
                continue
            out.append(asdict(tmpl))
        payload = {
            "templates": out,
            "deleted_default_ids": sorted(self._deleted_default_ids),
        }
        self.user_templates_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def render_filename(template: RenameTemplate, index: int, ppm: float, lat: float, lon: float, orig: str) -> str:
    """Render a filename (without extension) from template tokens.

    Supported tokens:
      {client} {date} {time} {index} {index:05d} {ppm} {lat} {lon} {orig}
    """
    from datetime import datetime

    now = datetime.now()
    ctx: dict[str, Any] = {
        "client": template.client,
        "date": now.strftime("%Y%m%d"),
        "time": now.strftime("%H%M%S"),
        "index": index,
        "ppm": int(round(ppm)),
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "orig": orig,
    }
    try:
        return template.pattern.format(**ctx)
    except Exception as e:
        # In production, surface this to GUI as a validation error.
        raise ValueError(f"Template format error: {e}") from e
