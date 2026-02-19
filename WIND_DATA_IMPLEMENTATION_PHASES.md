# Wind Data DOCX Feature - Phased Implementation Plan (Hard Gates)

Date created: 2026-02-06

This document is the execution plan for implementing the Wind Data DOCX feature defined in:
- `WIND_DATA_DOCX_FEATURE_PLAN.md`

It follows the same hard-gate style used by this repo's existing implementation plans.

## Execution Rules (Mandatory)

- Do not start a new phase until all tasks, tests, and gate criteria for the current phase are complete.
- Keep long-running work off the UI thread.
- Keep logic modular by package responsibility:
  - `core/` for data models, validation, templating logic
  - `gui/` for UI and interaction wiring
  - `util/` only for truly reusable helpers
- Keep macOS-first behavior for packaging and runtime.
- Use the approved placeholder contract for production template output:
  - `{{ CLIENT_NAME }}`
  - `{{ SYSTEM_NAME }}`
  - `{{ REGION_ID }}` (optional)
  - `{{ DATE }}`
  - `{{ S_TIME }}`
  - `{{ E_TIME }}`
  - `{{ S_STRING }}`
  - `{{ E_STRING }}`
  - `{{ TZ }}`
- Date placeholder format is locked:
  - `{{ DATE }}` -> `YYYY_MM_DD`
- Output filename format is locked:
  - `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`
- Output folder selection is required in Wind Data UI.
- Wind Direction input style is locked:
  - direct string input (examples: `SW`, `SSW`, `NW`, `NNE`)
- Wind Speed, Gusts, and Temp are locked to integer-only inputs:
  - reject values with units/suffixes (for example `17mph`) to avoid duplicate unit text in final string.
- Date/time inputs are picker-based and single-day scoped:
  - no overnight rollover logic in v1.
- Time Zone input is editable and defaults to `CST`.
- `{{ TZ }}` is used only in header text `Time ({{ TZ }})`.
- Debug export sidecar is required for rollout troubleshooting.
- At the end of each implementation phase, update:
  - `WIND_DATA_IMPLEMENTATION_PHASES.md` (phase notes)
  - `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (phase notes/checklist entries for this feature track)

---

## Phase W0 - Contract Lock + Test Fixture Baseline

### Goal

Freeze the template contract and prevent implementation drift.

### Work items

- [x] Confirm production template remains:
  - `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- [x] Create contract validator module for required placeholders.
- [x] Add tests for:
  - exact required placeholder set
  - missing placeholder failure
  - unexpected/extra placeholder policy behavior
  - timezone placeholder and header token presence (`{{ TZ }}` in `Time ({{ TZ }})`)
- [x] Add test fixture strategy:
  - use immutable fixture copy in `tests/test_data/wind/` or consume production template path directly with explicit checks.

### Files (new)

- `src/purway_geotagger/core/wind_template_contract.py`
- `tests/test_wind_template_contract.py`

### Files (modify)

- `WIND_DATA_DOCX_FEATURE_PLAN.md` (only if contract wording needs final lock update)

### Tests / verification (required before next phase)

- [x] `python3 -m pytest tests/test_wind_template_contract.py`
- [x] `python3 -m compileall src`

### Gate

- [x] Contract validator rejects missing required placeholders with clear messages.
- [x] Contract validator passes on current production template.

### Phase Notes

- Date completed: 2026-02-06
- Verification run:
  - `python3 -m pytest tests/test_wind_template_contract.py` (4 passed)
  - `python3 -m compileall src` (pass)
- Deviations:
  - W0 fixture strategy uses the production template path directly and creates temporary mutated `.docx` copies during tests instead of adding a dedicated `tests/test_data/wind/` fixture directory.

---

## Phase W1 - Core Data Model + Formatting + Validation

### Goal

Implement reliable, testable backend logic for raw inputs to final display values.

### Work items

- [x] Define dataclasses/models for:
  - report metadata
  - Start raw values
  - End raw values
  - rendered placeholder payload
- [x] Implement time normalization to output style:
  - `h:mmam` / `h:mmpm`
- [x] Implement date normalization for template injection:
  - `YYYY_MM_DD`
- [x] Implement weather summary formatter:
  - `<DIR> <SPEED> mph / Gusts <GUST> mph / <TEMP><degree_symbol>F`
- [x] Implement validation rules:
  - required fields
  - numeric ranges
  - direct text direction normalization
  - integer-only enforcement for speed/gust/temp (reject unit-suffixed text like `17mph`)
  - same-day Start/End policy (no overnight rollover handling)
  - timezone field required; prefill `CST`; direct text editable
- [x] Implement deterministic filename generation helper for DOCX outputs:
  - `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`
  - reuse the exact mapped `CLIENT_NAME` and `DATE` values used for placeholder injection.
- [x] Implement debug payload model for sidecar export:
  - raw Start/End component values
  - normalized display values
  - computed final strings
  - resolved template placeholder map

### Files (new)

- `src/purway_geotagger/core/wind_docx.py`
- `tests/test_wind_formatting.py`
- `tests/test_wind_validation.py`

### Files (modify)

- `src/purway_geotagger/util/errors.py` (only if adding dedicated wind validation error types)

### Tests / verification (required before next phase)

- [x] `python3 -m pytest tests/test_wind_formatting.py tests/test_wind_validation.py`
- [x] `python3 -m compileall src`

### Gate

- [x] Formatting output exactly matches contract examples.
- [x] Validation failures are explicit and pilot-readable.

### Phase Notes

- Date completed: 2026-02-06
- Verification run:
  - `python3 -m pytest tests/test_wind_formatting.py tests/test_wind_validation.py` (9 passed)
  - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py` (13 passed)
  - `python3 -m compileall src` (pass)
- Deviations:
  - Direction validation in W1 accepts letter-only direction tokens (up to 8 chars) to support common entries like `SW`, `SSW`, `NNE`, and `CALM`.

---

## Phase W2 - DOCX Render/Write Engine

### Goal

Generate a final DOCX by applying validated placeholder payload into the production template.

### Work items

- [x] Add DOCX rendering/writing service.
- [x] Validate template contract before replacement.
- [x] Replace placeholders for:
  - metadata (`CLIENT_NAME`, `SYSTEM_NAME`, `DATE`, `TZ`)
  - final values (`S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`)
- [x] Preserve header punctuation/format when replacing `TZ`:
  - `Time ({{ TZ }})` -> `Time (CST)` (or pilot-specified timezone)
- [x] Ensure output file writing is collision-safe and preserves template styling.
- [x] Ensure no unresolved required placeholders remain after render.
- [x] Write debug sidecar file alongside generated DOCX:
  - `<output_basename>.debug.json`

### Files (new)

- `src/purway_geotagger/core/wind_docx_writer.py`
- `tests/test_wind_docx_writer.py`

### Files (modify)

- `src/purway_geotagger/core/wind_docx.py` (if orchestration lives here)
- `requirements.txt` (add `python-docx` version pin)

### Tests / verification (required before next phase)

- [x] `python3 -m pytest tests/test_wind_docx_writer.py`
- [x] `python3 -m pytest tests/test_wind_debug_export.py`
- [x] `python3 -m compileall src`

### Gate

- [x] Generated DOCX contains replaced values in expected cells.
- [x] Required placeholders are fully resolved in generated output.
- [x] Template mismatch fails cleanly before writing output.
- [x] Debug sidecar is generated and includes raw + normalized + computed values.
- [x] Header format is correct (`Time (CST)` style) with parentheses preserved.

### Phase Notes

- Date completed: 2026-02-06
- Verification run:
  - `python3 -m pytest tests/test_wind_docx_writer.py tests/test_wind_debug_export.py` (4 passed)
  - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py` (17 passed)
  - `python3 -m compileall src` (pass)
- Deviations:
  - W2 rendering is implemented with direct DOCX zip/XML replacement (not `python-docx`) to preserve template styling and avoid table-reflow side effects; `python-docx` pin was still added for future feature flexibility.

---

## Phase W3 - Wind Data GUI Tab (Simple-First UX)

### Goal

Add a new top-level Wind Data tab with clear Start/End inputs and preview, while preserving existing app navigation and theme quality.

### Work items

- [x] Add new nav button/tab and page wiring in main window.
- [x] Build `Wind Data` page sections:
  - Report Info
  - Wind Inputs (Start + End rows)
  - Output Preview
  - Template + Save
- [x] Add editable timezone input in Report Info:
  - prefilled `CST`
  - manual direct text input allowed
- [x] Use picker controls for date/time:
  - date: `QDateEdit` (`YYYY_MM_DD`)
  - time: `QTimeEdit` for Start/End
- [x] Add required output-folder selection control:
  - user can browse/select destination folder for generated DOCX
  - generation is blocked until output folder is valid
  - selected folder is shown clearly in UI state
- [x] Implement form validation state and actionable error messaging.
- [x] Implement preview updates as inputs change.
- [x] Implement Generate action calling core render/write service.
- [x] (Tracking moved) Ensure behavior is correct in light and dark theme. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).
- [x] Ensure input controls enforce:
  - Wind Direction as direct text field
  - Wind Speed/Gust/Temp as integer-only entries (no unit text)
  - Time Zone as direct text field with default `CST`

### Files (new)

- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/pages/wind_data_logic.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`

### Files (modify)

- `src/purway_geotagger/gui/main_window.py`
- `src/purway_geotagger/gui/pages/__init__.py`
- `src/purway_geotagger/gui/style_sheet.py`

### Tests / verification (required before next phase)

- [x] `python3 -m compileall src`
- [x] Add and run non-Qt logic tests for page/controller helpers:
  - [x] `python3 -m pytest tests/test_wind_page_logic.py` (or equivalent extracted logic tests)
- [x] (Tracking moved) Manual smoke (macOS):
  - [x] Wind tab visible and selectable
  - [x] validation blocks invalid submissions
  - [x] `17mph` style numeric input is rejected for speed/gust/temp
  - [x] direct direction entries like `SW`, `SSW`, `NNE` are accepted
  - [x] timezone field defaults to `CST` and can be edited (for example `MST`, `PST`)
  - [x] date/time pickers enforce same-day workflow (no overnight logic path)
  - [x] preview strings update correctly
  - [x] output folder must be selected/valid before generate is enabled
  - [x] generated DOCX path is shown and opens
  - [x] debug sidecar file is generated next to DOCX
  - [x] light/dark contrast is acceptable
  - Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6) to keep one source of open tasks.

### Gate

- [x] (Tracking moved) A pilot can generate a valid DOCX end-to-end from GUI without terminal use. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).
- [x] (Tracking moved) UI remains consistent with existing run/jobs/templates/help style. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).

### Phase Notes

- Date completed: 2026-02-08 (tracking moved to consolidated release checklist)
- Verification run:
  - `python3 -m pytest tests/test_wind_page_logic.py tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py` (22 passed)
  - `python3 -m compileall src` (pass)
- Deviations:
  - W3 implementation is complete from code/test perspective; remaining release validation is tracked centrally in `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).

---

## Phase W4 - Worker, Threading, and UX Hardening

### Goal

Keep UI responsive and robust during DOCX generation and file operations.

### Work items

- [x] (Tracking moved) Add worker-based execution path if generation can block UI. Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).
- [x] (Tracking moved) Add cancel-safe and error-safe handling for generation flow. Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).
- [x] (Tracking moved) Add progress/status messaging for user confidence. Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).
- [x] (Tracking moved) Ensure repeated runs in a single session do not leak stale state. Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).

### Files (new)

- `src/purway_geotagger/gui/workers_wind.py` (optional if a dedicated worker module is preferred)

### Files (modify)

- `src/purway_geotagger/gui/workers.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/controllers.py` (only if shared controller abstractions are needed)

### Tests / verification (required before next phase)

- [x] (Tracking moved) `python3 -m compileall src` (W4 scope). Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).
- [x] (Tracking moved) Add/run tests for worker lifecycle and error handoff (non-UI logic where possible). Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).
- [x] (Tracking moved) Manual test:
  - [x] generate while rapidly switching tabs (no crash)
  - [x] repeated generate actions produce stable behavior
  - Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).

### Gate

- [x] (Tracking moved) No noticeable UI freeze during generation on normal pilot laptop datasets. Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).
- [x] (Tracking moved) Failures show clear messages and leave UI recoverable for next run. Active release decision tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).

### Phase Notes

- Date completed: 2026-02-08 (v1 defer decision recorded)
- Verification run:
- `python3 -m compileall src` (pass)
- `python3 -m pytest tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_autofill_dialog.py` (pass)
- Deviations:
  - Release decision: **defer W4 worker/cancel/progress hardening to post-v1** (Option B), documented in `RELEASE_READINESS_OPEN_ITEMS.md` (Item 10).
  - Accepted v1 risk: Wind DOCX generation remains synchronous and may briefly block UI on unusually slow storage/IO.
  - Post-v1 backlog scope: dedicated generation worker path, cancel-safe flow, explicit progress updates, and repeated-run stress validation.

---

## Phase W5 - Packaging, Resource Bundling, and Help Documentation

### Goal

Ensure packaged `.app` includes required resources/dependencies and pilots can use Wind Data feature in field distribution builds.

### Work items

- [x] Bundle production wind template in app resources.
- [x] Ensure runtime can resolve bundled template path via `resource_path`.
- [x] Validate dependency install and packaging for `python-docx`.
- [x] Update user-facing docs/help content for Wind tab usage (README + Wind page inline guidance for v1).
- [x] Add change-set rollback documentation for wind feature implementation.

### Files (new)

- `config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx` (bundled production template copy)
- `WIND_DATA_CHANGESET_NOTES.md`

### Files (modify)

- `PurwayGeotagger.spec`
- `scripts/macos/build_app.sh`
- `README.md`
- `src/purway_geotagger/gui/pages/help_page.py` (optional follow-up; v1 guidance is provided in README + Wind page UI copy)
- `src/purway_geotagger/core/settings.py` (if adding wind default paths/preferences)

### Tests / verification (required before completion)

- [x] `python3 -m compileall src`
- [x] targeted pytest run including wind tests:
  - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py`
- [x] (Tracking moved) Build verification:
  - [x] build `.app` from scripts
  - [x] launch `.app`
  - [x] generate Wind DOCX from packaged app using bundled template
  - Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).

### Gate

- [x] (Tracking moved) Feature works in packaged macOS app, not only dev environment. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).
- [x] Documentation reflects final user workflow.

### Phase Notes

- Date completed: 2026-02-08 (manual packaged-app gate pending)
- Verification run:
  - `python3 -m compileall src` (pass)
  - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py` (pass)
- Deviations:
  - Packaged `.app` generation/launch/manual DOCX generation verification is tracked centrally in `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).

---

## Phase W6 - Optional Enhancements (Only After W5)

### Candidate enhancements

- [x] (Deferred post-v1) Batch generation for multiple reports in one run.
- [x] (Deferred post-v1) Additional output presets (metric units, alternate string format).
- [x] (Deferred post-v1) Import assist from CSV/manual paste grid.
- [x] Weather API autofill spike for Start/End wind values (see `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md`).
  - WS0 planning gate completed on 2026-02-07 (provider + contract lock).
  - WS1 core service spike completed on 2026-02-07 (`src/purway_geotagger/core/wind_weather_autofill.py` + `tests/test_wind_weather_autofill.py`).
  - WS2 GUI thin slice implemented on 2026-02-07 (`wind_autofill_dialog` + worker-thread wiring + partial-fill status handling); manual smoke gate still pending.
- [x] DOCX embedded metadata spike for downstream automation:
  - inject backend placeholder/value map (for example `S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`, `E_*` and resolved display values) into DOCX-accessible metadata/custom fields.
  - evaluate extraction-friendly formats for the report automation program (for example custom document properties vs custom XML part).

### Files (to be determined when selected)

- TBD based on selected enhancement scope.

### Gate

- [x] Each selected optional enhancement includes dedicated tests and rollback notes.

### Phase Notes

- Date completed: 2026-02-08 (selected optional items only)
- Verification run:
- Deviations:
  - Optional W6 enhancements (batch/presets/import-assist) are explicitly deferred to post-v1 and are not release blockers for Sunday packaging.
- Tracking note (2026-02-07):
  - Weather autofill WS0 was completed and documented in `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md`.
  - Weather autofill WS1 was completed as isolated core-service work before GUI integration.
  - Weather autofill WS2 was implemented with off-UI-thread search/fill workers and explicit location suggestion/selection flow.
  - WS2.1 lifecycle hardening landed to prevent autofill worker teardown races that could trigger `QThread` crash on rapid/stale completion paths.
  - WS2.3 control-consistency hardening aligned popup time steppers with main Wind UI and added 24h typed-hour normalization (`13`-`23` -> `1`-`11` + `PM`) across both pages.
  - WS2.4 date-bounds hardening added popup report-date selection constrained to current-year-through-today and synced popup date into main Wind metadata before autofill request execution.
  - WS2.5 data-completeness hardening added provider-level backfill: when NWS rows are partial (for example missing gust), missing fields are now backfilled from Open-Meteo archive while preserving resolved NWS fields.
  - WS2.6 source-chain hardening added AviationWeather METAR as the middle provider: `NWS -> METAR -> Open-Meteo`, with partial-row merge performed in that order for higher gust/data fill rates.
  - DOCX metadata spike landed via embedded custom XML part `customXml/purway_wind_metadata.xml` carrying template placeholder values and component values (`S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`, `E_*`) for downstream extraction.
  - Region/System template-variant planning track added on 2026-02-18:
    - execution plan: `WIND_DATA_REGION_FIELD_IMPLEMENTATION_PHASES.md`
    - WR0 completed on 2026-02-18 (contract lock + template inventory).
    - added phase `WR3A` for 3-template auto-selection:
      - `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
      - `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
      - `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
    - placeholder decision for WR3A: keep system token unchanged and use `{{ REGION_ID }}` for region mapping.
    - filename token mapping for WR3A templates is documented (`ClientName`, `SYSTEM`, `Region`/`REGION`, `YYYY_MM_DD`).
    - includes planned cross-field validation rule: at least one of `System ID` or `Region` is required before generation.
  - WR implementation update on 2026-02-18:
    - added `src/purway_geotagger/core/wind_template_selector.py` and wired page generation to auto-select profile template by System/Region inputs.
    - made `System ID` optional in `src/purway_geotagger/core/wind_docx.py` with cross-field validation requiring at least one of `System ID` or `Region`.
    - added profile-aware required placeholder enforcement in `src/purway_geotagger/core/wind_template_contract.py` and writer wiring in `src/purway_geotagger/core/wind_docx_writer.py`.
    - verification:
      - `python -m pytest tests/test_wind_template_selector.py tests/test_wind_validation.py tests/test_wind_template_contract.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py` (51 passed)
      - `python -m compileall src` (pass)
    - open gate items: manual GUI smoke for all 3 profile scenarios and macOS dev-run verification.

---

## Open Decisions Before W1/W2 Coding

Locked decisions (already approved):
- Date format: `YYYY_MM_DD`
- Output filename: `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`
- Output folder selection in UI: required
- Wind Direction input: direct string entry
- Wind Speed/Gust/Temp inputs: integer-only (no unit text)
- Same-day date/time policy: no overnight rollover logic
- Time Zone input: editable direct text, default `CST` (mapped to `{{ TZ }}`)
- Debug sidecar export: required

Remaining open decisions:
- None blocking implementation.

---

## Summary of Planned File Paths

### New files (planned)

- `src/purway_geotagger/core/wind_template_contract.py`
- `src/purway_geotagger/core/wind_docx.py`
- `src/purway_geotagger/core/wind_docx_writer.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/pages/wind_data_logic.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- `tests/test_wind_template_contract.py`
- `tests/test_wind_formatting.py`
- `tests/test_wind_validation.py`
- `tests/test_wind_docx_writer.py`
- `tests/test_wind_debug_export.py`
- `tests/test_wind_page_logic.py` (or equivalent extracted-logic test file)
- `config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- `WIND_DATA_CHANGESET_NOTES.md`

### Existing files (planned modifications)

- `requirements.txt`
- `PurwayGeotagger.spec`
- `scripts/macos/build_app.sh`
- `src/purway_geotagger/core/settings.py`
- `src/purway_geotagger/util/errors.py` (optional)
- `src/purway_geotagger/gui/main_window.py`
- `src/purway_geotagger/gui/pages/__init__.py`
- `src/purway_geotagger/gui/style_sheet.py`
- `src/purway_geotagger/gui/workers.py`
- `src/purway_geotagger/gui/controllers.py` (optional)
- `src/purway_geotagger/gui/pages/help_page.py`
- `README.md`
- `WIND_DATA_DOCX_FEATURE_PLAN.md` (phase-notes alignment only)
- `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (phase notes/checklist updates during execution)
