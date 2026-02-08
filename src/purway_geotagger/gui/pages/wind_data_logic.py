from __future__ import annotations

import os
from pathlib import Path

from purway_geotagger.core.wind_docx import (
    WindReportMetadataRaw,
    WindRowRaw,
    WindTemplatePayload,
    build_wind_template_payload,
)
from purway_geotagger.core.utils import resource_path


_TEMPLATE_CANDIDATES = (
    "config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx",
    "wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx",
)

_PREVIEW_METADATA = WindReportMetadataRaw(
    client_name="PREVIEW_CLIENT",
    system_name="PREVIEW_SYSTEM",
    report_date="2000_01_01",
    timezone="CST",
)


def resolve_default_wind_template_path() -> Path:
    candidates = [resource_path(rel) for rel in _TEMPLATE_CANDIDATES]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Fall back to the dev template path so the browse field is pre-populated.
    return candidates[-1]


def compute_generate_availability(
    *,
    template_path: Path | None,
    output_dir_text: str,
    validation_error: str | None,
) -> tuple[bool, str]:
    if template_path is None or not template_path.exists():
        return False, "Select a valid Wind Data template (.docx)."

    output_text = (output_dir_text or "").strip()
    if not output_text:
        return False, "Select an output folder for generated DOCX files."

    output_dir = Path(output_text)
    if not output_dir.exists() or not output_dir.is_dir():
        return False, "Select a valid output folder."
    if not os.access(output_dir, os.W_OK):
        return False, "Selected output folder is not writable."

    if validation_error:
        return False, validation_error
    return True, ""


def to_24h_time_string(*, hour_12: int, minute: int, meridiem: str) -> str:
    if hour_12 < 1 or hour_12 > 12:
        raise ValueError("hour_12 must be in range 1..12")
    if minute < 0 or minute > 59:
        raise ValueError("minute must be in range 0..59")
    marker = (meridiem or "").strip().upper()
    if marker not in {"AM", "PM"}:
        raise ValueError("meridiem must be AM or PM")

    hour_24 = hour_12 % 12
    if marker == "PM":
        hour_24 += 12
    return f"{hour_24:02d}:{minute:02d}"


def build_live_preview_payload(start_raw: WindRowRaw, end_raw: WindRowRaw) -> WindTemplatePayload:
    """Build preview strings from wind rows only, independent of report metadata fields."""
    return build_wind_template_payload(_PREVIEW_METADATA, start_raw, end_raw).payload
