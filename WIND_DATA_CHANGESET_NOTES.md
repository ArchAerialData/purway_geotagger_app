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

## Change Set WS0/WS1/WS2 - Weather Autofill Spike (Contract Lock + Core + UI Thin Slice)

### Added
- `src/purway_geotagger/core/wind_weather_autofill.py`
- `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
- `tests/test_wind_weather_autofill.py`
- `tests/test_wind_autofill_dialog.py`

### Modified
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- `src/purway_geotagger/gui/workers.py`
- `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md`
- `WIND_DATA_IMPLEMENTATION_PHASES.md`

### Key updates
- Locked WS0 weather-autofill provider/contract decisions in the spike plan:
  - NWS observations for retrospective weather values.
  - Open-Meteo geocoding for search/suggestions.
  - Partial-fill behavior when one or more fields are missing.
  - 30-minute input support via nearest-observation mapping.
- Implemented WS1 core service module with swappable HTTP client abstractions:
  - location suggestion model
  - NWS observation retrieval/mapping
  - unit conversion to mph and F
  - direction degree-to-compass normalization
  - robust provider/location errors
- Added isolated WS1 tests with mocked HTTP responses for deterministic behavior.
- Implemented WS2 GUI thin slice:
  - `Autofill Wind/Temp Data…` action in Wind Inputs.
  - Debounced location search dialog with explicit suggestion selection.
  - Popup now includes explicit Start/End target time selectors (AM/PM) used for API lookup.
  - Worker-thread execution for both search and data fetch (no UI-thread API blocking).
  - Start/End partial-fill mapping that preserves manual values when provider fields are missing.
  - Status messaging for success, partial-fill warnings, and provider failures.
  - Search dialog now keeps typing/backspace fully interactive while suggestions refresh.
  - Geocoding results are constrained to U.S. locations only.
  - ZIP display now prefers the exact ZIP entered by the pilot when available (avoids unrelated first-postcode display).
  - Added source-verification URL capture from the exact NWS station observations query used for autofill.
  - Added `Open Autofill Source URL` action so pilots can manually validate retrieved values against the source endpoint.

### Rollback block (WS0/WS1/WS2 only)
- Remove:
  - `src/purway_geotagger/core/wind_weather_autofill.py`
  - `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
  - `tests/test_wind_weather_autofill.py`
  - `tests/test_wind_autofill_dialog.py`
- Revert weather autofill integration updates in:
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
  - `src/purway_geotagger/gui/workers.py`
  - `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
- Revert weather spike planning/status updates in:
  - `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md`
  - `WIND_DATA_IMPLEMENTATION_PHASES.md`

---

## Change Set WS2.1 - Autofill Worker Lifecycle Crash Fix

### Modified
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `tests/test_wind_autofill_dialog.py`

### Key updates
- Fixed a worker-lifecycle race that could crash on autofill selection (`QThread: Destroyed while thread is still running`).
- Updated autofill worker cleanup to be instance-specific:
  - `finished` now passes the finished worker instance into cleanup.
  - cleanup only clears `self._autofill_fill_worker` when the finished worker matches the currently tracked instance.
- Added regression coverage to ensure stale worker completions cannot clear/delete the active worker reference.

### Rollback block (WS2.1 only)
- Revert:
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `tests/test_wind_autofill_dialog.py`

---

## Change Set WS2.2 - Autofill Button Header Alignment

### Modified
- `src/purway_geotagger/gui/pages/wind_data_page.py`

### Key updates
- Moved `Autofill Wind/Temp Data…` from a standalone row into the `2) Wind Inputs` header row.
- Kept button styling/behavior unchanged and right-aligned it opposite the section title.
- Restored vertical space so the Wind input grid sits higher in the card.

### Rollback block (WS2.2 only)
- Revert:
  - `src/purway_geotagger/gui/pages/wind_data_page.py`

---

## Change Set WS2.3 - Time Control Consistency + 24h Overflow Normalization

### Modified
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- `tests/test_wind_autofill_dialog.py`
- `tests/test_wind_page_preview_behavior.py`

### Key updates
- Added fixed minimum height to the Wind Inputs header row so title/button alignment remains stable across themes and font rendering.
- Updated Autofill popup target-time controls to use the same custom `MacStepper` look/feel as the main Wind Inputs grid.
- Removed native popup time steppers to avoid mixed control styles.
- Added cross-page time overflow normalization for main Wind Inputs and popup Target Times:
  - typing `13`-`23` auto-converts to `1`-`11` and sets meridiem to `PM`,
  - typing `24` normalizes to `12:00 PM`,
  - typing `0` converts to `12` with meridiem `AM`.
- Preserved 24-hour backend mapping correctness (example: `10:30 PM` resolves to `22:30`).
- Added regression tests for both popup and main-page 24h-to-12h normalization behavior.

### Rollback block (WS2.3 only)
- Revert:
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
  - `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
  - `tests/test_wind_autofill_dialog.py`
  - `tests/test_wind_page_preview_behavior.py`

---

## Change Set WS2.5 - Historical Autofill Reliability + Date Picker Popover

### Modified
- `src/purway_geotagger/core/wind_weather_autofill.py`
- `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/style_sheet.py`
- `tests/test_wind_weather_autofill.py`

### Key updates
- Added automatic historical-data fallback when NWS station observations are unavailable for selected date/time windows.
  - Primary provider remains NWS observations.
  - Fallback provider is Open-Meteo historical archive (hourly).
- Added clearer failure messaging when both providers cannot return observations.
- Added provider warning text when fallback is used so pilots can see data provenance.
- Added styled date-picker control in Autofill popup:
  - date display + `Pick Date` button
  - themed calendar popover matching app light/dark palette
  - retains current-year-through-today bounds
- Added/updated tests for archive fallback behavior and no-observation failure behavior.

### Rollback block (WS2.5 only)
- Revert:
  - `src/purway_geotagger/core/wind_weather_autofill.py`
  - `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `src/purway_geotagger/gui/style_sheet.py`
  - `tests/test_wind_weather_autofill.py`

---

## Change Set WS2.4 - Autofill Report-Date Bounds + Main Date Sync

### Modified
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
- `tests/test_wind_autofill_dialog.py`
- `tests/test_wind_page_preview_behavior.py`

### Key updates
- Added explicit `Report Date` selector in the autofill popup UI.
- Constrained popup report date to:
  - minimum: January 1 of current year
  - maximum: current date (no future dates).
- Autofill request now uses popup-selected report date instead of implicitly using only the main page date.
- Main Wind page `Date` field is synchronized to the popup-selected report date when autofill starts, preventing date mismatch between retrieved observations and generated report placeholders.
- Added regression tests to verify date-window clamping and main-page date handoff into the popup.

### Rollback block (WS2.4 only)
- Revert:
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
  - `tests/test_wind_autofill_dialog.py`
  - `tests/test_wind_page_preview_behavior.py`

---

## Change Set GUI-S1 - Settings Dialog Refresh (Sections + Practical Defaults)

### Modified
- `src/purway_geotagger/gui/widgets/settings_dialog.py`
- `tests/test_settings_dialog.py`

### Key updates
- Rebuilt Settings dialog into grouped sections:
  - Run Defaults
  - Processing + Metadata
  - Confirmations + Theme
  - Tool Paths
- Exposed existing `AppSettings` fields that were previously not editable in dialog:
  - overwrite/flatten/sort/dry-run defaults
  - confirmation toggles for methane/encroachment/combined
  - theme selection (`light`/`dark`)
  - backup/write-XMP/join-delta/PPM edge controls
  - ExifTool path
- Added `Reset Defaults` action to quickly return controls to baseline defaults before saving.
- Added tests covering save behavior for extended fields and reset-default control behavior.

### Rollback block (GUI-S1 only)
- Revert:
  - `src/purway_geotagger/gui/widgets/settings_dialog.py`
  - `tests/test_settings_dialog.py`

---

## Change Set GUI-S2 - Settings UI Fit + Control Polish

### Added
- `assets/icons/checkmark_white.svg`
- `assets/icons/checkmark_blue.svg`
- `assets/icons/checkmark_white.png`
- `assets/icons/checkmark_blue.png`

### Modified
- `src/purway_geotagger/gui/widgets/settings_dialog.py`
- `src/purway_geotagger/gui/style_sheet.py`

### Key updates
- Made Settings dialog content scrollable so long section text/help cannot be visually clipped on smaller windows.
- Increased default Settings dialog size for better first-open readability.
- Replaced native `QSpinBox` arrows for `Max join delta` with the shared custom `MacStepper` control used in Wind UI.
- Added settings-specific checkbox styling (`cssClass="settings_checkbox"`) to avoid harsh solid-blue checked blocks and improve checked/unchecked clarity in both themes.
- Restored explicit visual checkmarks for checked checkbox states via packaged indicator icons in QSS.
- Switched checkbox indicator icons from SVG to PNG for more reliable Qt stylesheet rendering across environments.

### Rollback block (GUI-S2 only)
- Remove:
  - `assets/icons/checkmark_white.svg`
  - `assets/icons/checkmark_blue.svg`
  - `assets/icons/checkmark_white.png`
  - `assets/icons/checkmark_blue.png`
- Revert:
  - `src/purway_geotagger/gui/widgets/settings_dialog.py`
  - `src/purway_geotagger/gui/style_sheet.py`

---

## Change Set WS2.6 - Template Label Clarity + Autofill Calendar/Time Sync

### Modified
- `src/purway_geotagger/gui/main_window.py`
- `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- `tests/test_main_window_startup.py`
- `tests/test_wind_autofill_dialog.py`
- `tests/test_wind_page_preview_behavior.py`

### Key updates
- Templates tab list now shows filename-style index preview instead of backend wording:
  - from `Start 0001`
  - to `{CLIENT_ABBR}_{INDEX}` (for example `WWM_0001`).
- Autofill popup calendar styling polish:
  - removed platform-default weekend red text by forcing weekday/weekend text to theme color,
  - increased calendar/menu dimensions to avoid cramped/cut-off layout in the date popover.
- Autofill popup Start/End target times are now pushed into main Wind Inputs when autofill is launched, so main page time controls stay in sync with popup selections.

### Rollback block (WS2.6 only)
- Revert:
  - `src/purway_geotagger/gui/main_window.py`
  - `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
  - `src/purway_geotagger/gui/pages/wind_data_page.py`
  - `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
  - `tests/test_main_window_startup.py`
  - `tests/test_wind_autofill_dialog.py`
  - `tests/test_wind_page_preview_behavior.py`

---

## Change Set WS2.7 - Calendar Hover Polish + Month Arrow Alignment

### Modified
- `src/purway_geotagger/gui/style_sheet.py`

### Key updates
- Refined date-picker popover navigation bar sizing and spacing for cleaner alignment.
- Added explicit month/year button sizing and padding in the calendar header.
- Repositioned month dropdown indicator (`menu-indicator`) to right-center so it sits aligned with the month label instead of clipping/drooping.
- Added richer calendar hover feedback:
  - nav button hover/pressed states,
  - day-cell hover state for clearer pointer targeting.

### Rollback block (WS2.7 only)
- Revert:
  - `src/purway_geotagger/gui/style_sheet.py`

---

## Validation Snapshot

- `python3 -m pytest tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_main_window_startup.py tests/test_wind_template_contract.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py` -> 30 passed
- `python3 -m pytest tests/test_wind_weather_autofill.py` -> 6 passed
- `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py` -> 35 passed
- `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py` -> 36 passed
- `python3 -m pytest tests/test_main_window_startup.py tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py` -> 37 passed
- `python3 -m pytest tests/test_wind_autofill_dialog.py tests/test_wind_weather_autofill.py tests/test_wind_page_preview_behavior.py tests/test_wind_page_logic.py` -> 20 passed
- `python3 -m pytest tests/test_wind_autofill_dialog.py tests/test_wind_page_preview_behavior.py tests/test_wind_page_logic.py tests/test_wind_weather_autofill.py` -> 22 passed
- `python3 -m pytest tests/test_main_window_startup.py tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py` -> 42 passed
- `python3 -m pytest tests/test_wind_autofill_dialog.py tests/test_wind_page_preview_behavior.py tests/test_settings_dialog.py` -> 11 passed
- `python3 -m pytest tests/test_main_window_startup.py tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py tests/test_settings_dialog.py` -> 46 passed
- `python3 -m compileall src` -> pass
- `python3 -m pytest tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py tests/test_wind_page_preview_behavior.py tests/test_main_window_startup.py` -> 17 passed
- `PYTHONPATH=src python3 -m pytest tests/test_main_window_startup.py tests/test_wind_autofill_dialog.py tests/test_wind_page_preview_behavior.py` -> 13 passed
