from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from .wind_docx import WindReportBuildResult
from .wind_template_contract import (
    REQUIRED_PLACEHOLDERS,
    WindTemplateContractError,
    validate_wind_template_contract,
)


class WindDocxWriterError(RuntimeError):
    """Raised when rendering/writing the wind DOCX output fails."""


@dataclass(frozen=True)
class WindDocxRenderResult:
    output_docx_path: Path
    debug_json_path: Path


_EMBEDDED_METADATA_XML_PATH = "customXml/purway_wind_metadata.xml"
_EMBEDDED_METADATA_SCHEMA_VERSION = "1"


def generate_wind_docx_report(
    *,
    template_path: Path,
    output_dir: Path,
    report: WindReportBuildResult,
    output_filename: str | None = None,
) -> WindDocxRenderResult:
    try:
        validate_wind_template_contract(
            template_path=template_path,
            allow_extra_placeholders=False,
            require_tz_header=True,
        )
    except WindTemplateContractError as exc:
        raise WindDocxWriterError(f"Template contract validation failed: {exc}") from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chosen_filename = (output_filename or report.payload.output_filename()).strip()
    if not chosen_filename:
        raise WindDocxWriterError("Output filename is required.")
    if not chosen_filename.lower().endswith(".docx"):
        raise WindDocxWriterError("Output filename must end with .docx")
    if "/" in chosen_filename or "\\" in chosen_filename:
        raise WindDocxWriterError("Output filename cannot contain path separators.")

    output_docx_path = _next_collision_safe_path(output_dir / chosen_filename)
    placeholder_map = report.payload.as_placeholder_map()

    rendered_xml = _render_document_xml(template_path, placeholder_map)
    embedded_metadata_xml = _build_embedded_metadata_xml(
        report=report,
        output_docx_path=output_docx_path,
    )
    _write_rendered_docx(
        template_path=template_path,
        output_docx_path=output_docx_path,
        rendered_xml=rendered_xml,
        embedded_metadata_xml=embedded_metadata_xml,
    )

    debug_json_path = output_docx_path.with_suffix(".debug.json")
    _write_debug_sidecar(
        debug_json_path=debug_json_path,
        report=report,
        template_path=template_path,
        output_docx_path=output_docx_path,
    )
    return WindDocxRenderResult(
        output_docx_path=output_docx_path,
        debug_json_path=debug_json_path,
    )


def _render_document_xml(template_path: Path, placeholder_map: dict[str, str]) -> str:
    document_xml = _read_document_xml(template_path)
    replacement_counts: dict[str, int] = {}
    rendered = document_xml

    for key, value in placeholder_map.items():
        pattern = _placeholder_pattern(key)
        rendered, count = pattern.subn(str(value), rendered)
        replacement_counts[key] = count

    missing_replacements = sorted(
        key for key in REQUIRED_PLACEHOLDERS if replacement_counts.get(key, 0) <= 0
    )
    if missing_replacements:
        raise WindDocxWriterError(
            "Failed to replace required placeholders in template: "
            + ", ".join(missing_replacements)
        )

    unresolved = sorted(
        key for key in REQUIRED_PLACEHOLDERS if _placeholder_pattern(key).search(rendered)
    )
    if unresolved:
        raise WindDocxWriterError(
            "Unresolved required placeholders remain after render: "
            + ", ".join(unresolved)
        )

    return rendered


def _read_document_xml(template_path: Path) -> str:
    try:
        with ZipFile(template_path, "r") as zf:
            try:
                xml = zf.read("word/document.xml")
            except KeyError as exc:
                raise WindDocxWriterError(
                    f"Template is missing word/document.xml: {template_path}"
                ) from exc
    except BadZipFile as exc:
        raise WindDocxWriterError(f"Template is not a valid DOCX zip: {template_path}") from exc
    return xml.decode("utf-8", errors="replace")


def _write_rendered_docx(
    *,
    template_path: Path,
    output_docx_path: Path,
    rendered_xml: str,
    embedded_metadata_xml: bytes,
) -> None:
    xml_bytes = rendered_xml.encode("utf-8")
    metadata_written = False
    try:
        with ZipFile(template_path, "r") as zin, ZipFile(output_docx_path, "w") as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "word/document.xml":
                    data = xml_bytes
                elif info.filename == _EMBEDDED_METADATA_XML_PATH:
                    data = embedded_metadata_xml
                    metadata_written = True
                zout.writestr(info, data)
            if not metadata_written:
                zout.writestr(_EMBEDDED_METADATA_XML_PATH, embedded_metadata_xml)
    except BadZipFile as exc:
        raise WindDocxWriterError(f"Template is not a valid DOCX zip: {template_path}") from exc


def _write_debug_sidecar(
    *,
    debug_json_path: Path,
    report: WindReportBuildResult,
    template_path: Path,
    output_docx_path: Path,
) -> None:
    payload = report.debug_payload.to_dict()
    payload["generation"] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "template_path": str(template_path),
        "output_docx_path": str(output_docx_path),
        "output_docx_name": output_docx_path.name,
    }
    debug_json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _next_collision_safe_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index:02d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _build_embedded_metadata_xml(*, report: WindReportBuildResult, output_docx_path: Path) -> bytes:
    root = ET.Element(
        "purwayWindMetadata",
        {
            "schemaVersion": _EMBEDDED_METADATA_SCHEMA_VERSION,
        },
    )

    generation = ET.SubElement(root, "generation")
    generation.set("generatedAtUtc", datetime.now(timezone.utc).isoformat())
    generation.set("outputDocxName", output_docx_path.name)

    template_placeholders = ET.SubElement(root, "templatePlaceholders")
    for key in sorted(report.debug_payload.placeholder_map):
        entry = ET.SubElement(template_placeholders, "entry", {"key": key})
        entry.text = report.debug_payload.placeholder_map[key]

    component_values = ET.SubElement(root, "componentValues")
    component_map = _build_component_value_map(report)
    for key in sorted(component_map):
        entry = ET.SubElement(component_values, "entry", {"key": key})
        entry.text = component_map[key]

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _build_component_value_map(report: WindReportBuildResult) -> dict[str, str]:
    start = report.debug_payload.normalized_start
    end = report.debug_payload.normalized_end
    return {
        "S_WIND": start.get("wind_direction", ""),
        "S_SPEED": start.get("wind_speed_mph", ""),
        "S_GUST": start.get("gust_mph", ""),
        "S_TEMP": start.get("temp_f", ""),
        "E_WIND": end.get("wind_direction", ""),
        "E_SPEED": end.get("wind_speed_mph", ""),
        "E_GUST": end.get("gust_mph", ""),
        "E_TEMP": end.get("temp_f", ""),
    }


def _placeholder_pattern(key: str) -> re.Pattern[str]:
    return re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}")
