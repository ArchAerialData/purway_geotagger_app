from __future__ import annotations

from pathlib import Path
import re
from zipfile import ZipFile

import pytest

from purway_geotagger.core.wind_template_contract import (
    REQUIRED_PLACEHOLDERS,
    WindTemplateContractError,
    inspect_wind_template_contract,
    required_placeholders_for_profile,
    validate_wind_template_contract,
)
from purway_geotagger.core.wind_template_selector import (
    REGION_ONLY_TEMPLATE_REL_PATH,
    SYSTEM_ONLY_TEMPLATE_REL_PATH,
    SYSTEM_REGION_TEMPLATE_REL_PATH,
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _template_by_relative_path(relative_path: str) -> Path:
    return _repo_root() / Path(relative_path)


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

    assert set(REQUIRED_PLACEHOLDERS).issubset(set(report.found_placeholders))
    assert report.missing_placeholders == ()
    assert report.unexpected_placeholders == ()
    assert report.tz_header_present is True


@pytest.mark.parametrize(
    ("profile", "relative_path"),
    (
        ("system_only", SYSTEM_ONLY_TEMPLATE_REL_PATH),
        ("region_only", REGION_ONLY_TEMPLATE_REL_PATH),
        ("system_and_region", SYSTEM_REGION_TEMPLATE_REL_PATH),
    ),
)
def test_wr3a_template_contract_passes_for_each_profile(profile: str, relative_path: str) -> None:
    template = _template_by_relative_path(relative_path)
    assert template.exists(), f"Missing WR3A template: {template}"

    required = required_placeholders_for_profile(profile)
    report = validate_wind_template_contract(
        template,
        allow_extra_placeholders=False,
        required_placeholders=required,
    )
    assert set(required).issubset(set(report.found_placeholders))
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
