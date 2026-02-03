from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable

from purway_geotagger.core.modes import RunMode, default_methane_log_base, default_encroachment_base


@dataclass(frozen=True)
class ValidationIssue:
    field_id: str
    message: str


@dataclass
class ModeState:
    mode: RunMode = RunMode.METHANE
    inputs: list[Path] = field(default_factory=list)

    methane_threshold: int = 1000
    methane_generate_kmz: bool = False
    methane_log_base: Path | None = None

    encroachment_output_base: Path | None = None
    encroachment_rename_enabled: bool = False
    encroachment_template_id: str | None = None
    encroachment_client_abbr: str = ""
    encroachment_start_index: int = 1

    def resolved(self) -> "ModeState":
        base = default_methane_log_base(self.inputs) if self.methane_log_base is None else self.methane_log_base
        enc_base = (
            default_encroachment_base(self.inputs)
            if self.encroachment_output_base is None
            else self.encroachment_output_base
        )
        return replace(
            self,
            methane_log_base=base,
            encroachment_output_base=enc_base,
        )


def validate_mode_state(state: ModeState) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not state.inputs:
        issues.append(ValidationIssue("inputs", "Input folder(s) required."))

    if state.methane_threshold < 1:
        issues.append(ValidationIssue("methane_threshold", "PPM threshold must be 1 or greater."))

    if state.mode in (RunMode.ENCROACHMENT, RunMode.COMBINED):
        if not state.encroachment_output_base:
            issues.append(ValidationIssue("encroachment_output_base", "Output folder required."))

        if state.encroachment_rename_enabled:
            if state.encroachment_template_id:
                pass
            else:
                if not state.encroachment_client_abbr.strip():
                    issues.append(ValidationIssue("encroachment_client_abbr", "Client Abbreviation required."))
            if state.encroachment_start_index < 1:
                issues.append(ValidationIssue("encroachment_start_index", "Start Index must be 1 or greater."))

    return issues


def first_issue(issues: Iterable[ValidationIssue]) -> ValidationIssue | None:
    for issue in issues:
        return issue
    return None
