from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.modes import common_parent, default_methane_log_base, default_encroachment_base
from purway_geotagger.gui.mode_state import ModeState


def test_common_parent_with_shared_root(tmp_path: Path) -> None:
    a = tmp_path / "A"
    b = tmp_path / "B"
    a.mkdir()
    b.mkdir()
    common = common_parent([a / "one", b / "two"])
    assert common == tmp_path


def test_default_methane_log_base_uses_common_parent(tmp_path: Path) -> None:
    a = tmp_path / "A"
    b = tmp_path / "B"
    a.mkdir()
    b.mkdir()
    base = default_methane_log_base([a, b])
    assert base == tmp_path


def test_default_encroachment_base_auto_increments(tmp_path: Path) -> None:
    inp = tmp_path / "inputs"
    inp.mkdir()
    first = inp / "Encroachment_Output"
    first.mkdir()
    base = default_encroachment_base([inp])
    assert base.name == "Encroachment_Output_2"


def test_mode_state_resolves_defaults(tmp_path: Path) -> None:
    inp = tmp_path / "inputs"
    inp.mkdir()
    state = ModeState(inputs=[inp])
    resolved = state.resolved()
    assert resolved.methane_log_base is not None
    assert resolved.encroachment_output_base is not None
