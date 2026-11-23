# Wind Date And Time Picker Controls

## Goal

Make Wind Data date and time fields easier and safer to edit:

- Main Wind Data `Date` field opens the same popup calendar behavior used by the Autofill Wind/Temp Data modal.
- Main Wind Data start/end `Time` fields become dropdown menus with 5-minute choices from `1:00` through `12:55`.
- Autofill Wind/Temp Data modal start/end `Time` fields also become the same 5-minute dropdown controls.
- Main UI `AM/PM` controls remain visually and behaviorally separate.
- Selected report date continues to output in the existing `yyyy_MM_dd` format expected by Wind Report Info.

## Scope

- `src/purway_geotagger/gui/pages/wind_data_page.py`
- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
- Related Wind UI tests under `tests/`
- Any small shared GUI helper needed to avoid duplicating calendar or time-option code

## Non-Goals

- Do not change generated DOCX template placeholders or output formatting.
- Do not remove or redesign the existing `AM/PM` dropdowns.
- Do not change Wind Summary string formatting.
- Do not change weather provider/autofill lookup behavior.
- Do not visually redesign the Wind page or Autofill modal.

## Current Behavior / Evidence

- The main Wind Data page currently builds the Report Info date field as a visible `QDateEdit`, enables its calendar popup, displays `yyyy_MM_dd`, and defaults to the current date. Source: `src/purway_geotagger/gui/pages/wind_data_page.py:260`.
- Main Wind Data metadata still reads the report date as `self.date_edit.date().toString("yyyy_MM_dd")`, which must remain the output contract. Source: `src/purway_geotagger/gui/pages/wind_data_page.py:497`.
- The Autofill modal currently has a hidden `QDateEdit`, a readonly `QLineEdit` display, a `Pick Date` button, and a custom `QMenu` containing `QCalendarWidget`. Source: `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py:87`.
- The Autofill modal hides the calendar menu immediately after a date is selected. Source: `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py:471`.
- Main Wind Data time controls are currently `QTimeEdit` fields wrapped with custom steppers. Source: `src/purway_geotagger/gui/widgets/wind_entry_grid.py:60`.
- Main Wind Data time conversion currently reads the `QTimeEdit` value plus the separate `AM/PM` combo and converts it to 24-hour text. Source: `src/purway_geotagger/gui/widgets/wind_entry_grid.py:248`.
- Autofill modal start/end time controls are also currently `QTimeEdit` fields wrapped with custom steppers. Source: `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py:139` and `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py:300`.
- Existing tests verify 24-hour conversion and autofill time sync through direct `QTimeEdit` manipulation, so they will need updates when controls change. Sources: `tests/test_wind_page_preview_behavior.py:58`, `tests/test_wind_page_preview_behavior.py:145`, and `tests/test_wind_autofill_dialog.py:72`.

## Design

- Extract the Autofill modal calendar popup behavior into a reusable Wind date picker helper or widget.
- Keep the main Wind Data date field visually unchanged where possible. The interactive area inside the field should open the shared popup calendar, not require a separate visible button.
- The popup should close after selection and update the same underlying date value used by `_build_metadata()`.
- Replace main and Autofill `QTimeEdit` fields with `QComboBox` time dropdowns using identical option generation.
- Generate time options as display strings:
  - `1:00`, `1:05`, `1:10`, ... `12:55`
  - Include every 5-minute interval for 12 hours.
- Preserve the separate `AM/PM` controls as the source of meridiem.
- Preserve existing public behavior where callers can ask for start/end time in 24-hour format.
- Replace direct `QTimeEdit` APIs with a small internal abstraction such as:
  - selected hour/minute parser from combo text
  - `set_times_from_24h(...)` mapping `HH:MM` to display time plus meridiem
  - `start_time_24h_text()` and `end_time_24h_text()` remaining stable
- Remove or retire time-normalization code that only exists for free-typed `QTimeEdit` overflow input, unless a backward-compatible shim is needed for tests during transition.

## Compatibility Notes

- Must work on both macOS and Windows with PySide6.
- Use Qt widgets only; do not introduce OS-specific calendar or time picker dependencies.
- Avoid assumptions about system locale date formatting. Continue explicitly using `yyyy_MM_dd`.
- Do not rely on shell commands or platform-specific PATH behavior.
- If a reusable helper is added, place it under `src/purway_geotagger/gui/widgets/` to match current GUI organization.
- Keep visual styling compatible with existing style sheet classes and both platforms' Qt rendering.

## Implementation Phases

### Phase 1 - Shared Picker Design

- [ ] Identify exact reusable calendar behavior from Autofill modal.
- [ ] Decide whether to implement a reusable widget or helper functions.
- [ ] Define shared 5-minute time-option generator.
- [ ] Update this plan with final helper/widget choice.

Gate: Shared date picker and time dropdown approach is documented before code changes.

### Phase 2 - Main Wind Data Date Picker

- [ ] Reuse shared calendar popup for the main Report Info date field.
- [ ] Ensure clicking inside the field opens the popup.
- [ ] Ensure the popup closes after selection.
- [ ] Preserve `yyyy_MM_dd` output from `_build_metadata()`.
- [ ] Add or update tests for date selection behavior.

Gate: Main Wind Data date selection is verified without changing expected date format.

### Phase 3 - Main Wind Data Time Dropdowns

- [ ] Replace main Wind Data start/end `QTimeEdit` fields with 5-minute dropdowns.
- [ ] Preserve separate `AM/PM` combos.
- [ ] Preserve start/end 24-hour text APIs.
- [ ] Update preview refresh wiring.
- [ ] Update tests that currently manipulate `QTimeEdit` directly.

Gate: Main Wind Data preview and validation produce the same time strings for equivalent selections.

### Phase 4 - Autofill Modal Time Dropdowns

- [ ] Replace Autofill modal start/end `QTimeEdit` fields with the shared 5-minute dropdowns.
- [ ] Preserve selected start/end 24-hour outputs.
- [ ] Preserve syncing selected Autofill times back to the main Wind Data UI.
- [ ] Update Autofill modal tests.

Gate: Autofill modal start/end selections still feed provider requests and main UI sync correctly.

### Phase 5 - Verification And Documentation

- [ ] Run targeted Wind UI tests.
- [ ] Run at least one offscreen startup/open-close test for the Autofill modal.
- [ ] Manually verify popup open/select/close behavior on the local platform.
- [ ] Record test commands and results in this plan's Phase Notes.

Gate: All targeted tests pass, or any failures are documented with follow-up context.

## Verification Plan

- `pytest tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_autofill_dialog.py`
- Manual Qt/offscreen smoke test that opens `WindDataPage`, opens date picker, selects a date, and verifies `yyyy_MM_dd`.
- Manual interactive check on Windows local environment.
- GitHub Actions must continue to pass on Windows and macOS runners.

## Risks / Open Questions

- The main date field is requested to remain visually unchanged, while the Autofill modal currently uses a display field plus `Pick Date` button. Implementation should reuse popup behavior without copying the extra visible button into the main UI.
- Existing tests use direct `QTimeEdit` APIs. Updating tests should verify behavior, not preserve old implementation details.
- Confirm whether keyboard entry for time is no longer required. The request specifies dropdown menus, so the plan assumes dropdown-only selection is acceptable.

## Phase Notes

- 2026-06-19: Planning file created from user request. No implementation or tests run in this phase.

## Source Of Authority

- User request dated 2026-06-19.
- `markdown_planning/00-Task-Requirements.md`
- Repository root `AGENTS.md`
