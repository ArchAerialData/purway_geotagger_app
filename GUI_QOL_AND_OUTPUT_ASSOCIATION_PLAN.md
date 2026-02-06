# GUI QoL + Methane Output Association Plan

Date created: 2026-02-05

## Context
After recent GUI + pipeline work, several usability and output-correctness issues were identified. This plan defines **phased**, testable fixes that preserve macOS compatibility and existing repo organization.

This plan is **additive** and does not replace `GUI_HOME_PAGE_AND_MODES_PLAN.md`.

## Non‑Negotiables / Constraints
- **macOS-first**: app must behave correctly when launched from Finder / packaged `.app` (minimal PATH assumptions).
- **Do not alter the main header** in `src/purway_geotagger/gui/main_window.py` (Run/Jobs/Templates/Help + theme toggle remain as-is).
- Keep long-running work off the UI thread (use existing worker/job pipeline).
- Prefer `pathlib` for paths; no shell-string subprocess calls.
- **Phase discipline (required):**
  - Each phase **must run its listed tests/verification**.
  - After a phase completes, **update this file with Phase Notes** (date, tests run, issues).
  - **Do not start the next phase** until the Phase Notes for the current phase are recorded.

## Assumptions (Call out now to avoid surprises)
- **CSV↔JPG association**: `file_name` (or equivalent) values in a methane CSV refer to JPGs located in the **same directory as that CSV** (matching current test structure).
  - If future data violates this (e.g., CSV in parent folder, photos in subfolder), we’ll extend matching to search within scanned photos under the input root.
- **Filename column is expected in methane CSVs** (per Purway format). If missing, fall back to PPM-only filtering as a failsafe and log the missing-column condition.

## Dependencies
- **No new Python dependencies** required for these changes (QDesktopServices is part of Qt).

---

## Issue 1 — Checkbox Visibility (Light + Dark Themes)
### Goal
Unchecked checkboxes must remain clearly visible in **light mode** and improved in **dark mode** across the entire app.

### Current Behavior
- In light theme, unchecked `QCheckBox` indicators can appear invisible (indicator blends into background).

### Implementation Notes
- Add explicit QSS rules for `QCheckBox::indicator` for both checked and unchecked states.
- Ensure indicator has:
  - visible border in light mode,
  - appropriate contrast in dark mode,
  - consistent sizing.

### Files
- Modify: `src/purway_geotagger/gui/style_sheet.py`

### Verification
- Manual: in both themes, verify unchecked + checked checkboxes are visible on:
  - Methane page (`src/purway_geotagger/gui/pages/methane_page.py`)
  - Encroachment page (`src/purway_geotagger/gui/pages/encroachment_page.py`)
  - Combined wizard (`src/purway_geotagger/gui/pages/combined_wizard.py`)
  - Template editor dialogs (where applicable)

---

## Issue 2 — Cleaned CSV + KMZ Must Only Include Rows With Matching JPGs
### Goal
Cleaned CSV and KMZ outputs must include **only** methane CSV rows that:
1) have **PPM >= threshold**, and  
2) have a **photo filename** that matches an actual JPG present for that CSV’s folder.

### Desired Behavior (Example)
- Folder contains 12 JPGs.
- 10 JPGs correspond to rows with PPM >= 1000.
- Methane CSV has 45 rows with PPM >= 1000.
- Cleaned CSV should contain **only the 10 rows** that correspond to the 10 qualifying JPGs.
- KMZ placemarks must match the cleaned CSV (i.e., also only those 10).

### Implementation Notes
- Update methane outputs generation to:
  - identify the “photo filename” column (use `PHOTO_COL_CANDIDATES`-style matching),
  - build a set of JPG basenames in the CSV’s directory (`*.jpg`, `*.jpeg`, case-insensitive),
  - filter rows by (PPM threshold AND filename exists in that set).
- If a CSV has **no photo/filename column**:
  - fall back to **PPM-only filtering** (current behavior),
  - log a warning and surface in GUI output viewer (rare edge case).
- For rows that reference **missing JPGs**:
  - exclude them from cleaned CSV/KMZ,
  - log missing filenames and expose counts in the GUI (output summary).
- Ensure recursive behavior remains intact because the scan already finds CSVs in subfolders; each CSV is processed independently.

### Files
- Modify: `src/purway_geotagger/ops/methane_outputs.py`
  - import: `PHOTO_COL_CANDIDATES` from `src/purway_geotagger/parsers/purway_csv.py`
  - add filename-column selection + JPG existence filtering
- Modify (if needed): `src/purway_geotagger/core/pipeline.py`
  - update logging text for methane output generation to mention JPG association filtering
- Add tests:
  - Add: `tests/test_methane_outputs_photo_association.py`
    - create temp folder with:
      - methane CSV containing rows above threshold with mixed `file_name` values,
      - a subset of JPG filenames present on disk,
      - assert cleaned CSV rows == qualifying JPGs count,
      - assert KMZ placemark count matches cleaned CSV.

### Verification
- Automated:
  - `python3 -m pytest tests/test_methane_outputs_photo_association.py`
- Manual:
  - run Methane mode on a known folder and confirm cleaned CSV rows correspond only to JPGs in that folder.

---

## Issue 3 — Run Button Right-Aligned + Green
### Goal
For Methane Only / Encroachment Only / Combined:
- Run button is **right-aligned**.
- Run button is visually a “go” action (green).

### Implementation Notes
- Add a new button style class in QSS, e.g. `cssClass="run"`:
  - background uses theme `success` color,
  - hover/pressed states are distinct,
  - disabled state remains clear.
- Update action-row layouts so the run button is on the far right.
- Combined wizard:
  - keep the **Next** button for steps 1–3,
  - change only the **final step button** to “Run Combined” and apply the green run style.

### Files
- Modify: `src/purway_geotagger/gui/style_sheet.py` (new `QPushButton[cssClass="run"]` rules)
- Modify: `src/purway_geotagger/gui/pages/methane_page.py`
- Modify: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Modify: `src/purway_geotagger/gui/pages/combined_wizard.py` (Run Combined uses `self.next_btn` on confirm step)

### Verification
- Manual: confirm run buttons are right-aligned and green in both themes.

---

## Issue 4 — “Run Another Folder” (Reset + Return Home)
### Goal
After a run completes (success or failure), show a completion-only action:
- “Run another folder”
  - returns to the Run home menu,
  - clears previously added inputs,
  - resets mode-specific fields to defaults (as if a fresh instance).

### Implementation Notes
- Implement explicit reset APIs per page:
  - `reset_for_new_run()` resets the page to **fresh-instance defaults**:
    - clear inputs list + drop zone
    - reset methane threshold + KMZ checkbox to defaults
    - reset log/output folder fields to defaults
    - reset encroachment renaming options + template selection
    - clear status/progress + last-run IDs
  - clears visual state (drop zone, list widgets, status text, progress).
- Add completion-only button near run button; hidden during idle/running.
- Keep Jobs history intact (this is only resetting the Run workflow UI inputs/options).

### Files
- Modify: `src/purway_geotagger/gui/pages/methane_page.py`
- Modify: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Modify: `src/purway_geotagger/gui/pages/combined_wizard.py`
- Modify: `src/purway_geotagger/gui/main_window.py`
  - provide a single method to return to home and trigger page reset (or connect signals).

### Verification
- Manual:
  - Complete a run, click “Run another folder”, verify:
    - home menu appears,
    - inputs list is empty,
    - prior selections are reset to defaults.

---

## Issue 5 — Post-Run Output Actions + In-App Output Viewer
### Goal
After completion, provide quick access to run outputs without Finder spelunking:
- A completion-only button to open the output location (where meaningful).
- A completion-only button “View Output Files” that opens an in-app viewer listing:
  - cleaned CSVs
  - KMZs
  - (optionally) run folder/logs and encroachment output folder
  - with per-row actions: **Open File** (default app) and optionally **Reveal in Finder**.

### Implementation Notes
- Reuse/extend the existing run report dialog:
  - `src/purway_geotagger/gui/widgets/run_report_view.py` already loads `run_summary.json` and parses failures.
  - Extend it to render an “Outputs” table sourced from `RunSummary.methane_outputs` and settings (encroachment output folder).
- Use `QDesktopServices.openUrl()` for opening files on macOS reliably.
- Keep “Open output folder” behavior:
  - Methane: open the **log/run folder** (single location); cleaned CSVs may live next to each methane CSV.
  - Encroachment: open **encroachment output folder**.
  - Combined: offer both (buttons or a small chooser dialog).
- Output viewer must show **all cleaned CSV/KMZ paths** from the run summary (not a single folder).
- Each row should include:
  - **Open File** (default app)
  - **Reveal in Finder** (optional)

### Files
- Modify: `src/purway_geotagger/gui/widgets/run_report_view.py`
  - add outputs model/table + open actions
- Modify: `src/purway_geotagger/gui/pages/methane_page.py` (completion-only “View Output Files” + “Open Logs/Run Folder”)
- Modify: `src/purway_geotagger/gui/pages/encroachment_page.py` (completion-only output buttons)
- Modify: `src/purway_geotagger/gui/pages/combined_wizard.py` (completion-only output buttons)
- Add tests:
  - Extend or add: `tests/test_run_report_parser.py` to validate output list formatting from `run_summary.json`.

### Verification
- Manual:
  - Run methane with cleaned CSV + KMZ enabled; confirm viewer lists expected CSV/KMZ and open works.
  - Run encroachment; confirm output folder button opens expected folder.

---

## Issue 6 — Back + Home Navigation Must Be Always Visible (Sticky)
### Goal
- If the page scrolls, navigation controls must remain visible:
  - a compact **Back** control,
  - a compact **Home** icon (returns to Run home menu).
- Navigation should be minimal but obvious (browser-like).

### Implementation Notes
- Create a reusable “sticky nav row” widget placed **below the main header** and **outside scroll areas**.
- Methane + Encroachment pages currently place Back inside their scroll content; restructure so the sticky nav does not scroll away.
- Replace the current “Back” text button with:
  - **Arrow icon + “Previous Page”**
  - **Home icon + “Home”**
  - Both in the same top-left location as today, but always visible.

### Files
- Add: `src/purway_geotagger/gui/widgets/sticky_nav_row.py`
  - emits `back_requested` / `home_requested`
  - uses `QToolButton` icons (`QStyle` standard icons) for minimal styling
- Modify: `src/purway_geotagger/gui/pages/methane_page.py`
- Modify: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Modify: `src/purway_geotagger/gui/pages/combined_wizard.py` (optional: add home icon while keeping header unchanged)
- Modify: `src/purway_geotagger/gui/style_sheet.py` (styling for sticky nav buttons)

### Verification
- Manual:
  - Scroll down long pages and confirm Back/Home are always visible and clickable.

---

## Issue 7 — Placement: Sticky Nav Below Header (Header Unchanged)
### Goal
Header remains exactly as-is; sticky Back/Home controls live in the space directly below the header divider and above page titles.

### Implementation Notes
- Ensure sticky nav row is inserted at the top of each mode page layout, not in `MainWindow` header.
- Do not change header layout, spacing, or controls.

---

# Phased Implementation Plan

## Phase 1 — Theme Control Visibility (Checkboxes + Run Button Style)
**Scope:** Issue 1 + the QSS portion of Issue 3

**Sequence:** Must complete before Phase 2 to keep UI clarity during later changes.

### Tasks
- Add explicit QCheckBox indicator styling for both themes.
- Add `QPushButton[cssClass=\"run\"]` styling (green) and verify hover/pressed/disabled states.

### Files
- Modify: `src/purway_geotagger/gui/style_sheet.py`

### Tests / Verification
- Manual theme toggle verification on all pages with checkboxes.
  - **Required before Phase 2 starts.**

### Gate
- Unchecked checkboxes are clearly visible in light mode.
- Run button green style is available (even if not yet applied everywhere).

### Phase Notes
- Phase completed: 2026-02-06
- Tests/verification: Manual theme toggle verification across Methane, Encroachment, Combined pages; unchecked checkboxes visible in light mode and improved in dark mode.
- Notes: Added explicit checkbox indicator styling and green run button QSS class in `src/purway_geotagger/gui/style_sheet.py`.

---

## Phase 2 — Methane Cleaned CSV/KMZ JPG Association Filtering
**Scope:** Issue 2

**Sequence:** Must complete before Phase 3 so reset/run UI uses correct methane outputs.

### Tasks
- Implement photo filename column detection and JPG-existence filtering in methane outputs.
- Ensure KMZ placemark count matches filtered cleaned CSV.
- Log/report “fallback to PPM-only (no filename column)” cleanly.
- Log missing JPG filenames per CSV and surface counts in run summary / GUI.

### Files
- Modify: `src/purway_geotagger/ops/methane_outputs.py`
- Modify (if needed): `src/purway_geotagger/core/pipeline.py`
- Add: `tests/test_methane_outputs_photo_association.py`

### Tests / Verification
- `python3 -m pytest tests/test_methane_outputs_photo_association.py`
- Manual run on a known folder (spot-check counts).
  - **Required before Phase 3 starts.**

### Gate
- Cleaned CSV rows == qualifying JPGs above threshold (per folder/CSV).
- KMZ placemarks == cleaned CSV rows (with valid lat/lon).

### Phase Notes
- Phase completed: 2026-02-06
- Tests/verification:
  - `python3 -m pytest tests/test_methane_outputs_photo_association.py`
  - Manual spot-check: cleaned CSV for American Brine flight now contains only matching JPG rows; file_name column is column B; no blank filenames.
- Notes: Cleaned CSVs now require filename+PPM match when photo column exists; fallback to PPM-only if column missing. Missing JPG counts surfaced in run summary and log.

---

## Phase 3 — Sticky Nav + Run Button Layout + “Run Another Folder”
**Scope:** Issues 3, 4, 6, 7

**Sequence:** Must complete before Phase 4 so output viewer UI is framed within final navigation layout.

### Tasks
- Create sticky nav row widget (Back + Home icon).
- Refactor Methane/Encroachment pages so nav is outside scroll area.
- Right-align run buttons and apply green run style.
- Add completion-only “Run another folder” button and implement full reset behavior.

### Files
- Add: `src/purway_geotagger/gui/widgets/sticky_nav_row.py`
- Modify: `src/purway_geotagger/gui/pages/methane_page.py`
- Modify: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Modify: `src/purway_geotagger/gui/pages/combined_wizard.py`
- Modify: `src/purway_geotagger/gui/main_window.py` (home navigation + reset wiring)
- Modify: `src/purway_geotagger/gui/style_sheet.py` (sticky nav styling)

### Tests / Verification
- Manual:
  - Verify sticky Back/Home always visible while scrolling.
  - Verify run button right-aligned + green.
  - Complete a run and verify “Run another folder” resets inputs and returns to home.
  - **Required before Phase 4 starts.**

### Gate
- Navigation controls are always available during scroll.
- “Run another folder” produces a clean, fresh UI state.

### Phase Notes
- **2026-02-06:** Implemented sticky nav row + run button alignment for methane/encroachment/combined flows, added combined reset/run‑another handling and main window reset wiring. Added run‑another behavior to return Home and clear progress bar. Tests not run (UI manual verification pending). Note: run‑another button sizing/color may need polish.

---

## Phase 4 — Post‑Run Output Viewer + Output Buttons
**Scope:** Issue 5

**Sequence:** Final phase for this plan.

### Tasks
- Extend RunReportDialog to include an Outputs list/table with open actions.
- Add completion-only “View Output Files” buttons on run pages and wire them to last run folder.
- Add completion-only “Open output folder” buttons where meaningful.

### Files
- Modify: `src/purway_geotagger/gui/widgets/run_report_view.py`
- Modify: `src/purway_geotagger/gui/pages/methane_page.py`
- Modify: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Modify: `src/purway_geotagger/gui/pages/combined_wizard.py`
- Modify: `tests/test_run_report_parser.py`

### Tests / Verification
- `python3 -m pytest tests/test_run_report_parser.py`
- Manual:
  - verify output viewer lists cleaned CSV/KMZ and opens files correctly.
  - **Required before marking Phase 4 complete.**

### Gate
- Pilot can view and open run outputs from inside the app without Finder digging.

### Phase Notes
- (fill in after completion)
