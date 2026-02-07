from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile


REQUIRED_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "CLIENT_NAME",
        "SYSTEM_NAME",
        "DATE",
        "S_TIME",
        "E_TIME",
        "S_STRING",
        "E_STRING",
        "TZ",
    }
)

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
_TZ_HEADER_RE = re.compile(r"\bTime\s*\(\s*\{\{\s*TZ\s*\}\}\s*\)")
_W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


class WindTemplateContractError(ValueError):
    """Raised when the wind DOCX template violates the required contract."""


@dataclass(frozen=True)
class WindTemplateContractReport:
    template_path: Path
    found_placeholders: tuple[str, ...]
    missing_placeholders: tuple[str, ...]
    unexpected_placeholders: tuple[str, ...]
    tz_header_present: bool


def _read_document_xml(template_path: Path) -> str:
    if not template_path.exists():
        raise WindTemplateContractError(f"Template not found: {template_path}")
    try:
        with ZipFile(template_path) as zf:
            try:
                data = zf.read("word/document.xml")
            except KeyError as exc:
                raise WindTemplateContractError(
                    f"Missing word/document.xml in template: {template_path}"
                ) from exc
    except BadZipFile as exc:
        raise WindTemplateContractError(f"Invalid DOCX archive: {template_path}") from exc
    return data.decode("utf-8", errors="replace")


def _extract_placeholders(document_xml: str) -> set[str]:
    return {name.upper() for name in _PLACEHOLDER_RE.findall(document_xml)}


def _extract_table_cells(document_xml: str) -> list[str]:
    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError:
        # Parse failures should be handled by caller as contract error.
        return []
    cells: list[str] = []
    for tc in root.findall(".//w:tc", _W_NS):
        texts = [t.text or "" for t in tc.findall(".//w:t", _W_NS)]
        cells.append("".join(texts).strip())
    return cells


def inspect_wind_template_contract(template_path: Path) -> WindTemplateContractReport:
    document_xml = _read_document_xml(template_path)
    placeholders = _extract_placeholders(document_xml)
    missing = tuple(sorted(REQUIRED_PLACEHOLDERS - placeholders))
    unexpected = tuple(sorted(placeholders - REQUIRED_PLACEHOLDERS))

    cells = _extract_table_cells(document_xml)
    tz_header_present = any(_TZ_HEADER_RE.search(cell) for cell in cells)

    # Fallback check in case table parsing fails but XML is still usable.
    if not cells and _TZ_HEADER_RE.search(document_xml):
        tz_header_present = True

    return WindTemplateContractReport(
        template_path=template_path,
        found_placeholders=tuple(sorted(placeholders)),
        missing_placeholders=missing,
        unexpected_placeholders=unexpected,
        tz_header_present=tz_header_present,
    )


def validate_wind_template_contract(
    template_path: Path,
    *,
    allow_extra_placeholders: bool = True,
    require_tz_header: bool = True,
) -> WindTemplateContractReport:
    report = inspect_wind_template_contract(template_path)
    errors: list[str] = []

    if report.missing_placeholders:
        errors.append(
            "Missing required placeholders: "
            + ", ".join(report.missing_placeholders)
        )
    if require_tz_header and not report.tz_header_present:
        errors.append("Missing required header token: Time ({{ TZ }})")
    if not allow_extra_placeholders and report.unexpected_placeholders:
        errors.append(
            "Unexpected placeholders present: "
            + ", ".join(report.unexpected_placeholders)
        )

    if errors:
        raise WindTemplateContractError("; ".join(errors))
    return report

