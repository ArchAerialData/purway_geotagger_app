from __future__ import annotations

import pytest

from purway_geotagger.core.wind_docx import (
    WindInputValidationError,
    WindReportMetadataRaw,
    WindRowRaw,
    build_wind_template_payload,
)


def _valid_metadata() -> WindReportMetadataRaw:
    return WindReportMetadataRaw(
        client_name="TargaResources",
        system_name="KDB-20",
        report_date="2026-02-06",
        timezone="cst",
    )


def _valid_start() -> WindRowRaw:
    return WindRowRaw(
        time_value="10:00",
        wind_direction="sw",
        wind_speed_mph="7",
        gust_mph="11",
        temp_f="51",
    )


def _valid_end() -> WindRowRaw:
    return WindRowRaw(
        time_value="13:00",
        wind_direction=" nne ",
        wind_speed_mph="9",
        gust_mph="15",
        temp_f="54",
    )


def test_build_payload_success_and_debug_shape() -> None:
    result = build_wind_template_payload(_valid_metadata(), _valid_start(), _valid_end())

    assert result.payload.tz == "CST"
    assert result.payload.s_time == "10:00am"
    assert result.payload.e_time == "1:00pm"
    assert result.payload.s_string == "SW 7 mph / Gusts 11 mph / 51\u00B0F"
    assert result.payload.e_string == "NNE 9 mph / Gusts 15 mph / 54\u00B0F"
    assert result.payload.as_placeholder_map()["TZ"] == "CST"

    debug = result.debug_payload.to_dict()
    assert "raw_metadata" in debug
    assert "normalized_start" in debug
    assert "computed_strings" in debug
    assert debug["computed_strings"]["output_filename"] == "WindData_TargaResources_2026_02_06.docx"


def test_integer_only_enforcement_rejects_units() -> None:
    bad_start = WindRowRaw(
        time_value="10:00",
        wind_direction="SW",
        wind_speed_mph="17mph",
        gust_mph="20",
        temp_f="51",
    )
    with pytest.raises(WindInputValidationError, match="integer-only"):
        build_wind_template_payload(_valid_metadata(), bad_start, _valid_end())


def test_end_time_before_start_is_rejected() -> None:
    late_start = WindRowRaw(
        time_value="15:00",
        wind_direction="SW",
        wind_speed_mph="10",
        gust_mph="15",
        temp_f="60",
    )
    early_end = WindRowRaw(
        time_value="14:59",
        wind_direction="SW",
        wind_speed_mph="9",
        gust_mph="12",
        temp_f="58",
    )
    with pytest.raises(WindInputValidationError, match="same as or later than start time"):
        build_wind_template_payload(_valid_metadata(), late_start, early_end)


def test_timezone_required_and_non_empty() -> None:
    bad_metadata = WindReportMetadataRaw(
        client_name="TargaResources",
        system_name="KDB-20",
        report_date="2026-02-06",
        timezone="   ",
    )
    with pytest.raises(WindInputValidationError, match="Time Zone is required"):
        build_wind_template_payload(bad_metadata, _valid_start(), _valid_end())


def test_direction_must_be_letter_based() -> None:
    bad_end = WindRowRaw(
        time_value="13:00",
        wind_direction="SW-17",
        wind_speed_mph="9",
        gust_mph="15",
        temp_f="54",
    )
    with pytest.raises(WindInputValidationError, match="letters only"):
        build_wind_template_payload(_valid_metadata(), _valid_start(), bad_end)


def test_debug_payload_filename_uses_whitespace_stripped_client_name() -> None:
    spaced_metadata = WindReportMetadataRaw(
        client_name="Targa Resources",
        system_name="KDB-20",
        report_date="2026-02-06",
        timezone="cst",
    )
    result = build_wind_template_payload(spaced_metadata, _valid_start(), _valid_end())
    debug = result.debug_payload.to_dict()

    assert result.payload.client_name == "Targa Resources"
    assert debug["computed_strings"]["output_filename"] == "WindData_TargaResources_2026_02_06.docx"
