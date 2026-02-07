# Wind Data Feature Change Sets + Rollback Blocks

Date: 2026-02-06

This file groups Wind Data work into isolated change sets so each phase can be kept or reverted independently.

---

## Change Set W0 - Template Contract Lock

### Added
- `src/purway_geotagger/core/wind_template_contract.py`
- `tests/test_wind_template_contract.py`

### Rollback block (W0 only)
- Remove:
  - `src/purway_geotagger/core/wind_template_contract.py`
  - `tests/test_wind_template_contract.py`
- Revert W0 checkbox/note updates in:
  - `WIND_DATA_IMPLEMENTATION_PHASES.md`
  - `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`

---

## Change Set W1 - Core Wind Formatting + Validation

### Added
- `src/purway_geotagger/core/wind_docx.py`
- `tests/test_wind_formatting.py`
- `tests/test_wind_validation.py`

### Rollback block (W1 only)
- Remove:
  - `src/purway_geotagger/core/wind_docx.py`
  - `tests/test_wind_formatting.py`
  - `tests/test_wind_validation.py`
- Revert W1 checkbox/note updates in:
  - `WIND_DATA_IMPLEMENTATION_PHASES.md`
  - `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`

---

## Change Set W2 - DOCX Writer + Debug Sidecar

### Added
- `src/purway_geotagger/core/wind_docx_writer.py`
- `tests/test_wind_docx_writer.py`
- `tests/test_wind_debug_export.py`

### Modified
- `requirements.txt` (added `python-docx==1.1.2`)

### Rollback block (W2 only)
- Remove:
  - `src/purway_geotagger/core/wind_docx_writer.py`
  - `tests/test_wind_docx_writer.py`
  - `tests/test_wind_debug_export.py`
- Revert dependency change in:
  - `requirements.txt`
- Revert W2 checkbox/note updates in:
  - `WIND_DATA_IMPLEMENTATION_PHASES.md`
  - `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`

---

## Change Set W3 - Wind Data GUI Tab + Page Logic

### Added
- `src/purway_geotagger/gui/pages/wind_data_logic.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- `tests/test_wind_page_logic.py`

### Modified
- `src/purway_geotagger/gui/main_window.py`
- `src/purway_geotagger/gui/pages/__init__.py`
- `src/purway_geotagger/gui/style_sheet.py`

### Rollback block (W3 only)
- Remove:
  - `src/purway_geotagger/gui/pages/wind_data_logic.py`
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
  - `tests/test_wind_page_logic.py`
- Revert GUI integration/style changes in:
  - `src/purway_geotagger/gui/main_window.py`
  - `src/purway_geotagger/gui/pages/__init__.py`
  - `src/purway_geotagger/gui/style_sheet.py`
- Revert W3 checkbox/note updates in:
  - `WIND_DATA_IMPLEMENTATION_PHASES.md`
  - `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`

---

## Change Set W3.1 - Wind Data UI Polish (Theme + Time UX)

### Modified
- `src/purway_geotagger/gui/widgets/mac_stepper.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/pages/wind_data_logic.py`
- `src/purway_geotagger/gui/style_sheet.py`
- `tests/test_wind_page_logic.py`

### Key updates
- Added explicit AM/PM dropdowns next to Start/End time entries.
- Start defaults to `AM`, End defaults to `PM`.
- Added 12h-to-24h conversion helper (`to_24h_time_string`) for robust backend mapping.
- Reduced Wind Direction input width to balance row proportions.
- Kept speed/gust/temp compact and integer-only.
- Made `Select Template...` and `Select Output Folder...` buttons primary blue.
- Added `QDateEdit/QTimeEdit` theme styling to fix dark/black field rendering in Light mode.
- Reworked Output Preview into bordered row blocks with stronger headings/time/summary contrast for Dark mode readability.
- Added blue stepper button styling for Wind time/speed/gust/temp controls.
- Fixed Wind input change-signal wiring so Output Preview updates live as values are edited.
- Replaced native Qt inline steppers with custom segmented macOS-style stepper controls (`field + stepper` layout).
- Tuned stepper resting-state contrast (dedicated background/border/divider tokens) so controls remain visible in both Light and Dark themes before hover.
- Center-aligned Wind Input column headers and their control groups so each header sits directly above its associated field/stepper.
- Decoupled live Output Preview from report metadata validation so preview updates from Wind Inputs alone.
- Added regression coverage ensuring preview renders even when Client/System/Time Zone are blank.
- Sanitized output filename client segment by removing internal whitespace (for example, `Targa Resources` -> `TargaResources`) while preserving spaced `CLIENT_NAME` in DOCX placeholders.
- Added tests for new time conversion helper behavior/validation.

### Rollback block (W3.1 only)
- Revert:
  - `src/purway_geotagger/gui/widgets/mac_stepper.py`
  - `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `src/purway_geotagger/gui/pages/wind_data_logic.py`
  - `src/purway_geotagger/gui/style_sheet.py`
  - `src/purway_geotagger/core/wind_docx.py`
  - `tests/test_wind_page_logic.py`
  - `tests/test_wind_page_preview_behavior.py`
  - `tests/test_wind_formatting.py`
  - `tests/test_wind_validation.py`

---

## Validation Snapshot

- `python3 -m pytest tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_main_window_startup.py tests/test_wind_template_contract.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py` -> 30 passed
- `python3 -m compileall src` -> pass
