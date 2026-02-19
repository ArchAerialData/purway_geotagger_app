from __future__ import annotations

from pathlib import Path

import pytest

from purway_geotagger.core.wind_template_selector import (
    REGION_ONLY_TEMPLATE_REL_PATH,
    SYSTEM_ONLY_TEMPLATE_REL_PATH,
    SYSTEM_REGION_TEMPLATE_REL_PATH,
    WindTemplateSelectionError,
    select_wind_template,
    select_wind_template_profile,
)


@pytest.mark.parametrize(
    ("system_name", "region_id", "expected_profile"),
    (
        ("System-1", "", "system_only"),
        ("", "Region-7", "region_only"),
        ("System-1", "Region-7", "system_and_region"),
    ),
)
def test_select_wind_template_profile(system_name: str, region_id: str, expected_profile: str) -> None:
    profile = select_wind_template_profile(system_name=system_name, region_id=region_id)
    assert profile == expected_profile


def test_select_wind_template_profile_rejects_blank_blank() -> None:
    with pytest.raises(WindTemplateSelectionError, match="System ID or Region is required"):
        select_wind_template_profile(system_name="  ", region_id=" ")


@pytest.mark.parametrize(
    ("system_name", "region_id", "expected_suffix"),
    (
        ("System-1", "", Path(SYSTEM_ONLY_TEMPLATE_REL_PATH)),
        ("", "Region-7", Path(REGION_ONLY_TEMPLATE_REL_PATH)),
        ("System-1", "Region-7", Path(SYSTEM_REGION_TEMPLATE_REL_PATH)),
    ),
)
def test_select_wind_template_resolves_existing_profile_path(
    system_name: str,
    region_id: str,
    expected_suffix: Path,
) -> None:
    selection = select_wind_template(system_name=system_name, region_id=region_id)
    assert selection.template_path.exists(), f"Expected template to exist: {selection.template_path}"
    assert selection.template_path.as_posix().endswith(expected_suffix.as_posix())
