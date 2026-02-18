# Wind Data DOCX Generator Feature Plan (Planning Only)

Date: 2026-02-06
Status: Planning only. No app behavior changes in this document.

Decision update (approved in-thread):
- Preferred production template contract is simplified.
- Keep raw wind inputs in GUI/backend.
- Use final DOCX placeholders for display values:
  - `{{ S_TIME }}`
  - `{{ E_TIME }}`
  - `{{ S_STRING }}`
  - `{{ E_STRING }}`
- Use timezone placeholder in final table header:
  - `{{ TZ }}`
- Add optional region placeholder support:
  - `{{ REGION_ID }}`
- Do not require a template table containing raw component placeholders (`S_WIND`, `S_SPEED`, etc.) for v1 output.
- Date placeholder output format is locked to `YYYY_MM_DD`.
- Output filename format is locked to:
  - `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`
- Output folder selection is required in the Wind Data UI.
- Wind Direction input is direct string entry (examples: `SW`, `SSW`, `NW`, `NNE`).
- Wind Speed, Gusts, and Temp are integer-only GUI inputs (no unit text allowed in input).
- Date/time are selected in GUI controls for a single report day (no overnight rollover handling).
- Debug export is enabled for rollout troubleshooting.
- Timezone input is editable and defaults to `CST`.

## 1) Objective

Add a new GUI tab that lets pilots enter wind data once and generate a polished DOCX report from a master template, with strict formatting and reliable placeholder mapping.

Primary workflow target:
- Pilot opens `Wind Data` tab.
- Pilot enters client/system/date plus Start and End wind values.
- App validates inputs, previews final output strings, and writes a new DOCX file.
- Generated DOCX preserves template styling and uses the required final display format.

## 2) Source Assets Confirmed

Folder:
- `wind_data_generator/Example of Template Structure`

Files:
- `MacOS_WindData_ClientName_YYYY_MM_DD.pages`
- `MacOS_WindData_ClientName_YYYY_MM_DD.docx`
- `PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`

Current DOCX inspection (reference template) shows 3 tables:

Table 1:
- `Client Name | {{ CLIENT_NAME }}`
- `System Name | {{ SYSTEM_NAME }}`
- `Date | {{ DATE }}`

Table 2:
- Header row: `Time | Wind Direction | Wind Speed | Gusts | Temp`
- Start row placeholders: `{{ S_TIME }}`, `{{ S_WIND }}`, `{{ S_SPEED }}`, `{{ S_GUST }}`, `{{ S_TEMP }}`
- End row placeholders: `{{ E_TIME }}`, `{{ E_WIND }}`, `{{ E_SPEED }}`, `{{ E_GUST }}`, `{{ E_TEMP }}`

Table 3:
- Header label row: `EXAMPLE OF EXPECTED OUTPUT FORMAT`
- Column headers: `Time` and `Wind Direction, Wind Speed, Gusts, Temp`
- Data rows currently contain hard-coded sample text:
  - `Start | 10:00am | SW 0 mph / Gusts 0 mph / 51(deg)F`
  - `End | 1:00pm | SW 0 mph / Gusts 0 mph / 51(deg)F`

Approved production contract for v1:
- Keep Table 1 metadata placeholders.
- Use a final output table with placeholders:
  - `{{ S_TIME }}`
  - `{{ E_TIME }}`
  - `{{ S_STRING }}`
  - `{{ E_STRING }}`
  - `{{ TZ }}`
- Table 2 is optional reference-only material and not required in production output.

Production template verification snapshot (2026-02-06):
- File checked: `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- Found placeholders (required set + optional region token):
  - `{{ CLIENT_NAME }}`
  - `{{ SYSTEM_NAME }}`
  - `{{ REGION_ID }}` (optional)
  - `{{ DATE }}`
  - `{{ S_TIME }}`
  - `{{ E_TIME }}`
  - `{{ S_STRING }}`
  - `{{ E_STRING }}`
  - `{{ TZ }}`
- Table shape (current):
  - Table 1: metadata key/value rows
  - Table 2: final output rows (`Start`, `End`) with header:
    - `Time ({{ TZ }})`
    - `Wind Direction / Wind Speed / Gusts / Temp`
- Result: matches this plan's required contract; no template changes required right now.

## 3) Exact Output Contract

### 3.1 Final combined weather column format

Required output string format for each row:
- `<WIND_DIR> <WIND_SPEED> mph / Gusts <GUST> mph / <TEMP><degree_symbol>F`

Example:
- `SW 0 mph / Gusts 0 mph / 51(deg)F`

Important formatting rules:
- No slash between direction and speed.
- Single spaces before/after slash separators.
- Static tokens must be exact:
  - `mph`
  - `Gusts`
  - degree symbol + `F` after temperature.

### 3.2 Time format contract

Final displayed time in DOCX:
- `h:mmam` or `h:mmpm` (no space before am/pm), matching your sample style.

Examples:
- `10:00am`
- `1:00pm`

### 3.3 Start and End semantics

Inputs are explicitly split into two records:
- Start row raw inputs (internal): `S_TIME`, `S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`
- End row raw inputs (internal): `E_TIME`, `E_WIND`, `E_SPEED`, `E_GUST`, `E_TEMP`

Mapping must never cross rows:
- Start raw fields compute Start placeholders (`S_TIME`, `S_STRING`).
- End raw fields compute End placeholders (`E_TIME`, `E_STRING`).

### 3.4 Date and filename contract

Date placeholder format:
- `{{ DATE }}` must be normalized to `YYYY_MM_DD`.

Output filename format:
- `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`

Example:
- `WindData_TargaResources_2026_02_06.docx`

Filename source values:
- Reuse the exact values sent to template placeholders for `CLIENT_NAME` and `DATE`.

Day-boundary policy:
- Each report DOCX is for one selected day only.
- If pilots fly on a different day, generate a separate DOCX for that day.

Timezone header policy:
- Timezone is rendered via `{{ TZ }}` in the table header text `Time ({{ TZ }})`.
- Parentheses remain template-owned and must remain in final output.
- Example final header:
  - `Time (CST)`

## 4) Product Scope and Non-Goals

### In scope
- New `Wind Data` top-level tab in GUI.
- Manual pilot data entry (no weather API dependency).
- DOCX generation from a bundled master template.
- Strong validation and preview before save.
- Dark/light theme support consistent with current app styling conventions.

### Out of scope (initial release)
- Editing `.pages` files directly.
- Bulk generation of many wind documents in one run.
- Importing wind values from CSVs or external APIs.
- Template visual editor inside app.

## 5) Recommended Architecture in This Repo

Follow existing boundaries from `AGENTS.md`.

### 5.1 Core layer (`src/purway_geotagger/core/`)

Proposed files:
- `src/purway_geotagger/core/wind_docx.py`
  - DTO/dataclasses for request payload.
  - Validation helpers.
  - Formatting helpers (time and combined weather string).
  - Placeholder context builder (`S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`).
  - DOCX render/save logic with collision-safe output naming.

- `src/purway_geotagger/core/wind_template_contract.py`
  - Template sanity checks (required placeholder set).
  - Template version/shape validation before writing.

### 5.2 GUI layer (`src/purway_geotagger/gui/`)

Proposed files:
- `src/purway_geotagger/gui/pages/wind_data_page.py`
  - Main wind tab UI.
  - Input widgets for metadata + Start/End raw values.
  - Inline preview and validation messages.

- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
  - Reusable Start/End entry table widget.

- `src/purway_geotagger/gui/workers.py`
  - Add `WindDocWorker` if generation/validation/file IO should be offloaded from UI thread.

- `src/purway_geotagger/gui/main_window.py`
  - Add top nav button `Wind Data`.
  - Insert new tab/page into stack.

- `src/purway_geotagger/gui/style_sheet.py`
  - Reuse existing card/input/button classes.
  - Add minimal row-tag styling for Start/End if needed.

### 5.3 Utility layer (`src/purway_geotagger/util/`)

Optional helpers if reused:
- `src/purway_geotagger/util/wind_format.py`
  - Time normalization.
  - Direction canonicalization.
  - Numeric parsing.

## 6) Template Strategy Options

### Option A: Minimal placeholder contract with `python-docx` replacement (recommended for v1)

Approach:
- Use a production DOCX template with explicit placeholders:
  - metadata: `CLIENT_NAME`, `SYSTEM_NAME`, `DATE`
  - final values: `S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`
- Generate final Start/End strings in backend.
- Replace placeholders in DOCX by walking table cells/paragraphs/runs.

Pros:
- Matches approved simplified plan.
- Easy to understand and maintain.
- Keeps formatting logic in tested code, not in template text composition.
- No need for intermediate raw-placeholder table in output document.

Risks:
- Word edits can split placeholder text across runs.

Mitigations:
- Add template contract validation and fail fast with clear messages.
- Maintain a locked production template.
- Add tests that verify replacement on the production template fixture.

### Option B: Table-index write strategy (fallback)

Approach:
- Ignore placeholders and write fixed cells by table/row/column indices.

Pros:
- Works even if placeholders are removed by mistake.

Risks:
- Fragile if table structure changes.
- Harder for template maintainers to reason about.

### Option C: `docxtpl` templating engine (future only if needed)

Pros:
- Powerful templating semantics.

Risks:
- Additional dependency and packaging surface.
- Not required for the current simplified contract.

### Option D: Raw XML string replacement (not recommended)

Risks:
- Fragile with Word XML run behavior and formatting.

Recommendation:
- Use Option A for v1.
- Keep Option B as emergency fallback if placeholder integrity is lost.

## 7) Recommended Production Template Contract

Create a dedicated production template file (separate from example/mockup) with this required placeholder set:

- `{{ CLIENT_NAME }}`
- `{{ SYSTEM_NAME }}`
- `{{ DATE }}`
- `{{ S_TIME }}`
- `{{ E_TIME }}`
- `{{ S_STRING }}`
- `{{ E_STRING }}`
- `{{ TZ }}`

Optional placeholder:
- `{{ REGION_ID }}`

Template guidance:
1. Keep only final report content needed by pilots.
2. Remove reference-only raw mapping table from production output unless explicitly needed.
3. Add a visible template version marker (for support and contract checks).
4. Keep placeholders editable but stable.

## 8) GUI UX Blueprint (Pilot-Friendly by Default)

### 8.1 Tab layout

Top-level cards:
- Card A: `Report Info`
  - Client Name
  - System Name
  - Date
  - Time Zone (`TZ`, default `CST`, editable)

- Card B: `Wind Inputs`
  - Two explicit rows: `Start` and `End`
  - Columns:
    - Time
    - Wind Direction
    - Wind Speed
    - Gusts
    - Temp

- Card C: `Output Preview`
  - Start preview line:
    - Time value + computed `S_STRING`
  - End preview line:
    - Time value + computed `E_STRING`

- Card D: `Template and Save`
  - Template file picker (defaults to bundled production template)
  - Output folder picker (required)
  - Output filename preview
  - `Generate DOCX` primary button

### 8.2 Simple-first behavior

Defaults for pilots:
- Pre-fill date picker to today (displayed as `YYYY_MM_DD`).
- Pre-fill template path to bundled canonical DOCX.
- Pre-fill output folder from last-used value (or user home/Documents fallback).
- Keep only required fields visible by default.

Advanced section (collapsed by default):
- Optional filename pattern override.
- Optional output row label override (`Start`/`End`) if ever needed.

### 8.3 Suggested input widgets

- Date: `QDateEdit` (calendar popup) normalized to `YYYY_MM_DD`.
- Time: `QTimeEdit` for Start/End time fields.
- Time Zone: `QLineEdit` prefilled with `CST` and editable.
- Wind Direction: direct text input (`QLineEdit`) with uppercase normalization.
- Wind Speed/Gusts/Temp: integer-only controls (`QSpinBox` or strict integer validators).

## 9) Data Model Proposal

```text
WindPoint:
  time_raw: str
  wind_direction: str
  wind_speed_mph: int
  gust_mph: int
  temp_f: int

WindReportRequest:
  client_name: str
  system_name: str
  report_date: str  # normalized: YYYY_MM_DD
  timezone: str     # default: CST, editable (for {{ TZ }})
  start: WindPoint
  end: WindPoint
  template_path: Path
  output_dir: Path  # required
  output_filename: str | None

WindReportRender:
  s_time: str
  e_time: str
  s_string: str
  e_string: str
  placeholders: dict[str, str]
```

## 10) Validation Rules

### Required fields
- Client Name: non-empty
- System Name: non-empty
- Date: non-empty and normalizable to `YYYY_MM_DD`
- Time Zone: non-empty (default `CST`), direct text editable
- Start and End raw fields required
- Template file must exist and be `.docx`
- Output folder selection is required and must exist or be creatable

### Time parsing
- Source of truth is GUI date/time picker controls (`QDateEdit` + `QTimeEdit`).
- Convert selected time to final format:
  - `h:mmam` / `h:mmpm`
- Convert selected date to:
  - `YYYY_MM_DD`

### Wind direction
- Normalize to uppercase.
- Accept compass-like values (`N`, `SW`, `NNE`, `WNW`).
- Reject empty values.
- Direct string input is allowed for pilots (not restricted to preset-only dropdown values).

### Numeric ranges (initial recommendation)
- Wind speed mph: 0..150
- Gust mph: 0..200
- Temp F: -80..160
- Integer-only enforcement for all three numeric fields:
  - reject non-integer text
  - reject values with units or suffixes/prefixes (for example `17mph`, `mph17`, `51F`)
  - GUI blocks generation until all numeric fields are valid integers

### Cross-field checks
- Same-day only policy:
  - Start and End belong to the selected report date.
  - No overnight rollover logic in v1.

### Template contract checks
- Required placeholder set exists.
- No missing required placeholders.
- Optional: enforce expected count of each placeholder.

## 11) DOCX Placeholder Mapping (Approved v1)

Metadata mapping:
- `{{ CLIENT_NAME }}` -> client name input
- `{{ SYSTEM_NAME }}` -> system name input
- `{{ REGION_ID }}` -> optional Region input (blank-safe)
- `{{ DATE }}` -> normalized report date text in `YYYY_MM_DD`
- `{{ TZ }}` -> timezone input text (default `CST`)

Final output mapping:
- `{{ S_TIME }}` -> normalized Start time display
- `{{ E_TIME }}` -> normalized End time display
- `{{ S_STRING }}` -> computed Start weather summary string
- `{{ E_STRING }}` -> computed End weather summary string

Raw fields are internal-only inputs for computation:
- `S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`
- `E_WIND`, `E_SPEED`, `E_GUST`, `E_TEMP`

The production output template does not require an intermediate raw placeholder table.

Filename mapping:
- Output filename is derived from mapped placeholders:
  - `WindData_{{ CLIENT_NAME }}_{{ DATE }}.docx`
- Example:
  - `WindData_TargaResources_2026_02_06.docx`

Header rendering note:
- Replace only the `{{ TZ }}` token and preserve template punctuation.
- `Time ({{ TZ }})` must become `Time (CST)` (or another pilot-provided timezone).

Debug mapping artifact:
- Generate a debug sidecar file for troubleshooting:
  - `<output_basename>.debug.json`
- Sidecar should include:
  - raw input values (`S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`, `E_*`)
  - normalized display values (`S_TIME`, `E_TIME`)
  - computed strings (`S_STRING`, `E_STRING`)
  - resolved placeholder payload

## 12) Error Handling and Pilot Messaging

Pilot-facing errors should be specific and actionable:

- `Template mismatch: missing required placeholder {{ S_STRING }}.`
- `Template mismatch: expected placeholders not found in production template.`
- `Invalid Start Time. Expected format like 10:00am or 1:00pm.`
- `Wind Speed must be an integer between 0 and 150.`
- `Wind Speed, Gusts, and Temp must be integers only (no unit text).`
- `Time Zone is required (example: CST).`
- `Could not write output file. Check folder permissions and try again.`

Success message:
- `Wind DOCX generated: <absolute path>`

## 13) Dependencies and Packaging Impact

### Proposed dependency
- Add `python-docx` to `requirements.txt` (version pin during implementation).

### macOS packaging considerations
- Update `PurwayGeotagger.spec` if hidden imports are required.
- Bundle production master DOCX template in app data section.
- Use `resource_path(...)` resolution for default template path.
- Never rely on shell commands for document generation.

### Why not `.pages` for generation
- `.pages` internals are iWork binary structures, not stable for deterministic placeholder edits in this pipeline.
- DOCX is the correct automation target for maintainability.

## 14) Test Plan

### Unit tests
- `tests/test_wind_formatting.py`
  - time normalization cases
  - combined string format exactness
  - direction normalization

- `tests/test_wind_validation.py`
  - required field checks
  - numeric boundary tests
  - cross-field start/end logic

- `tests/test_wind_template_contract.py`
  - detects required placeholder set
  - clear failure messages on mismatch

- `tests/test_wind_docx_writer.py`
  - renders from fixture production template
  - verifies `S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`, `TZ` replacements
  - verifies header remains `Time (CST)` style with parentheses preserved

- `tests/test_wind_debug_export.py`
  - verifies debug sidecar JSON is written
  - verifies payload includes raw values + computed values

### GUI-focused tests (lightweight)
- controller/page logic tests for:
  - validation gating of `Generate DOCX` button
  - preview updates from raw inputs to final strings

### Manual verification checklist
- Light mode and dark mode readability
- Start and End row clarity on small laptop width
- Generated DOCX opens in Word/Pages and preserves styling

## 15) Phased Implementation Gates (For Later Execution)

This is a future implementation roadmap. No phase has started yet.

### Phase W0 - Contract lock
- Finalize production DOCX template with approved placeholder set.
- Freeze final output string rules.
- Gate: approved template contract + signed-off sample output.

### Phase W1 - Core generator
- Implement core formatter, validation, placeholder checks, DOCX writer, and debug sidecar export.
- Add unit tests for mapping/formatting/validation.
- Gate: all W1 tests pass; generated sample matches expected output exactly.

### Phase W2 - GUI tab
- Add new `Wind Data` tab and input cards.
- Add preview and generate flow.
- Keep long-running/file IO off UI thread if needed.
- Gate: manual smoke run succeeds in light/dark themes on macOS.

### Phase W3 - Packaging and docs
- Add dependency + bundled template to packaging flow.
- Add user documentation/help section for Wind tab.
- Gate: packaged app can generate DOCX without terminal dependencies.

### Phase W4 - Optional enhancements
- Batch mode, alternate output layouts, import helpers.
- Gate: explicit requirement approval before scope expansion.

## 16) Risks and Mitigations

Risk: Template edits break placeholder integrity.
- Mitigation: strict placeholder contract validator + clear errors.

Risk: Placeholder text gets split by Word formatting edits.
- Mitigation: lock production template and verify in tests against exact file.

Risk: UI complexity grows quickly.
- Mitigation: simple default form; advanced options collapsed.

Risk: Date/time ambiguity.
- Mitigation: explicit accepted formats + normalized preview before generation.

## 17) Open Questions to Resolve Before Coding

No blocking open questions remain for implementation start.

## 18) Immediate Next Step Recommendation

Create one production DOCX template dedicated to generation (not example documentation) with the approved placeholder set, then lock tests to that contract before implementation starts.

## 19) Revisit Tonight (Talking Points Only, No Implementation Yet)

These are intentionally deferred discussion items to review before expanding scope:

1. Output Preview header alignment polish
- Status: closed for now (accepted in pilot review on 2026-02-07).
- Reopen only if future UI changes regress alignment.

2. Simplify `Template + Save` UI section
- Current thought: remove visible template location/path from the primary pilot UI.
- Revisit goal: keep this section focused on:
  - output folder selection
  - output filename preview
- Constraint to decide later: whether template selection remains available behind an advanced control or is fully hidden for pilots.

3. Weather API-assisted autofill feasibility (future)
- Exploration target: evaluate whether we can support pilot input of:
  - ZIP code (or ZIP + city/state)
  - Start time
  - End time
- Desired behavior:
  - retrieve authoritative weather values for only Start/End timestamps (not every interval in between),
  - map to required fields (direction, speed, gust, temp),
  - eventually allow one-click autofill into Wind Inputs.
- Deferred technical questions for later research:
  - trusted, authoritative provider options,
  - free-tier limits and terms,
  - support for 30-minute/hourly granularity at location/time specificity,
  - macOS app constraints for optional location-based UX (for example, "Use my location") versus explicit ZIP/city input.

4. DOCX embedded metadata for downstream report automation
- Exploration target: evaluate adding backend placeholder/value payload into generated DOCX metadata so external automation can extract the same source values used for replacement.
- Desired behavior:
  - preserve normal visible template output for pilots,
  - also embed machine-readable key/value data (original backend placeholders and final resolved values).
- Deferred technical questions for later research:
  - best container in DOCX package (custom properties vs custom XML part),
  - compatibility of extraction across Word/Pages/save cycles,
  - size/format conventions and versioning for robust downstream parsing.
- Status update (2026-02-07):
  - Implemented using a custom XML part in generated DOCX outputs:
    - `customXml/purway_wind_metadata.xml`
  - Embedded payload includes:
    - resolved template placeholder map (`CLIENT_NAME`, `SYSTEM_NAME`, `DATE`, `TZ`, `S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`)
    - component value map (`S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`, `E_WIND`, `E_SPEED`, `E_GUST`, `E_TEMP`)
