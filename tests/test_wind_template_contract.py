from __future__ import annotations

from pathlib import Path
import re
from zipfile import ZipFile

import pytest

from purway_geotagger.core.wind_template_contract import (
    REQUIRED_PLACEHOLDERS,
    WindTemplateContractError,
    inspect_wind_template_contract,
    validate_wind_template_contract,
)


def _production_template_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "wind_data_generator"
        / "Example of Template Structure"
        / "PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx"
    )


def _rewrite_document_xml(src: Path, dst: Path, mutator) -> None:
    with ZipFile(src, "r") as zin, ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == "word/document.xml":
                xml = data.decode("utf-8", errors="replace")
                xml = mutator(xml)
                data = xml.encode("utf-8")
            zout.writestr(info, data)


def test_production_template_contract_passes_strict() -> None:
    template = _production_template_path()
    assert template.exists(), f"Missing production template: {template}"

    report = validate_wind_template_contract(template, allow_extra_placeholders=False)

    assert set(report.found_placeholders) == set(REQUIRED_PLACEHOLDERS)
    assert report.missing_placeholders == ()
    assert report.unexpected_placeholders == ()
    assert report.tz_header_present is True


def test_missing_required_placeholder_raises(tmp_path: Path) -> None:
    src = _production_template_path()
    assert src.exists(), f"Missing production template: {src}"
    dst = tmp_path / "missing_placeholder.docx"

    def _mutate(xml: str) -> str:
        updated, count = re.subn(r"\{\{\s*E_STRING\s*\}\}", "E_STRING_REMOVED", xml, count=1)
        assert count == 1, "Expected {{ E_STRING }} placeholder not found for test mutation."
        return updated

    _rewrite_document_xml(src, dst, _mutate)

    with pytest.raises(WindTemplateContractError, match="Missing required placeholders: E_STRING"):
        validate_wind_template_contract(dst, allow_extra_placeholders=False)


def test_unexpected_placeholder_policy_behavior(tmp_path: Path) -> None:
    src = _production_template_path()
    assert src.exists(), f"Missing production template: {src}"
    dst = tmp_path / "extra_placeholder.docx"

    def _mutate(xml: str) -> str:
        updated, count = re.subn(
            r"\{\{\s*E_STRING\s*\}\}",
            "{{ E_STRING }} {{ EXTRA_TOKEN }}",
            xml,
            count=1,
        )
        assert count == 1, "Expected {{ E_STRING }} placeholder not found for test mutation."
        return updated

    _rewrite_document_xml(src, dst, _mutate)

    # Non-strict mode: extra placeholders are reported but not fatal.
    report = validate_wind_template_contract(dst, allow_extra_placeholders=True)
    assert "EXTRA_TOKEN" in report.unexpected_placeholders

    # Strict mode: extra placeholders are fatal.
    with pytest.raises(WindTemplateContractError, match="Unexpected placeholders present: EXTRA_TOKEN"):
        validate_wind_template_contract(dst, allow_extra_placeholders=False)


def test_tz_header_token_required(tmp_path: Path) -> None:
    src = _production_template_path()
    assert src.exists(), f"Missing production template: {src}"
    dst = tmp_path / "missing_tz_header.docx"

    def _mutate(xml: str) -> str:
        # Keep the TZ placeholder but remove the required "Time ({{ TZ }})" wrapper.
        updated, count = re.subn(r"\(\s*\{\{\s*TZ\s*\}\}\s*\)", "{{ TZ }}", xml, count=1)
        assert count == 1, "Expected TZ header token pattern not found for test mutation."
        return updated

    _rewrite_document_xml(src, dst, _mutate)

    report = inspect_wind_template_contract(dst)
    assert "TZ" in report.found_placeholders
    assert report.tz_header_present is False

    with pytest.raises(WindTemplateContractError, match=r"Missing required header token: Time \(\{\{ TZ \}\}\)"):
        validate_wind_template_contract(dst, require_tz_header=True)
