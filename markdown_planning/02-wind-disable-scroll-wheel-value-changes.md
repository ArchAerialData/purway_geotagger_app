# Wind Disable Scroll Wheel Value Changes

## Goal

Prevent mouse-wheel scrolling from changing Wind Data page field values while users scroll the page or Autofill Wind/Temp Data modal.

## Scope

- Main Wind Data page controls that can change value from wheel events.
- Autofill Wind/Temp Data modal controls that can change value from wheel events.
- Reusable GUI helper or event filter if needed.
- Tests that verify wheel events do not mutate field values.

## Non-Goals

- Do not remove normal mouse click, keyboard, dropdown, or custom stepper behavior.
- Do not change visual styling.
- Do not disable page or modal scrolling.
- Do not alter generated Wind report output.

## Current Behavior / Evidence

- Main Wind Data start/end time, meridiem, speed, gust, and temp controls are wired as editable value controls. Source: `src/purway_geotagger/gui/widgets/wind_entry_grid.py:110`.
- Main Wind Data currently uses `QSpinBox` for speed, gust, and temperature, and `QComboBox` for `AM/PM`. Source: `src/purway_geotagger/gui/widgets/wind_entry_grid.py:393` and `src/purway_geotagger/gui/widgets/wind_entry_grid.py:407`.
- Main Wind Data currently uses `QTimeEdit` for time fields. Source: `src/purway_geotagger/gui/widgets/wind_entry_grid.py:384`.
- Autofill modal currently uses `QTimeEdit` for start/end time and `QComboBox` for `AM/PM`. Source: `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py:300` and `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py:323`.
- A repository search found no existing Wind GUI `wheelEvent`, `Wheel`, or `eventFilter` handling for these widgets. Source: `rg -n "wheelEvent|Wheel|setFocusPolicy|StrongFocus|NoFocus|eventFilter" src/purway_geotagger/gui -S` run on 2026-06-19.
- The related date/time picker plan will convert time fields from `QTimeEdit` to `QComboBox`, so this work should cover the final widget set after that change.

## Design

- Add a reusable wheel-blocking helper for value controls in Wind UI.
- Preferred implementation: install an event filter on specific value widgets that ignores `QEvent.Wheel` when the widget is not an intentional scroll surface.
- Apply the helper to:
  - main Wind Data time dropdowns
  - main Wind Data `AM/PM` dropdowns
  - main Wind Data speed/gust/temp spin boxes
  - Autofill modal time dropdowns
  - Autofill modal `AM/PM` dropdowns
  - any date picker display/control that would otherwise mutate on wheel while focused
- Keep custom `MacStepper` clicks working because those are explicit value changes.
- If Qt still routes wheel events to focused child controls during page scroll, the event filter should consume the wheel event for the control and allow surrounding scroll areas to handle user scrolling where possible.

## Compatibility Notes

- Must work on macOS and Windows with PySide6.
- Do not use platform-specific event APIs.
- Keep behavior compatible with packaged macOS `.app` launches.
- Avoid global application event filters unless a widget-scoped helper is insufficient.
- Wheel behavior can vary by mouse, trackpad, and Qt platform plugin, so tests should verify no value mutation at the widget level and manual checks should cover page scrolling.

## Implementation Phases

### Phase 1 - Inventory Affected Controls

- [ ] Confirm final time widgets after `01-wind-date-time-picker-controls.md`.
- [ ] Inventory all Wind page and Autofill modal value widgets that accept wheel events.
- [ ] Decide helper location and API.
- [ ] Update this plan if additional controls are discovered.

Gate: Affected control list is complete for the final UI widget set.

### Phase 2 - Implement Reusable Wheel Guard

- [ ] Add a small helper/event filter under `src/purway_geotagger/gui/widgets/` or another existing GUI utility location.
- [ ] Ensure the helper consumes wheel value changes without blocking explicit clicks, typing, dropdown selection, or steppers.
- [ ] Add focused unit or offscreen Qt coverage for the helper.

Gate: Helper blocks wheel-driven value mutation in an isolated test.

### Phase 3 - Apply To Main Wind Data UI

- [ ] Apply wheel guard to main Wind Data time dropdowns.
- [ ] Apply wheel guard to main Wind Data `AM/PM` dropdowns.
- [ ] Apply wheel guard to main Wind Data speed/gust/temp spin boxes.
- [ ] Verify page scrolling still works.

Gate: Main Wind Data fields no longer change from wheel scrolling.

### Phase 4 - Apply To Autofill Modal

- [ ] Apply wheel guard to Autofill modal time dropdowns.
- [ ] Apply wheel guard to Autofill modal `AM/PM` dropdowns.
- [ ] Verify modal scrolling and ordinary interaction still work.

Gate: Autofill modal fields no longer change from wheel scrolling.

### Phase 5 - Verification And Phase Notes

- [ ] Run targeted Wind UI tests.
- [ ] Add or update tests that simulate wheel events on guarded controls.
- [ ] Manually verify page and modal scrolling behavior.
- [ ] Record verification results in this plan's Phase Notes.

Gate: Tests and manual checks confirm scroll wheel no longer changes values.

## Verification Plan

- `pytest tests/test_wind_page_preview_behavior.py tests/test_wind_autofill_dialog.py`
- New focused test for wheel event suppression on dropdowns and spin boxes.
- Manual check: scroll over Wind Data controls and Autofill modal controls with focus present and verify values do not change.
- GitHub Actions must continue to pass on macOS and Windows.

## Risks / Open Questions

- Consuming wheel events at the control may prevent the parent scroll area from receiving the same event. If that happens, implementation may need to forward or ignore carefully so page scrolling remains smooth.
- Coordinate this after or alongside the date/time picker task so time controls are not guarded twice across old and new widget types.

## Phase Notes

- 2026-06-19: Planning file created from user request. No implementation or tests run in this phase.

## Source Of Authority

- User request dated 2026-06-19.
- `markdown_planning/00-Task-Requirements.md`
- Repository root `AGENTS.md`
