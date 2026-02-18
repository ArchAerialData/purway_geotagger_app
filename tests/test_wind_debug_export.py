from __future__ import annotations

import json
from pathlib import Path

from purway_geotagger.core.wind_docx import WindReportMetadataRaw, WindRowRaw, build_wind_template_payload
from purway_geotagger.core.wind_docx_writer import generate_wind_docx_report


def _production_template_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidates = (
        root / "config" / "wind_templates" / "PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx",
        root / "wind_data_generator" / "Example of Template Structure" / "PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def test_debug_sidecar_contains_required_sections(tmp_path: Path) -> None:
    template = _production_template_path()
    assert template.exists(), f"Missing production template: {template}"

    metadata = WindReportMetadataRaw(
        client_name="TargaResources",
        system_name="KDB-20",
        report_date="2026-02-06",
        timezone="cst",
        region_id="North Sector",
    )
    start = WindRowRaw("10:00", "SW", "0", "1", "51")
    end = WindRowRaw("13:00", "SW", "0", "1", "51")
    report = build_wind_template_payload(metadata, start, end)

    result = generate_wind_docx_report(
        template_path=template,
        output_dir=tmp_path,
        report=report,
    )

    payload = json.loads(result.debug_json_path.read_text(encoding="utf-8"))
    assert payload["raw_metadata"]["client_name"] == "TargaResources"
    assert payload["normalized_metadata"]["timezone"] == "CST"
    assert payload["raw_metadata"]["region_id"] == "North Sector"
    assert payload["normalized_metadata"]["region_id"] == "North Sector"
    assert payload["normalized_start"]["time"] == "10:00am"
    assert payload["computed_strings"]["S_STRING"] == "SW 0 mph / Gusts 1 mph / 51\u00B0F"
    assert payload["placeholder_map"]["DATE"] == "2026_02_06"
    assert payload["placeholder_map"]["REGION_ID"] == "North Sector"
    assert payload["generation"]["output_docx_name"] == result.output_docx_path.name
    assert payload["generation"]["template_path"].endswith(
        "PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx"
    )
