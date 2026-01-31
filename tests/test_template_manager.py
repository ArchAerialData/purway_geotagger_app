from __future__ import annotations

import json
from pathlib import Path

from purway_geotagger.templates.models import RenameTemplate
from purway_geotagger.templates.template_manager import TemplateManager


def _write_defaults(path: Path) -> None:
    payload = {
        "templates": [
            {
                "id": "default",
                "name": "Default",
                "client": "CLIENT",
                "pattern": "{client}_{index:03d}",
                "description": "",
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_template_manager_persists_overrides(tmp_path: Path) -> None:
    defaults = tmp_path / "defaults.json"
    user = tmp_path / "user.json"
    _write_defaults(defaults)

    mgr = TemplateManager(default_templates_path=defaults, user_templates_path=user)
    assert len(mgr.list_templates()) == 1

    mgr.delete("default")
    assert len(mgr.list_templates()) == 0

    custom = RenameTemplate(
        id="custom",
        name="Custom",
        client="ACME",
        pattern="{client}_{index}",
        description="",
    )
    mgr.upsert(custom)
    assert len(mgr.list_templates()) == 1

    mgr2 = TemplateManager(default_templates_path=defaults, user_templates_path=user)
    ids = [t.id for t in mgr2.list_templates()]
    assert "default" not in ids
    assert "custom" in ids
