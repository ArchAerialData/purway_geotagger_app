from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .utils import resource_path


WindTemplateProfile = Literal["system_only", "region_only", "system_and_region"]

SYSTEM_ONLY_TEMPLATE_REL_PATH = (
    "config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx"
)
REGION_ONLY_TEMPLATE_REL_PATH = (
    "config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx"
)
SYSTEM_REGION_TEMPLATE_REL_PATH = (
    "config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx"
)

_PROFILE_TEMPLATE_PATHS: dict[WindTemplateProfile, str] = {
    "system_only": SYSTEM_ONLY_TEMPLATE_REL_PATH,
    "region_only": REGION_ONLY_TEMPLATE_REL_PATH,
    "system_and_region": SYSTEM_REGION_TEMPLATE_REL_PATH,
}


class WindTemplateSelectionError(ValueError):
    """Raised when a wind template cannot be resolved from input metadata."""


@dataclass(frozen=True)
class WindTemplateSelection:
    profile: WindTemplateProfile
    template_path: Path


def select_wind_template_profile(
    *,
    system_name: str | None,
    region_id: str | None,
) -> WindTemplateProfile:
    has_system = bool((system_name or "").strip())
    has_region = bool((region_id or "").strip())
    if has_system and has_region:
        return "system_and_region"
    if has_system:
        return "system_only"
    if has_region:
        return "region_only"
    raise WindTemplateSelectionError("System ID or Region is required.")


def select_wind_template(
    *,
    system_name: str | None,
    region_id: str | None,
) -> WindTemplateSelection:
    profile = select_wind_template_profile(system_name=system_name, region_id=region_id)
    template_path = resource_path(_PROFILE_TEMPLATE_PATHS[profile])
    if not template_path.exists():
        raise WindTemplateSelectionError(
            "Resolved template path does not exist for profile "
            f"'{profile}': {template_path}"
        )
    return WindTemplateSelection(profile=profile, template_path=template_path)
