from __future__ import annotations

from datetime import date, datetime, time

from purway_geotagger.core.wind_docx import (
    WindReportMetadataRaw,
    WindRowRaw,
    build_wind_output_filename,
    build_wind_template_payload,
    format_wind_summary,
    format_wind_time,
    normalize_report_date,
)


def test_normalize_report_date_supported_inputs() -> None:
    assert normalize_report_date(date(2026, 2, 6)) == "2026_02_06"
    assert normalize_report_date(datetime(2026, 2, 6, 11, 22)) == "2026_02_06"
    assert normalize_report_date("2026-02-06") == "2026_02_06"
    assert normalize_report_date("2026/02/06") == "2026_02_06"
    assert normalize_report_date("02/06/2026") == "2026_02_06"


def test_format_wind_time_contract_style() -> None:
    assert format_wind_time(time(10, 0)) == "10:00am"
    assert format_wind_time(time(13, 0)) == "1:00pm"
    assert format_wind_time("01:05 PM") == "1:05pm"
    assert format_wind_time("00:07") == "12:07am"


def test_format_wind_summary_contract_string() -> None:
    assert format_wind_summary("SW", 0, 1, 51) == "SW 0 mph / Gusts 1 mph / 51\u00B0F"
    assert format_wind_summary("NNE", 12, 17, -2) == "NNE 12 mph / Gusts 17 mph / -2\u00B0F"


def test_output_filename_reuses_payload_values() -> None:
    metadata = WindReportMetadataRaw(
        client_name="TargaResources",
        system_name="KDB 20-IN",
        report_date="2026-02-06",
    )
    start = WindRowRaw("10:00", "SW", "0", "1", "51")
    end = WindRowRaw("13:00", "SW", "0", "1", "51")
    result = build_wind_template_payload(metadata, start, end)

    assert result.payload.date == "2026_02_06"
    assert result.payload.output_filename() == "WindData_TargaResources_2026_02_06.docx"
    assert build_wind_output_filename(result.payload.client_name, result.payload.date) == (
        "WindData_TargaResources_2026_02_06.docx"
    )


def test_output_filename_strips_whitespace_from_client_name_only() -> None:
    metadata = WindReportMetadataRaw(
        client_name="Targa Resources",
        system_name="KDB 20-IN",
        report_date="2026-02-06",
    )
    start = WindRowRaw("10:00", "SW", "0", "1", "51")
    end = WindRowRaw("13:00", "SW", "0", "1", "51")
    result = build_wind_template_payload(metadata, start, end)

    assert result.payload.client_name == "Targa Resources"
    assert result.payload.output_filename() == "WindData_TargaResources_2026_02_06.docx"
