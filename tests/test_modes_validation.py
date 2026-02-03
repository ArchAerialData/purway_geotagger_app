from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.modes import RunMode
from purway_geotagger.gui.mode_state import ModeState, validate_mode_state


def _tmp_input(tmp_path: Path) -> Path:
    p = tmp_path / "inputs"
    p.mkdir()
    return p


def test_validate_requires_inputs(tmp_path: Path) -> None:
    state = ModeState(mode=RunMode.METHANE, inputs=[])
    issues = validate_mode_state(state)
    assert any(i.field_id == "inputs" for i in issues)


def test_encroachment_requires_output_base(tmp_path: Path) -> None:
    inputs = [_tmp_input(tmp_path)]
    state = ModeState(mode=RunMode.ENCROACHMENT, inputs=inputs, encroachment_output_base=None)
    issues = validate_mode_state(state)
    assert any(i.field_id == "encroachment_output_base" for i in issues)


def test_rename_requires_client_abbr_when_no_template(tmp_path: Path) -> None:
    inputs = [_tmp_input(tmp_path)]
    state = ModeState(
        mode=RunMode.ENCROACHMENT,
        inputs=inputs,
        encroachment_output_base=tmp_path / "out",
        encroachment_rename_enabled=True,
        encroachment_template_id=None,
        encroachment_client_abbr="",
        encroachment_start_index=1,
    )
    issues = validate_mode_state(state)
    assert any(i.field_id == "encroachment_client_abbr" for i in issues)
