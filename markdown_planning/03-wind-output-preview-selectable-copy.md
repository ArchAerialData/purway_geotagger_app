# Wind Output Preview Selectable Copy

## Goal

Allow users to highlight and copy populated `3) Output Preview` time values and Wind Summary strings from the Wind Data page, without changing the visual appearance.

## Scope

- `3) Output Preview` section on the main Wind Data page.
- Start and End preview time labels.
- Start and End preview summary labels.
- Tests or smoke checks for text interaction and copied/displayed values.

## Non-Goals

- Do not add visible copy buttons.
- Do not redesign preview rows, spacing, colors, or typography.
- Do not change Wind Summary formatting.
- Do not change generated DOCX output.
- Do not make unrelated labels selectable unless needed for this behavior.

## Current Behavior / Evidence

- The Output Preview card is built in `src/purway_geotagger/gui/pages/wind_data_page.py`, section label `3) Output Preview`. Source: `src/purway_geotagger/gui/pages/wind_data_page.py:331`.
- Preview rows currently use `QLabel` widgets for time and summary values. Source: `src/purway_geotagger/gui/pages/wind_data_page.py:389`.
- `_refresh_preview()` populates those labels with `preview_payload.s_time`, `preview_payload.s_string`, `preview_payload.e_time`, and `preview_payload.e_string`. Source: `src/purway_geotagger/gui/pages/wind_data_page.py:546`.
- Existing tests assert displayed preview strings such as `10:00am` and a wind summary ending in `51 degrees F` format in code as `51\u00B0F`. Source: `tests/test_wind_page_preview_behavior.py:9`.
- There is no `setTextInteractionFlags` usage in the preview row construction today. Source: repository search for `setTextInteractionFlags` in `src/purway_geotagger/gui/pages/wind_data_page.py` on 2026-06-19.

## Design

- Keep `QLabel` widgets if they can provide the required selection behavior without visual changes.
- Set text interaction flags on the preview value labels so users can select text with the mouse and copy it.
- Candidate flags:
  - `Qt.TextSelectableByMouse`
  - optionally `Qt.TextSelectableByKeyboard` if it does not introduce visible focus styling
- Preserve alignment, word wrapping, fixed widths, cssClass properties, and text values.
- Ensure the copied text exactly matches the label text currently displayed.
- Do not add rich text unless needed; plain text labels are preferred to avoid copy-format surprises.

## Compatibility Notes

- Must work on macOS and Windows with PySide6 clipboard behavior.
- Do not use platform-specific clipboard APIs.
- Visual appearance should remain unchanged across both platforms.
- If focus rectangles appear on one platform after enabling keyboard selection, prefer mouse-only selection unless keyboard selection is explicitly needed.

## Implementation Phases

### Phase 1 - Selectability Prototype

- [ ] Confirm `QLabel` text selection can be enabled without visual changes.
- [ ] Determine whether mouse-only or mouse-plus-keyboard selection is appropriate.
- [ ] Update this plan if a different widget is required.

Gate: Implementation approach preserves visual appearance.

### Phase 2 - Apply To Preview Values

- [ ] Enable selection on start time preview.
- [ ] Enable selection on start summary preview.
- [ ] Enable selection on end time preview.
- [ ] Enable selection on end summary preview.
- [ ] Keep placeholder behavior unchanged when preview is not populated.

Gate: All populated preview output values can be highlighted.

### Phase 3 - Verification

- [ ] Add or update an offscreen test that checks text interaction flags.
- [ ] Verify displayed strings remain unchanged.
- [ ] Manually verify highlight and copy/paste behavior.
- [ ] Record verification results in this plan's Phase Notes.

Gate: Copyable text behavior is verified without visual or formatting regressions.

## Verification Plan

- `pytest tests/test_wind_page_preview_behavior.py`
- New or updated test asserting preview labels have text selection enabled.
- Manual check: populate Output Preview, highlight time and summary strings, copy, and paste into a text field to confirm exact displayed text.
- GitHub Actions must continue to pass on macOS and Windows.

## Risks / Open Questions

- QLabel selection can introduce focus or cursor behavior depending on platform and style. If that creates visible changes, use the least intrusive text interaction flags.
- Exact copied value should be the displayed label text, not hidden normalized values.

## Phase Notes

- 2026-06-19: Planning file created from user request. No implementation or tests run in this phase.

## Source Of Authority

- User request dated 2026-06-19.
- `markdown_planning/00-Task-Requirements.md`
- Repository root `AGENTS.md`
