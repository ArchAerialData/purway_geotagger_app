# GUI Theme Change Set Notes (2026-02-06)

This file documents the GUI updates as isolated change sets so each set can be reverted independently.

## Revert strategy

- Before commit: revert a set with `git restore <files...>`.
- After commit: revert a set by restoring the same files from the pre-change commit:
  - `git checkout <commit-before-change> -- <files...>`

## CHG-001: Contrast-safe theme tokens + stronger card/section boundaries

- Purpose: improve light/dark contrast and make cards/sections visually distinct.
- Files:
  - `src/purway_geotagger/gui/style_sheet.py`
  - `src/purway_geotagger/gui/main_window.py`
- Markers in code:
  - `GUI_CHANGESET_A11Y_001`
  - `GUI_CHANGESET_A11Y_002`
- Key updates:
  - New semantic tokens (`text_muted`, `status_*`, button fg/bg roles, `card_border`, table tokens).
  - Better default button/read-only/input/disabled/focus styling.
  - Header border moved into shared QSS (`QWidget#mainHeader`).
  - Jobs table switched to alternating rows for readability.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/style_sheet.py src/purway_geotagger/gui/main_window.py`

## CHG-002: Remove hardcoded page colors and use theme-driven status classes

- Purpose: prevent light/dark drift caused by inline color literals and unsupported style tricks.
- Files:
  - `src/purway_geotagger/gui/pages/home_page.py`
  - `src/purway_geotagger/gui/pages/help_page.py`
- Key updates:
  - Home status labels/icons now use shared `status_*` classes.
  - Last-used mode label now uses theme-aware info styling.
  - Help page tip/title/body text now uses shared classes (`label_strong`, `muted`, `subtitle`) instead of inline styles.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/pages/home_page.py src/purway_geotagger/gui/pages/help_page.py`

## CHG-003: Unified table polish across report/preview dialogs

- Purpose: consistent readability for tables in both themes.
- Files:
  - `src/purway_geotagger/gui/widgets/run_report_view.py`
  - `src/purway_geotagger/gui/widgets/preview_dialog.py`
  - `src/purway_geotagger/gui/widgets/schema_dialog.py`
- Key updates:
  - Applied shared table class usage and alternating rows.
  - Standardized row/header behavior on failure/preview/schema tables.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/widgets/run_report_view.py src/purway_geotagger/gui/widgets/preview_dialog.py src/purway_geotagger/gui/widgets/schema_dialog.py`

## CHG-004: Combined wizard duplicate-note cleanup

- Purpose: remove duplicated helper note in confirm step.
- Files:
  - `src/purway_geotagger/gui/pages/combined_wizard.py`
- Revert only this set:
  - `git restore src/purway_geotagger/gui/pages/combined_wizard.py`

## CHG-005: Theme contrast regression guard test

- Purpose: enforce minimum contrast for critical token pairs in CI/local tests.
- Files:
  - `tests/test_gui_theme_contrast.py`
- Revert only this set:
  - `git restore tests/test_gui_theme_contrast.py`

## CHG-006: Sticky nav redesign (left anchor + pill controls + breadcrumbs)

- Purpose: remove janky centered nav placement, improve icon quality, and align nav visuals with app theme.
- Files:
  - `src/purway_geotagger/gui/widgets/sticky_nav_row.py`
  - `src/purway_geotagger/gui/style_sheet.py`
  - `src/purway_geotagger/gui/pages/methane_page.py`
  - `src/purway_geotagger/gui/pages/encroachment_page.py`
  - `src/purway_geotagger/gui/pages/combined_wizard.py`
- Key updates:
  - Custom palette-aware Back/Home icons replace generic style icons.
  - Sticky nav buttons restyled as compact pills with clearer hover/press/focus states.
  - Methane/Encroachment nav rows are explicitly left-anchored and no longer float.
  - Breadcrumb context labels added: `Run / Methane`, `Run / Encroachment`, `Run / Combined`.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/widgets/sticky_nav_row.py src/purway_geotagger/gui/style_sheet.py src/purway_geotagger/gui/pages/methane_page.py src/purway_geotagger/gui/pages/encroachment_page.py src/purway_geotagger/gui/pages/combined_wizard.py`

## CHG-007: Responsive sticky-nav spacing/margins for 13" vs 16" widths

- Purpose: improve nav/title spacing rhythm across common macOS laptop sizes without changing behavior.
- Files:
  - `src/purway_geotagger/gui/pages/methane_page.py`
  - `src/purway_geotagger/gui/pages/encroachment_page.py`
  - `src/purway_geotagger/gui/pages/combined_wizard.py`
- Key updates:
  - Added breakpoint-based margin/spacing tuning via `_apply_responsive_spacing(...)` + `resizeEvent(...)`.
  - Tuned side/top/content spacing for wide/medium/compact windows.
  - Breadcrumb labels auto-hide below `980px` width to prevent nav crowding.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/pages/methane_page.py src/purway_geotagger/gui/pages/encroachment_page.py src/purway_geotagger/gui/pages/combined_wizard.py`

## CHG-008: Help page content redesign + responsive mode cards

- Purpose: make Help content easier to scan for first-time users while keeping key task guidance concise.
- Files:
  - `src/purway_geotagger/gui/pages/help_page.py`
- Key updates:
  - Reorganized content into: Quick Start, Mode chooser, Feature Reference, and Troubleshooting.
  - Streamlined wording to focus on run flow, mode intent, and where to look when a run fails.
  - Added responsive mode-card layout (horizontal on wide windows, stacked on narrower windows).
- Revert only this set:
  - `git restore src/purway_geotagger/gui/pages/help_page.py`

## CHG-009: Jobs tab simplification + advanced details workflow

- Purpose: reduce Jobs tab clutter for default users while preserving deeper diagnostics for advanced users.
- Files:
  - `src/purway_geotagger/gui/main_window.py`
  - `src/purway_geotagger/gui/models/job_table_model.py`
  - `src/purway_geotagger/gui/models/jobs_filter_proxy_model.py`
  - `src/purway_geotagger/gui/style_sheet.py`
- Key updates:
  - Added simplified default jobs table columns with mode/started/status/progress/output focus.
  - Added `JobsFilterProxyModel` for status filters, search, and recent-job limiting (default 20).
  - Added quick filter chips (`All`, `Running`, `Failed`, `Completed`) and search input.
  - Added `Show all history`, `Show advanced columns`, and `Show details panel` toggles.
  - Replaced crowded action row with contextual primary actions + `More` menu.
  - Added collapsible Job Details panel with status badge and full run metrics.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/main_window.py src/purway_geotagger/gui/models/job_table_model.py src/purway_geotagger/gui/models/jobs_filter_proxy_model.py src/purway_geotagger/gui/style_sheet.py`

## CHG-010: macOS Qt startup crash guard for Jobs table header sizing

- Purpose: prevent launch-time segmentation faults on macOS/Qt 6.7 caused by calling `QHeaderView.setSectionResizeMode(...)` before model sections exist.
- Files:
  - `src/purway_geotagger/gui/main_window.py`
  - `tests/test_main_window_startup.py`
- Key updates:
  - Moved jobs-table section resize configuration to run only after `setModel(...)`.
  - Added `_configure_jobs_table_columns()` with section-count guards.
  - Updated resize mode enum usage to `QHeaderView.ResizeMode.*`.
  - Added subprocess startup regression test using `QT_QPA_PLATFORM=offscreen`.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/main_window.py tests/test_main_window_startup.py`

## CHG-011: Template UI simplification (pilot-friendly labels only)

- Purpose: remove backend template syntax/jargon from Templates views and show only pilot-relevant values.
- Files:
  - `src/purway_geotagger/gui/main_window.py`
  - `src/purway_geotagger/gui/widgets/template_editor.py`
- Key updates:
  - Templates tab list now shows `Client Name`, `Client Abbreviation`, and `Starting Index` instead of template IDs and raw `{client}_{index...}` pattern syntax.
  - Template Editor removed token-reference helper text from the main flow.
  - Suffix field placeholder now uses plain language (`Optional suffix, e.g. _AREA`).
  - Preview labels now show pilot-facing wording (`Output format`, `Example output`) instead of backend pattern labels.
  - Pattern-related error wording changed to generic template/preview wording.
- Revert only this set:
  - `git restore src/purway_geotagger/gui/main_window.py src/purway_geotagger/gui/widgets/template_editor.py`
