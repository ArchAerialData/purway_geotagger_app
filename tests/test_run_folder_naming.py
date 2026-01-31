from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("appdirs")

from purway_geotagger.core.settings import AppSettings


def test_run_folder_naming(tmp_path: Path) -> None:
    run_folder = AppSettings.new_run_folder(tmp_path)
    assert run_folder.parent == tmp_path
    assert run_folder.name.startswith("PurwayGeotagger_")
    assert re.fullmatch(r"PurwayGeotagger_\d{8}_\d{6}", run_folder.name)
