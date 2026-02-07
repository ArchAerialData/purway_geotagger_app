from __future__ import annotations

from pathlib import Path
import re
from zipfile import ZipFile

import pytest

from purway_geotagger.core.wind_docx import WindReportMetadataRaw, WindRowRaw, build_wind_template_payload
from purway_geotagger.core.wind_docx_writer import (
    WindDocxWriterError,
    generate_wind_docx_report,
)


def _production_template_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "wind_data_generator"
        / "Example of Template Structure"
        / "PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx"
    )


def _build_valid_report():
    metadata = WindReportMetadataRaw(
        client_name="TargaResources",
        system_name="KDB-20",
        report_date="2026-02-06",
        timezone="CST",
    )
    start = WindRowRaw("10:00", "SW", "0", "1", "51")
    end = WindRowRaw("13:00", "SW", "0", "1", "51")
    return build_wind_template_payload(metadata, start, end)


def _read_document_xml(docx_path: Path) -> str:
    with ZipFile(docx_path, "r") as zf:
        return zf.read("word/document.xml").decode("utf-8", errors="replace")


def _read_visible_text(docx_path: Path) -> str:
    xml = _read_document_xml(docx_path)
    chunks = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml)
    return "".join(chunks)


def _rewrite_document_xml(src: Path, dst: Path, mutator) -> None:
    with ZipFile(src, "r") as zin, ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == "word/document.xml":
                xml = data.decode("utf-8", errors="replace")
                xml = mutator(xml)
                data = xml.encode("utf-8")
            zout.writestr(info, data)


def test_generate_wind_docx_replaces_placeholders(tmp_path: Path) -> None:
    template = _production_template_path()
    assert template.exists(), f"Missing production template: {template}"

    result = generate_wind_docx_report(
        template_path=template,
        output_dir=tmp_path,
        report=_build_valid_report(),
    )

    assert result.output_docx_path.exists()
    assert result.debug_json_path.exists()

    xml = _read_document_xml(result.output_docx_path)
    visible_text = _read_visible_text(result.output_docx_path)
    assert "Time (CST)" in visible_text
    assert "10:00am" in visible_text
    assert "1:00pm" in visible_text
    assert "SW 0 mph / Gusts 1 mph / 51\u00B0F" in visible_text
    assert "{{ S_STRING }}" not in xml
    assert "{{ E_STRING }}" not in xml
    assert "{{ TZ }}" not in xml


def test_generate_wind_docx_is_collision_safe(tmp_path: Path) -> None:
    template = _production_template_path()
    assert template.exists(), f"Missing production template: {template}"
    report = _build_valid_report()
    fixed_name = "WindData_TargaResources_2026_02_06.docx"

    first = generate_wind_docx_report(
        template_path=template,
        output_dir=tmp_path,
        report=report,
        output_filename=fixed_name,
    )
    second = generate_wind_docx_report(
        template_path=template,
        output_dir=tmp_path,
        report=report,
        output_filename=fixed_name,
    )

    assert first.output_docx_path.name == fixed_name
    assert second.output_docx_path.name == "WindData_TargaResources_2026_02_06_01.docx"


def test_template_contract_failure_blocks_write(tmp_path: Path) -> None:
    src = _production_template_path()
    assert src.exists(), f"Missing production template: {src}"
    bad_template = tmp_path / "bad_template.docx"

    def _mutate(xml: str) -> str:
        updated, count = re.subn(r"\{\{\s*E_STRING\s*\}\}", "E_STRING_REMOVED", xml, count=1)
        assert count == 1, "Expected {{ E_STRING }} placeholder not found for test mutation."
        return updated

    _rewrite_document_xml(src, bad_template, _mutate)

    with pytest.raises(WindDocxWriterError, match="Template contract validation failed"):
        generate_wind_docx_report(
            template_path=bad_template,
            output_dir=tmp_path / "output",
            report=_build_valid_report(),
        )
