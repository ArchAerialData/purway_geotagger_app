# Wind Data Region Field Update - Phased Implementation Plan (Hard Gates)

Date created: 2026-02-18
Status: Planning only. No app behavior changes in this document.

This document defines the phased implementation plan for adding an optional `Region` input to the Wind Data GUI and wiring it to DOCX/template metadata as `{{ REGION_ID }}`.

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

- [ ] Confirm final naming:
  - GUI field: `Region`
  - Placeholder: `REGION_ID`
  - Internal metadata key: `region_id` (Python), exported placeholder key `REGION_ID`.
- [ ] Confirm whether System field label should remain `System Name` or be relabeled `System ID` in Wind GUI.
- [ ] Confirm canonical production template file(s) to update for both Windows and macOS usage.
- [ ] Document whether one shared template is used cross-platform or separate source templates are maintained.

### Files (new)

- [x] `WIND_DATA_REGION_FIELD_IMPLEMENTATION_PHASES.md` (this file)

### Files (modify)

- [ ] `WIND_DATA_DOCX_FEATURE_PLAN.md` (contract section update for `REGION_ID` optional token)
- [ ] `README.md` (Wind placeholder contract update)

### Tests / verification (required before next phase)

- [ ] Manual contract review in docs:
  - verify `REGION_ID` language is consistent across all wind docs listed above.

### Gate

- [ ] Region naming/contract is documented and approved.
- [ ] Template ownership for Windows/macOS is explicitly documented.

### Phase Notes

- Date completed:
- Verification run:
- Deviations:

---

## Phase WR1 - Core Payload + Validation + Metadata Wiring

### Goal

Extend Wind payload models to carry optional Region and emit `REGION_ID` in placeholder/debug metadata.

### Work items

- [ ] Extend metadata input model with optional region value:
  - `WindReportMetadataRaw` adds `region_id` (optional text).
- [ ] Extend normalized payload:
  - `WindTemplatePayload` adds `region_id`.
  - `as_placeholder_map()` includes `REGION_ID`.
- [ ] Keep Region optional:
  - empty/whitespace input should normalize to empty string.
  - no required-field validation error for missing Region.
- [ ] Include region in debug payload maps:
  - `raw_metadata.region_id`
  - `normalized_metadata.region_id`
- [ ] Keep output filename contract unchanged:
  - `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`

### Files (new)

- [ ] `tests/test_wind_region_field.py` (optional dedicated tests if updates are not kept in existing test files)

### Files (modify)

- [ ] `src/purway_geotagger/core/wind_docx.py`
- [ ] `tests/test_wind_validation.py`
- [ ] `tests/test_wind_debug_export.py`

### Tests / verification (required before next phase)

- [ ] `python -m pytest tests/test_wind_validation.py`
- [ ] `python -m pytest tests/test_wind_debug_export.py`
- [ ] `python -m compileall src`

### Gate

- [ ] Payload/debug metadata include `REGION_ID` when provided.
- [ ] Blank Region remains valid and does not block generation.

### Phase Notes

- Date completed:
- Verification run:
- Deviations:

---

## Phase WR2 - Template Contract + DOCX Render + Embedded Metadata

### Goal

Allow and replace `{{ REGION_ID }}` in DOCX templates while preserving strict validation behavior.

### Work items

- [ ] Update wind template contract policy to support optional placeholder token:
  - allowed placeholder set includes `REGION_ID`
  - required placeholder set remains existing required tokens.
- [ ] Ensure DOCX rendering replaces `{{ REGION_ID }}` using payload placeholder map.
- [ ] Ensure unresolved `{{ REGION_ID }}` does not remain in rendered DOCX when token exists in template.
- [ ] Ensure embedded metadata part includes `REGION_ID` in `templatePlaceholders` map.
- [ ] Update bundled production template to add a visible Region row/slot near system metadata.
- [ ] If a secondary source template is maintained for another OS, sync the same placeholder update there.

### Files (new)

- [ ] `config/wind_templates/REGION_FIELD_CHANGELOG.md` (optional audit note for template versioning)
- [ ] `wind_data_generator/templates/macos/` (optional, only if separate source templates are introduced)
- [ ] `wind_data_generator/templates/windows/` (optional, only if separate source templates are introduced)

### Files (modify)

- [ ] `src/purway_geotagger/core/wind_template_contract.py`
- [ ] `src/purway_geotagger/core/wind_docx_writer.py`
- [ ] `tests/test_wind_template_contract.py`
- [ ] `tests/test_wind_docx_writer.py`
- [ ] `config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- [ ] `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx` (if present in active template workflow)

### Tests / verification (required before next phase)

- [ ] `python -m pytest tests/test_wind_template_contract.py`
- [ ] `python -m pytest tests/test_wind_docx_writer.py`
- [ ] `python -m pytest tests/test_wind_debug_export.py`
- [ ] `python -m compileall src`

### Gate

- [ ] Strict contract validation passes for approved production template(s).
- [ ] Generated DOCX has no unresolved `{{ REGION_ID }}` token when template includes it.
- [ ] Embedded metadata/custom XML includes `REGION_ID` value for downstream XMP-compatible consumers.

### Phase Notes

- Date completed:
- Verification run:
- Deviations:

---

## Phase WR3 - Wind GUI Report Info Update (System + Region)

### Goal

Add the optional Region field to Wind Data GUI and wire it into payload generation.

### Work items

- [ ] Add Region input control in Report Info card beside the System field.
- [ ] Keep Region field optional:
  - no validation error when blank.
- [ ] If approved in WR0, relabel System field to `System ID` (or keep `System Name` if not approved).
- [ ] Include region value in `_build_metadata()` when building `WindReportMetadataRaw`.
- [ ] Keep Generate button enablement behavior unchanged except for Region passthrough support.
- [ ] Verify preview/generation still functions without region input.

### Files (new)

- [ ] `tests/test_wind_page_region_behavior.py` (optional dedicated GUI logic tests)

### Files (modify)

- [ ] `src/purway_geotagger/gui/pages/wind_data_page.py`
- [ ] `src/purway_geotagger/gui/pages/wind_data_logic.py` (if generate gating text or helpers change)
- [ ] `src/purway_geotagger/gui/style_sheet.py` (only if spacing/alignment tweaks are needed)
- [ ] `tests/test_wind_page_logic.py`
- [ ] `tests/test_wind_page_preview_behavior.py`

### Tests / verification (required before next phase)

- [ ] `python -m pytest tests/test_wind_page_logic.py`
- [ ] `python -m pytest tests/test_wind_page_preview_behavior.py`
- [ ] `python -m compileall src`
- [ ] Manual GUI smoke:
  - [ ] Region is visible beside system field.
  - [ ] Region blank -> generation succeeds.
  - [ ] Region filled -> output/docx metadata contains expected value.

### Gate

- [ ] Pilot can generate wind DOCX with or without Region field input.
- [ ] Region value from GUI is mapped to `REGION_ID` consistently.

### Phase Notes

- Date completed:
- Verification run:
- Deviations:

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

- [ ] Should the Wind GUI label be changed from `System Name` to `System ID`, or should only Region be added with current System naming retained?
- [ ] Do we maintain one shared production template for both OS paths, or maintain separate source templates for Windows/macOS authoring while bundling one canonical runtime template?
- [ ] Should Region also be propagated into non-Wind EXIF/XMP flows, or remain scoped to Wind DOCX/template metadata only for this track?

---

## Summary of Planned File Paths

### New files/folders (planned)

- `WIND_DATA_REGION_FIELD_IMPLEMENTATION_PHASES.md`
- `tests/test_wind_region_field.py` (optional)
- `tests/test_wind_page_region_behavior.py` (optional)
- `WIND_DATA_REGION_FIELD_CHANGESET_NOTES.md` (optional)
- `config/wind_templates/REGION_FIELD_CHANGELOG.md` (optional)
- `wind_data_generator/templates/macos/` (optional)
- `wind_data_generator/templates/windows/` (optional)

### Existing files (planned modifications)

- `src/purway_geotagger/core/wind_docx.py`
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
