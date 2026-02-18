from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pytest

from purway_geotagger.core.wind_docx import WindReportMetadataRaw, WindRowRaw, build_wind_template_payload
from purway_geotagger.core.wind_docx_writer import (
    WindDocxWriterError,
    generate_wind_docx_report,
)


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


def _build_valid_report():
    metadata = WindReportMetadataRaw(
        client_name="TargaResources",
        system_name="KDB-20",
        report_date="2026-02-06",
        timezone="CST",
        region_id="Region7",
    )
    start = WindRowRaw("10:00", "SW", "0", "1", "51")
    end = WindRowRaw("13:00", "SW", "0", "1", "51")
    return build_wind_template_payload(metadata, start, end)


def _read_document_xml(docx_path: Path) -> str:
    with ZipFile(docx_path, "r") as zf:
        return zf.read("word/document.xml").decode("utf-8", errors="replace")


def _read_visible_text(docx_path: Path) -> str:
    xml = _read_document_xml(docx_path)
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    chunks = [(node.text or "") for node in root.findall(".//w:t", ns)]
    return "".join(chunks)


def _read_embedded_metadata_xml(docx_path: Path) -> str:
    with ZipFile(docx_path, "r") as zf:
        return zf.read("customXml/purway_wind_metadata.xml").decode("utf-8", errors="replace")


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
    assert "{{ REGION_ID }}" not in xml


def test_generate_wind_docx_embeds_metadata_part_with_placeholder_and_component_values(tmp_path: Path) -> None:
    template = _production_template_path()
    assert template.exists(), f"Missing production template: {template}"

    result = generate_wind_docx_report(
        template_path=template,
        output_dir=tmp_path,
        report=_build_valid_report(),
    )

    metadata_xml = _read_embedded_metadata_xml(result.output_docx_path)
    root = ET.fromstring(metadata_xml)

    assert root.tag == "purwayWindMetadata"
    assert root.attrib.get("schemaVersion") == "1"

    generation = root.find("generation")
    assert generation is not None
    assert generation.attrib.get("generatedAtUtc")
    assert generation.attrib.get("outputDocxName") == result.output_docx_path.name

    template_values = {
        entry.attrib["key"]: (entry.text or "")
        for entry in root.findall("./templatePlaceholders/entry")
    }
    assert template_values["CLIENT_NAME"] == "TargaResources"
    assert template_values["DATE"] == "2026_02_06"
    assert template_values["REGION_ID"] == "Region7"
    assert template_values["S_TIME"] == "10:00am"
    assert template_values["E_TIME"] == "1:00pm"
    assert template_values["S_STRING"] == "SW 0 mph / Gusts 1 mph / 51\u00B0F"
    assert template_values["E_STRING"] == "SW 0 mph / Gusts 1 mph / 51\u00B0F"

    component_values = {
        entry.attrib["key"]: (entry.text or "")
        for entry in root.findall("./componentValues/entry")
    }
    assert component_values["S_WIND"] == "SW"
    assert component_values["S_SPEED"] == "0"
    assert component_values["S_GUST"] == "1"
    assert component_values["S_TEMP"] == "51"
    assert component_values["E_WIND"] == "SW"
    assert component_values["E_SPEED"] == "0"
    assert component_values["E_GUST"] == "1"
    assert component_values["E_TEMP"] == "51"


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


def test_generate_wind_docx_escapes_xml_special_characters_in_placeholders(tmp_path: Path) -> None:
    template = _production_template_path()
    assert template.exists(), f"Missing production template: {template}"

    # These characters must be escaped in XML, otherwise Word can't open the resulting DOCX.
    metadata = WindReportMetadataRaw(
        client_name="TargaResources",
        system_name="Katy ROW & Facility <Test>",
        report_date="2026-02-06",
        timezone="CST",
    )
    start = WindRowRaw("10:00", "SW", "0", "1", "51")
    end = WindRowRaw("13:00", "SW", "0", "1", "51")
    report = build_wind_template_payload(metadata, start, end)

    result = generate_wind_docx_report(
        template_path=template,
        output_dir=tmp_path,
        report=report,
    )

    xml = _read_document_xml(result.output_docx_path)
    # Must be well-formed XML.
    ET.fromstring(xml)

    assert "Katy ROW & Facility <Test>" not in xml
    assert "Katy ROW &amp; Facility &lt;Test&gt;" in xml
