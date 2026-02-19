# Wind Data Region Field Update - Phased Implementation Plan (Hard Gates)

Date created: 2026-02-18
Status: Planning only. No app behavior changes in this document.

This document defines the phased implementation plan for adding an optional `Region` input to the Wind Data GUI and wiring it to DOCX/template metadata as `{{ REGION_ID }}`.

Decision update (confirmed 2026-02-18):
- Auto-selected multi-template UX is approved:
  - `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
  - `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
  - `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
- System placeholders remain unchanged (existing system placeholder contract is preserved).
- Region placeholder for this track is `{{ REGION_ID }}`.
- No additional template-selection controls are added to the primary pilot UI; template choice is automatic from field state.

Reviewed wind-data GUI planning/docs context:
- `README.md` (Wind Data section)
- `WIND_DATA_DOCX_FEATURE_PLAN.md`
- `WIND_DATA_IMPLEMENTATION_PHASES.md`
- `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md`
- `WIND_DATA_ZIP_AUTOFILL_RESOURCE_MAP.md`
- `WIND_DATA_CHANGESET_NOTES.md`
- `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (W-series track)

## Execution Rules (Mandatory)

- Do not start a new phase until all tasks, tests, and gate criteria for the current phase are complete.
- Keep macOS-first behavior for packaging/runtime, while preserving Windows dev/runtime compatibility.
- Keep long-running work off the UI thread.
- Keep Wind placeholder/templating logic in `src/purway_geotagger/core/`.
- Keep Wind page/field wiring in `src/purway_geotagger/gui/`.
- Region field contract is locked for this track:
  - GUI label: `Region`
  - Placeholder token: `{{ REGION_ID }}`
  - Backend metadata key: `REGION_ID`
  - Behavior: optional (blank input is valid and maps to empty replacement text)
- `Region` must be displayed in Report Info next to the System field.
- If a template contains `{{ REGION_ID }}`, it must be replaced.
- If a template does not contain `{{ REGION_ID }}`, generation must still succeed.
- At the end of each phase, update:
  - `WIND_DATA_REGION_FIELD_IMPLEMENTATION_PHASES.md` (phase notes)
  - `WIND_DATA_IMPLEMENTATION_PHASES.md` (cross-link/summary note)
  - `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (W-track note)

---

## Phase WR0 - Contract Lock + Template Inventory

### Goal

Freeze naming, optional behavior, and template ownership for Region before code changes.

### Work items

- [x] Confirm final naming:
  - GUI field: `Region`
  - Placeholder: `REGION_ID`
  - Internal metadata key: `region_id` (Python), exported placeholder key `REGION_ID`.
- [x] Confirm whether System field label should remain `System Name` or be relabeled `System ID` in Wind GUI.
- [x] Confirm canonical production template file(s) to update for both Windows and macOS usage.
- [x] Document whether one shared template is used cross-platform or separate source templates are maintained.

### Files (new)

- [x] `WIND_DATA_REGION_FIELD_IMPLEMENTATION_PHASES.md` (this file)

### Files (modify)

- [x] `WIND_DATA_DOCX_FEATURE_PLAN.md` (contract section update for `REGION_ID` optional token)
- [x] `README.md` (Wind placeholder contract update)
- [x] `WIND_DATA_IMPLEMENTATION_PHASES.md` (WR3A summary alignment)
- [x] `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (WR tracking alignment)

### Tests / verification (required before next phase)

- [x] Manual contract review in docs:
  - verify `REGION_ID` language is consistent across all wind docs listed above.

### Gate

- [x] Region naming/contract is documented and approved.
- [x] Template ownership for Windows/macOS is explicitly documented.

### Phase Notes

- Date completed: 2026-02-18
- Verification run:
  - `python` placeholder inventory script against `config/wind_templates/**/*.docx` confirmed:
    - System-only template contains `SYSTEM_NAME` and omits `REGION_ID`.
    - Region-only template contains `REGION_ID` and omits `SYSTEM_NAME`.
    - System+Region template contains both `SYSTEM_NAME` and `REGION_ID`.
  - Markdown alignment check updated:
    - `README.md`
    - `WIND_DATA_DOCX_FEATURE_PLAN.md`
    - `WIND_DATA_IMPLEMENTATION_PHASES.md`
    - `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`
- Deviations:
  - Canonical WR3A template filenames are foldered production paths, not short names (`System.docx`, `Region.docx`, `System-Region.docx`).

---

## Phase WR1 - Core Payload + Validation + Metadata Wiring

### Goal

Extend Wind payload models to carry optional Region and emit `REGION_ID` in placeholder/debug metadata.

### Work items

- [x] Extend metadata input model with optional region value:
  - `WindReportMetadataRaw` adds `region_id` (optional text).
- [x] Extend normalized payload:
  - `WindTemplatePayload` adds `region_id`.
  - `as_placeholder_map()` includes `REGION_ID`.
- [x] Keep Region optional:
  - empty/whitespace input should normalize to empty string.
  - no required-field validation error for missing Region.
- [x] Include region in debug payload maps:
  - `raw_metadata.region_id`
  - `normalized_metadata.region_id`
- [x] Keep output filename contract unchanged:
  - `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`

### Files (new)

- [ ] `tests/test_wind_region_field.py` (optional dedicated tests if updates are not kept in existing test files)

### Files (modify)

- [x] `src/purway_geotagger/core/wind_docx.py`
- [x] `tests/test_wind_validation.py`
- [x] `tests/test_wind_debug_export.py`

### Tests / verification (required before next phase)

- [x] `python -m pytest tests/test_wind_validation.py`
- [x] `python -m pytest tests/test_wind_debug_export.py`
- [x] `python -m compileall src`

### Gate

- [x] Payload/debug metadata include `REGION_ID` when provided.
- [x] Blank Region remains valid and does not block generation.

### Phase Notes

- Date completed: 2026-02-18
- Verification run:
  - `python -m pytest tests/test_wind_validation.py tests/test_wind_debug_export.py` (pass)
  - `python -m compileall src` (pass)
- Deviations:
  - WR1 scope retained existing output filename contract (`WindData_<ClientNoSpaces>_<YYYY_MM_DD>.docx`).

---

## Phase WR2 - Template Contract + DOCX Render + Embedded Metadata

### Goal

Allow and replace `{{ REGION_ID }}` in DOCX templates while preserving strict validation behavior.

### Work items

- [x] Update wind template contract policy to support optional placeholder token:
  - allowed placeholder set includes `REGION_ID`
  - required placeholder set remains existing required tokens.
- [x] Ensure DOCX rendering replaces `{{ REGION_ID }}` using payload placeholder map.
- [x] Ensure unresolved `{{ REGION_ID }}` does not remain in rendered DOCX when token exists in template.
- [x] Ensure embedded metadata part includes `REGION_ID` in `templatePlaceholders` map.
- [x] Update bundled production template to add a visible Region row/slot near system metadata.
- [ ] If a secondary source template is maintained for another OS, sync the same placeholder update there.

### Files (new)

- [ ] `config/wind_templates/REGION_FIELD_CHANGELOG.md` (optional audit note for template versioning)
- [ ] `wind_data_generator/templates/macos/` (optional, only if separate source templates are introduced)
- [ ] `wind_data_generator/templates/windows/` (optional, only if separate source templates are introduced)

### Files (modify)

- [x] `src/purway_geotagger/core/wind_template_contract.py`
- [x] `src/purway_geotagger/core/wind_docx_writer.py`
- [x] `tests/test_wind_template_contract.py`
- [x] `tests/test_wind_docx_writer.py`
- [x] `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
- [x] `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
- [x] `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
- [ ] `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx` (if present in active template workflow)

### Tests / verification (required before next phase)

- [x] `python -m pytest tests/test_wind_template_contract.py`
- [x] `python -m pytest tests/test_wind_docx_writer.py`
- [x] `python -m pytest tests/test_wind_debug_export.py`
- [x] `python -m compileall src`

### Gate

- [x] Strict contract validation passes for approved production template(s).
- [x] Generated DOCX has no unresolved `{{ REGION_ID }}` token when template includes it.
- [x] Embedded metadata/custom XML includes `REGION_ID` value for downstream XMP-compatible consumers.

### Phase Notes

- Date completed: 2026-02-18
- Verification run:
  - `python -m pytest tests/test_wind_template_contract.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py` (pass)
  - `python -m compileall src` (pass)
- Deviations:
  - `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx` was not modified in this phase (not used by WR3A runtime selector).

---

## Phase WR3 - Wind GUI Report Info Update (System + Region)

### Goal

Add the optional Region field to Wind Data GUI and wire it into payload generation.

### Work items

- [x] Add Region input control in Report Info card beside the System field.
- [x] Keep Region field optional:
  - no validation error when blank.
- [x] If approved in WR0, relabel System field to `System ID` (or keep `System Name` if not approved).
- [x] Include region value in `_build_metadata()` when building `WindReportMetadataRaw`.
- [x] Keep Generate button enablement behavior unchanged except for Region passthrough support.
- [x] Verify preview/generation still functions without region input.

### Files (new)

- [ ] `tests/test_wind_page_region_behavior.py` (optional dedicated GUI logic tests)

### Files (modify)

- [x] `src/purway_geotagger/gui/pages/wind_data_page.py`
- [x] `src/purway_geotagger/gui/pages/wind_data_logic.py` (if generate gating text or helpers change)
- [ ] `src/purway_geotagger/gui/style_sheet.py` (only if spacing/alignment tweaks are needed)
- [x] `tests/test_wind_page_logic.py`
- [x] `tests/test_wind_page_preview_behavior.py`

### Tests / verification (required before next phase)

- [x] `python -m pytest tests/test_wind_page_logic.py`
- [x] `python -m pytest tests/test_wind_page_preview_behavior.py`
- [x] `python -m compileall src`
- [x] Manual GUI smoke:
  - [x] Region is visible beside system field.
  - [x] Region blank -> generation succeeds.
  - [x] Region filled -> output/docx metadata contains expected value.

### Gate

- [x] Pilot can generate wind DOCX with or without Region field input.
- [x] Region value from GUI is mapped to `REGION_ID` consistently.

### Phase Notes

- Date completed: 2026-02-18
- Verification run:
  - `python -m pytest tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py` (pass)
  - `python -m compileall src` (pass)
- Deviations:
  - GUI validation used offscreen regression harness in this environment; packaged-app click-through remains part of WR4 cross-OS release checks.

---

## Phase WR3A - Multi-Template Selector (System Only / Region Only / Both)

### Goal

Support three production template variants and automatically select the correct template based on optional `System ID` and `Region` inputs.

### Work items

- [x] Make `System ID` optional in Wind core validation (same blank-safe behavior as Region).
- [x] Add cross-field validation rule:
  - require at least one of `system_id` or `region_id` before generation.
  - allow both fields together.
- [x] Add template profile model and selector helper:
  - `system_only`
  - `region_only`
  - `system_and_region`
- [x] Add deterministic auto-selection logic:
  - only system populated -> `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
  - only region populated -> `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
  - both populated -> `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
- [x] Add three production templates under bundled config path.
- [x] Update template contract validation for profile-aware placeholder enforcement.
- [x] Keep output filename contract unchanged:
  - `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`
- [x] Keep debug/custom XML metadata maps stable for downstream extraction:
  - always include `SYSTEM_NAME` and `REGION_ID` keys with blank-safe values.

### Filename Token Mapping (Locked)

- System-only template filename: `WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
  - `ClientName` -> filename-safe client value from GUI.
  - `SYSTEM` -> filename-safe system value from GUI.
  - `YYYY_MM_DD` -> normalized report date.
- Region-only template filename: `WindData_ClientName_Region_YYYY_MM_DD.docx`
  - `ClientName` -> filename-safe client value from GUI.
  - `Region` -> filename-safe region value from GUI.
  - `YYYY_MM_DD` -> normalized report date.
- System+Region template filename: `WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
  - `ClientName` -> filename-safe client value from GUI.
  - `REGION` -> filename-safe region value from GUI.
  - `SYSTEM` -> filename-safe system value from GUI.
  - `YYYY_MM_DD` -> normalized report date.

### Files (new)

- [x] `src/purway_geotagger/core/wind_template_selector.py`
- [x] `tests/test_wind_template_selector.py`
- [x] `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
- [x] `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
- [x] `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`

### Files (modify)

- [x] `src/purway_geotagger/core/wind_docx.py`
- [x] `src/purway_geotagger/core/wind_template_contract.py`
- [x] `src/purway_geotagger/core/wind_docx_writer.py`
- [x] `src/purway_geotagger/gui/pages/wind_data_logic.py`
- [x] `src/purway_geotagger/gui/pages/wind_data_page.py`
- [x] `tests/test_wind_validation.py`
- [x] `tests/test_wind_template_contract.py`
- [x] `tests/test_wind_docx_writer.py`
- [x] `README.md`

### Tests / verification (required before next phase)

- [x] `python -m pytest tests/test_wind_template_selector.py`
- [x] `python -m pytest tests/test_wind_validation.py`
- [x] `python -m pytest tests/test_wind_template_contract.py`
- [x] `python -m pytest tests/test_wind_docx_writer.py tests/test_wind_debug_export.py`
- [x] `python -m compileall src`
- [ ] Manual GUI smoke:
  - [ ] System-only input auto-selects `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx` and generates DOCX.
  - [ ] Region-only input auto-selects `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx` and generates DOCX.
  - [ ] Both inputs auto-select `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx` and generate DOCX.
  - [ ] Both blank fails with clear pilot-facing message.

### Gate

- [x] Auto-selector chooses the correct template file path for all 3 input scenarios:
  - `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
  - `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
  - `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
- [ ] DOCX generation succeeds for all 3 scenarios in both Windows and macOS dev runs.
- [x] Cross-field validation blocks blank/blank (`System ID` + `Region`) with explicit error text.

### Phase Notes

- Date completed: 2026-02-18 (code + automated tests)
- Verification run:
  - `python -m pytest tests/test_wind_template_selector.py tests/test_wind_validation.py tests/test_wind_template_contract.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py` (51 passed)
  - `python -m compileall src` (pass)
- Deviations:
  - Remaining WR3A gate items are manual UI smoke and explicit macOS dev-run verification.

---

## Phase WR4 - Windows + macOS Validation, Packaging, and Documentation

### Goal

Confirm the Region update works consistently in both Windows and macOS workflows and is fully documented.

### Work items

- [ ] Update wind feature docs with Region contract and optional behavior.
- [ ] Validate dev test scripts on both OS tracks.
- [ ] Validate generated DOCX output from both OS runs uses the same Region placeholder behavior.
- [ ] Record release/readiness notes for this change.

### Files (new)

- [ ] `WIND_DATA_REGION_FIELD_CHANGESET_NOTES.md` (optional rollback/change block notes)

### Files (modify)

- [ ] `README.md`
- [ ] `WIND_DATA_DOCX_FEATURE_PLAN.md`
- [ ] `WIND_DATA_IMPLEMENTATION_PHASES.md`
- [ ] `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`
- [ ] `RELEASE_READINESS_OPEN_ITEMS.md` (if new release gate items are needed)
- [ ] `scripts/macos/README.md` (only if runbook text needs wind-field update)
- [ ] `scripts/windows/setup_windows.ps1` (only if setup/help text references wind placeholder set)

### Tests / verification (required before completion)

- [ ] Targeted wind regressions:
  - `python -m pytest tests/test_wind_template_contract.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py`
- [ ] Windows dev script run:
  - `powershell -ExecutionPolicy Bypass -File scripts/windows/run_tests.ps1`
- [ ] macOS dev script run:
  - `bash scripts/macos/run_tests.sh`
- [ ] Manual output verification on both OS:
  - [ ] generated DOCX opens and shows Region value replacement when provided.
  - [ ] generated DOCX opens and leaves Region blank (no token text) when omitted.

### Gate

- [ ] Region behavior is validated on both Windows and macOS workflows.
- [ ] Docs and phase notes are updated with exact verification commands and dates.

### Phase Notes

- Date completed:
- Verification run:
- Deviations:

---

## Open Decisions Before WR1 Coding

- [x] Wind GUI label decision: use `System ID` label in Report Info (completed in current implementation track).
- [x] Canonical naming for template variants is locked:
  - `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
  - `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
  - `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
- [x] Manual template override UX decision:
  - keep manual template selection out of primary pilot flow to avoid UI clutter.
  - optional support-only override can remain internal/non-default if needed.
- [ ] Confirm scope boundary: keep this behavior Wind-only, or propagate System/Region metadata to non-Wind EXIF/XMP tracks.

---

## Summary of Planned File Paths

### New files/folders (planned)

- `WIND_DATA_REGION_FIELD_IMPLEMENTATION_PHASES.md`
- `tests/test_wind_region_field.py` (optional)
- `tests/test_wind_page_region_behavior.py` (optional)
- `src/purway_geotagger/core/wind_template_selector.py`
- `tests/test_wind_template_selector.py`
- `WIND_DATA_REGION_FIELD_CHANGESET_NOTES.md` (optional)
- `config/wind_templates/REGION_FIELD_CHANGELOG.md` (optional)
- `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
- `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
- `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
- `wind_data_generator/templates/macos/` (optional)
- `wind_data_generator/templates/windows/` (optional)

### Existing files (planned modifications)

- `src/purway_geotagger/core/wind_docx.py`
- `src/purway_geotagger/core/wind_template_selector.py` (created in WR3A)
- `src/purway_geotagger/core/wind_template_contract.py`
- `src/purway_geotagger/core/wind_docx_writer.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/pages/wind_data_logic.py`
- `src/purway_geotagger/gui/style_sheet.py`
- `tests/test_wind_validation.py`
- `tests/test_wind_debug_export.py`
- `tests/test_wind_template_contract.py`
- `tests/test_wind_docx_writer.py`
- `tests/test_wind_page_logic.py`
- `tests/test_wind_page_preview_behavior.py`
- `config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx` (if present/active)
- `README.md`
- `WIND_DATA_DOCX_FEATURE_PLAN.md`
- `WIND_DATA_IMPLEMENTATION_PHASES.md`
- `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`
- `RELEASE_READINESS_OPEN_ITEMS.md`
