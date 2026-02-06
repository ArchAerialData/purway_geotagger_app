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
- Do not require a template table containing raw component placeholders (`S_WIND`, `S_SPEED`, etc.) for v1 output.

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
- Table 2 is optional reference-only material and not required in production output.

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
  - Output folder picker
  - Output filename preview
  - `Generate DOCX` primary button

### 8.2 Simple-first behavior

Defaults for pilots:
- Pre-fill date to today.
- Pre-fill template path to bundled canonical DOCX.
- Keep only required fields visible by default.

Advanced section (collapsed by default):
- Optional filename pattern override.
- Optional output row label override (`Start`/`End`) if ever needed.

### 8.3 Suggested input widgets

- Time: masked text input with validation feedback.
- Wind Direction: combo box with common compass values + editable fallback.
- Wind Speed/Gusts/Temp: numeric spin boxes.

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
  report_date: str
  start: WindPoint
  end: WindPoint
  template_path: Path
  output_dir: Path
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
- Date: non-empty and parseable by chosen date format
- Start and End raw fields required
- Template file must exist and be `.docx`
- Output folder must exist or be creatable

### Time parsing
- Accept pilot-friendly inputs, normalize to final format:
  - `10:00am`, `10:00 am`, `10:00 AM`
  - `1:00pm`, `1:00 PM`
  - optional `13:00` -> `1:00pm`

### Wind direction
- Normalize to uppercase.
- Accept compass-like values (`N`, `SW`, `NNE`, `WNW`).
- Reject empty values.

### Numeric ranges (initial recommendation)
- Wind speed mph: 0..150
- Gust mph: 0..200
- Temp F: -80..160

### Cross-field checks
- End time must not be earlier than Start time if same-day assumption is enforced.
- If overnight runs are needed, include an explicit `Allow overnight` toggle.

### Template contract checks
- Required placeholder set exists.
- No missing required placeholders.
- Optional: enforce expected count of each placeholder.

## 11) DOCX Placeholder Mapping (Approved v1)

Metadata mapping:
- `{{ CLIENT_NAME }}` -> client name input
- `{{ SYSTEM_NAME }}` -> system name input
- `{{ DATE }}` -> normalized report date text

Final output mapping:
- `{{ S_TIME }}` -> normalized Start time display
- `{{ E_TIME }}` -> normalized End time display
- `{{ S_STRING }}` -> computed Start weather summary string
- `{{ E_STRING }}` -> computed End weather summary string

Raw fields are internal-only inputs for computation:
- `S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`
- `E_WIND`, `E_SPEED`, `E_GUST`, `E_TEMP`

The production output template does not require an intermediate raw placeholder table.

## 12) Error Handling and Pilot Messaging

Pilot-facing errors should be specific and actionable:

- `Template mismatch: missing required placeholder {{ S_STRING }}.`
- `Template mismatch: expected placeholders not found in production template.`
- `Invalid Start Time. Expected format like 10:00am or 1:00pm.`
- `Wind Speed must be an integer between 0 and 150.`
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
  - verifies `S_TIME`, `E_TIME`, `S_STRING`, `E_STRING` replacements

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
- Implement core formatter, validation, placeholder checks, DOCX writer.
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

1. Final date display format in report:
   - `MM/DD/YYYY` vs `YYYY-MM-DD` vs pilot-entered free text?
2. Should End time be allowed to roll into next day?
3. Should Wind Direction be free text or constrained to compass presets?
4. Preferred generated filename convention (example: `WindData_<Client>_<YYYY_MM_DD>.docx`)?
5. Do you want an optional debug export (outside DOCX) that includes raw component values used to build `S_STRING` and `E_STRING`?

## 18) Immediate Next Step Recommendation

Create one production DOCX template dedicated to generation (not example documentation) with the approved placeholder set, then lock tests to that contract before implementation starts.

