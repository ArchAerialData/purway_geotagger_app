from __future__ import annotations

from pathlib import Path

import pytest

from purway_geotagger.core.wind_docx import WindInputValidationError, WindRowRaw
from purway_geotagger.gui.pages.wind_data_logic import (
    build_live_preview_payload,
    compute_generate_availability,
    resolve_default_wind_template_path,
    resolve_wind_template_for_inputs,
    to_24h_time_string,
)


def test_resolve_default_wind_template_path() -> None:
    path = resolve_default_wind_template_path()
    assert path.name == "PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx"
    assert path.exists(), f"Expected default wind template to exist at: {path}"


def test_generate_availability_requires_template(tmp_path: Path) -> None:
    enabled, reason = compute_generate_availability(
        template_path=tmp_path / "missing.docx",
        output_dir_text=str(tmp_path),
        validation_error=None,
    )
    assert enabled is False
    assert "template" in reason.lower()


def test_generate_availability_requires_output_folder(tmp_path: Path) -> None:
    template = resolve_default_wind_template_path()
    enabled, reason = compute_generate_availability(
        template_path=template,
        output_dir_text="",
        validation_error=None,
    )
    assert enabled is False
    assert "output folder" in reason.lower()


def test_generate_availability_requires_validated_inputs(tmp_path: Path) -> None:
    template = resolve_default_wind_template_path()
    enabled, reason = compute_generate_availability(
        template_path=template,
        output_dir_text=str(tmp_path),
        validation_error="Client Name is required.",
    )
    assert enabled is False
    assert reason == "Client Name is required."


def test_generate_availability_passes_when_ready(tmp_path: Path) -> None:
    template = resolve_default_wind_template_path()
    enabled, reason = compute_generate_availability(
        template_path=template,
        output_dir_text=str(tmp_path),
        validation_error=None,
    )
    assert enabled is True
    assert reason == ""


def test_to_24h_time_string_converts_am_pm() -> None:
    assert to_24h_time_string(hour_12=10, minute=0, meridiem="AM") == "10:00"
    assert to_24h_time_string(hour_12=1, minute=5, meridiem="PM") == "13:05"
    assert to_24h_time_string(hour_12=12, minute=0, meridiem="AM") == "00:00"
    assert to_24h_time_string(hour_12=12, minute=0, meridiem="PM") == "12:00"


def test_to_24h_time_string_validates_inputs() -> None:
    with pytest.raises(ValueError, match="hour_12"):
        to_24h_time_string(hour_12=0, minute=0, meridiem="AM")
    with pytest.raises(ValueError, match="minute"):
        to_24h_time_string(hour_12=10, minute=60, meridiem="AM")
    with pytest.raises(ValueError, match="meridiem"):
        to_24h_time_string(hour_12=10, minute=0, meridiem="NOON")


def test_build_live_preview_payload_is_independent_of_metadata() -> None:
    payload = build_live_preview_payload(
        WindRowRaw(
            time_value="10:00",
            wind_direction="SSW",
            wind_speed_mph=5,
            gust_mph=20,
            temp_f=51,
        ),
        WindRowRaw(
            time_value="13:00",
            wind_direction="NNW",
            wind_speed_mph=16,
            gust_mph=20,
            temp_f=55,
        ),
    )

    assert payload.s_time == "10:00am"
    assert payload.s_string == "SSW 5 mph / Gusts 20 mph / 51\u00B0F"
    assert payload.e_time == "1:00pm"
    assert payload.e_string == "NNW 16 mph / Gusts 20 mph / 55\u00B0F"


def test_build_live_preview_payload_raises_for_invalid_wind_rows() -> None:
    with pytest.raises(WindInputValidationError, match="Start wind direction"):
        build_live_preview_payload(
            WindRowRaw(
                time_value="10:00",
                wind_direction="",
                wind_speed_mph=5,
                gust_mph=20,
                temp_f=51,
            ),
            WindRowRaw(
                time_value="13:00",
                wind_direction="NNW",
                wind_speed_mph=16,
                gust_mph=20,
                temp_f=55,
            ),
        )


@pytest.mark.parametrize(
    ("system_name", "region_id", "expected_stem"),
    (
        ("System-1", "", "WindData_ClientName_SYSTEM_YYYY_MM_DD.docx"),
        ("", "Region-7", "WindData_ClientName_Region_YYYY_MM_DD.docx"),
        ("System-1", "Region-7", "WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx"),
    ),
)
def test_resolve_wind_template_for_inputs(system_name: str, region_id: str, expected_stem: str) -> None:
    selection = resolve_wind_template_for_inputs(system_name=system_name, region_id=region_id)
    assert selection.template_path.exists()
    assert selection.template_path.name == expected_stem
    assert selection.required_placeholders


def test_resolve_wind_template_for_inputs_rejects_blank_blank() -> None:
    with pytest.raises(ValueError, match="System ID or Region is required"):
        resolve_wind_template_for_inputs(system_name="  ", region_id=" ")
