from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
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
    _write_rendered_docx(template_path, output_docx_path, rendered_xml)

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


def _write_rendered_docx(template_path: Path, output_docx_path: Path, rendered_xml: str) -> None:
    xml_bytes = rendered_xml.encode("utf-8")
    try:
        with ZipFile(template_path, "r") as zin, ZipFile(output_docx_path, "w") as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "word/document.xml":
                    data = xml_bytes
                zout.writestr(info, data)
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


def _placeholder_pattern(key: str) -> re.Pattern[str]:
    return re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}")
