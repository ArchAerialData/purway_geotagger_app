from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytest.importorskip("appdirs")

from purway_geotagger.gui.controllers import JobController, _failed_paths_from_manifest
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.templates.template_manager import TemplateManager


def test_failed_paths_from_manifest(tmp_path: Path) -> None:
    photo = tmp_path / "a.jpg"
    photo.write_text("x", encoding="utf-8")
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source_path", "status"])
        w.writeheader()
        w.writerow({"source_path": str(photo), "status": "FAILED"})
        w.writerow({"source_path": str(photo), "status": "SUCCESS"})
    paths = _failed_paths_from_manifest(manifest)
    assert paths == [photo]


def test_suggest_template_id(tmp_path: Path) -> None:
    defaults = tmp_path / "defaults.json"
    defaults.write_text(
        """{"templates":[{"id":"clienta","name":"Client A","client":"ClientA","pattern":"{client}_{index}"}]}""",
        encoding="utf-8",
    )
    user = tmp_path / "user.json"

    controller = JobController(settings=AppSettings())
    controller.template_manager = TemplateManager(default_templates_path=defaults, user_templates_path=user)

    paths = [Path("/data/ClientA/flight1")]
    assert controller.suggest_template_id(paths) == "clienta"
