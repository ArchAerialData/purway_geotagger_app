# Purway Geotagger — Home Page + Mode-Specific GUI Plan

Date: 2026-02-02

This document captures the context, constraints, risks, and a phased plan to add a **Home page** with three mode choices (Methane-only, Encroachment-only, Combined) and a **run-log/report UI** with failure notifications.

It is intended to be used alongside:
- `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`
- `IMPLEMENTATION_PHASES.md`

No implementation should begin until Phase gates are met.

---

## 1) Current Context (what exists today)

### GUI structure (PySide6)
- Main window has tabs: **Run**, **Jobs**, **Templates**, **Help**.
- **Run tab** contains:
  - input drag/drop and output folder selection
  - basic options (overwrite / dry run)
  - advanced options (flatten, cleanup, sort-by-PPM, write XMP, rename, template + start index, payload)
  - preview/schema/settings tools
- **Jobs tab** shows job list, progress, and buttons (cancel, open output folder, export manifest, rerun failed).
- **Templates tab** already supports create/edit/delete via Template Editor.

### Pipeline + artifacts
- A run writes:
  - `run_config.json`
  - `run_log.txt`
  - `manifest.csv`
- These are stored in a **run folder** under the chosen output directory.
- `run_log.txt` is a simple text log (timestamp + message).
- `manifest.csv` already contains `status` and `reason` fields for failures.

### Known gaps (already documented in plan)
From `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`:
- **Cleaned methane CSV** generation is not implemented.
- **Encroachment chronological indexing** (rename order by DateTimeOriginal) is not implemented.
- **Combined run** (methane + encroachment) requires separated outputs and isolated rename behavior.

---

## 2) New Goals (from pilot workflow request)

### A) New Home Page
On launch, show a **home screen** with three large choices:
1) **Methane Reports Only**
2) **Encroachment Reports Only**
3) **Methane + Encroachments**

Each option opens a **dedicated UI** with only the relevant controls.
Include a visible **Back** action on every mode page to return to Home and change report type.

### B) Mode-specific screens

**Option 1 — Methane Reports Only**
- Input: drag/drop or file browser
- **PPM threshold input** (default 1000)
- Generates “cleaned CSV” outputs for each methane CSV using the chosen threshold
- Cleaned CSV naming: `OriginalName_Cleaned_<PPM>-PPM.csv` (example: `12345_Methane_Cleaned_1000-PPM.csv`)
- Optional: generate a **KMZ** from the cleaned CSV (only rows with **PPM ≥ threshold** appear). Each row becomes a Placemark with the label set to the **PPM value**.
- KMZ naming matches the cleaned CSV base name (same stem, `.kmz` extension).
- **No output folder required** (methane runs write in-place + beside the original methane CSVs).
- Methane logs are written to the **highest-level input root** (common parent if it exists; otherwise the first input root; shown on Confirm with a change option).
- Run artifacts (`run_log.txt`, `run_config.json`, `manifest.csv`) are stored in a run folder:
  - Methane-only: `<log_location>/PurwayGeotagger_YYYYMMDD_HHMMSS/`
  - Encroachment-only: a **sibling** folder next to the output folder, named `<Encroachment_Output>_RunLogs/PurwayGeotagger_YYYYMMDD_HHMMSS/`
  - Combined: TBD (align with encroachment output base once combined flow is implemented)
- No encroachment copies, no renaming

**Option 2 — Encroachment Reports Only**
- Input: drag/drop or file browser
- Output folder required (this is the **base directory** for the run). Default base = `<common-parent-or-first-root>/Encroachment_Output` (auto-increment if it exists: `Encroachment_Output_2`, etc.). Auto-filled, pilot can override.
- App creates a run folder inside the selected base: `<output_base>/PurwayGeotagger_YYYYMMDD_HHMMSS/`, and all copied JPGs are placed in that run folder.
- Renaming options:
  - template selection
  - start index
  - edit/create templates
- Or use **blank fields** (Client Abbreviation + Start Index default 1) to build a one-off rename without choosing a template.
- Renaming can be **disabled entirely** (copy without renaming).
- Renaming precedence: if a template is selected, **template wins**. If no template is selected and renaming is enabled, require Client Abbreviation and use Start Index.
- Must index in chronological order (earliest capture time → latest). If a photo is missing capture time, keep it grouped with its source folder and place it adjacent to that folder’s dated photos before moving to the next folder.

**Option 3 — Combined (wizard)**
- Shared inputs
- Methane options **separate** from encroachment options
- Methane settings do **not** require an output folder (in-place + beside CSVs), since methane runs do not move or rename the original photos.
- Encroachment requires an output folder (default to `Encroachment_Output` under common parent if it exists; otherwise under first input root).
- Encroachment renaming applies only to encroachment copies. Provide template selection **or** blank Client Abbreviation + Start Index fields, and allow renaming to be disabled.
- Renaming precedence: template wins when selected; otherwise manual Client Abbreviation + Start Index are used (when renaming enabled).
- Use a **multi-step wizard**:
  1) inputs
  2) methane options
  3) encroachment options
  4) confirm
- Every step has **Back** and **Next**. Back preserves selections. Confirm shows a full summary and allows jumping back to edit before final run.
- Combined run artifacts and encroachment copies live under the encroachment output base (run folder created as above). Methane outputs remain in-place beside CSVs.

### C) Run Logs / Report UI
- After run completes, show a **summary view** in the GUI.
- If there are failures, show a **popup** with:
  - failure count summary
  - button: **“View logs for this run”**
- “View logs” opens an **in-app log/report viewer** that clearly shows success vs failures (failure list derived from `manifest.csv`, general info from `run_log.txt`).
- Failures must be easy to find (not buried).

### D) Templates tab stays
Templates editor must remain accessible (as a dedicated tab).

---

## 3) Constraints + Compatibility Requirements

- **macOS-first** (Finder launch, PATH not guaranteed).
- No long-running work on the UI thread; use `QThread` + signals.
- Prefer `pathlib` and argument-list subprocess usage.
- **ExifTool calls stay in `exif/`**.
- **CSV heuristics stay in `parsers/`**.
- Phase discipline per `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` + `IMPLEMENTATION_PHASES.md`.

---

## 4) Risks / Conflicts to Resolve Early

1) **Combined mode pipeline design**
   - Current pipeline is single-flow: copy *or* overwrite.
   - Combined mode needs in-place EXIF + cleaned methane CSV **and** encroachment copies.
   - Likely requires:
     - two-pass pipeline, or
     - split task sets by output policy.

2) **Output folder requirement**
   - Current UI requires output folder even for methane-only runs.
   - **Decision:** methane-only runs do **not** require an output folder (in-place + beside CSVs).
   - **Decision:** methane-only run logs should be written to the **highest-level input root** (use common parent if it exists; otherwise first input root).
- **Decision:** run artifacts live in `<base>/PurwayGeotagger_YYYYMMDD_HHMMSS/` where base is:
  - methane-only: methane log location,
  - encroachment-only: sibling folder `<Encroachment_Output>_RunLogs`,
  - combined: align to encroachment output base (finalize in Phase 5/6).
   - **Decision:** encroachment default output folder uses common parent if it exists; otherwise first input root.
   - **Decision:** default encroachment output folder name is `Encroachment_Output` (auto-increment if it already exists).

3) **Chronological renaming**
   - Current rename order is scan order, not capture-time order.
   - **Decision:** sort by capture time; for **missing datetime**, keep files grouped with their **source folder** and place them adjacent to that folder’s dated photos before moving to the next folder.

4) **Cleaned methane CSV naming**
   - **Decision:** `OriginalName_Cleaned_<PPM>-PPM.csv` (and matching `.kmz` stem).

5) **Log/report UX**
   - **Decision:** in-app log/report viewer that clearly shows success vs failures (failures derived from `manifest.csv`).

---

## 5) Proposed UX Architecture (high level)

**Option A — QStackedWidget (selected)**
- Main window uses a stacked widget:
  - Home page
  - Methane page
  - Encroachment page
  - Combined page (or wizard)
- Tabs stay for Jobs / Templates / Help.
  - Methane mode does not prompt for output folder; encroachment mode does.
  - Existing Run tab is replaced by the mode pages.
  - Every page includes a **Back** control (returns to previous screen without losing selections).

**Option B — Home tab + Mode tabs (rejected)**
- Home tab is default.
- Clicking an option switches to a dedicated tab for that mode.
  - Methane mode hides output-folder controls; encroachment mode shows them with a default value.
  - Existing Run tab is replaced by the mode pages.

---

## 6) Phased Plan (sequential, gated)

### Phase 0 — UX spec + decisions
**Goal:** Lock down exact screen flow and mapping to pipeline behaviors.

**Work items**
- [x] Confirm **stacked pages** + persistent Back navigation on every page.
- [x] Document methane-only logging location: **highest-level input root** (use common parent if it exists; otherwise default to the first input root and show the path on the Confirm step with a change option).
- [x] Document encroachment default output folder when multiple input roots (common parent if it exists; otherwise first input root).
- [x] Document default encroachment output folder name (`Encroachment_Output`) and collision handling.
- [x] Document run artifact locations for each mode (methane: log location run folder; encroachment/combined: output base run folder).
- [x] Document cleaned methane CSV naming: `OriginalName_Cleaned_<PPM>-PPM.csv`, KMZ uses same base name.
- [x] Document chronological ordering: missing datetime stays grouped with its source folder, adjacent to that folder’s dated images.
- [x] Document log/report viewer behavior (in-app viewer + failure summary).
- [x] Confirm combined flow uses a 4-step wizard (Inputs → Methane → Encroachment → Confirm).
- [x] Define validation UX: missing required fields show **inline red “input required”** text and auto-scroll to the first missing section **only when the page is scrollable**.
- [x] Confirm **macOS constraints** for all UI flows (no PATH assumptions; no shell commands; use `pathlib`).

**Files (add/modify)**
- None (documentation-only phase).

**Verification (required)**
- [x] Manual review: confirm no internal conflicts and all decisions are consistent.
- [x] Record verification notes and any issues in this file.

**Gate**
- [x] Written UX flow and naming rules agreed.

**Phase Notes (Phase 0)**
- Date: 2026-02-02
- Verification: Manual review of `GUI_HOME_PAGE_AND_MODES_PLAN.md` for internal consistency; no tests run.
- Issues/Deviations: None.

---

### Phase 1 — Mode model + validation layer
**Goal:** Formalize run modes and option presets.

**Work items**
- [x] Add `RunMode` enum or equivalent.
- [x] Extend job options to include methane threshold + encroachment output base + methane log base + run folder naming policy.
- [x] Implement validation rules per mode.
  - Methane mode: output folder optional/hidden.
  - Encroachment mode: output folder required (default to `Encroachment_Output` under common parent if it exists; otherwise under first input root; auto-increment if exists).
  - Methane mode: log output path resolves to highest-level input root (common parent if it exists; otherwise first input root).
  - Missing required fields block **Next**, show inline red “input required” markers, and auto-scroll only when the page is scrollable.
- [x] Implement a **mode state object** that persists selections across Back/Next and is the single source of truth for the Confirm step.
- [x] Add a default output folder resolver that builds `Encroachment_Output` (auto-increment if exists) using the selected base directory.
- [x] Unit tests for option mapping + validation.

**Files (add/modify)**
- Add: `src/purway_geotagger/core/modes.py` (RunMode enum + data structures).
- Add: `src/purway_geotagger/gui/mode_state.py` (UI state object + validation helpers).
- Modify: `src/purway_geotagger/core/job.py` (JobOptions fields for thresholds/log/output base).
- Modify: `src/purway_geotagger/gui/controllers.py` (map ModeState → JobOptions).
- Tests: `tests/test_modes_validation.py`, `tests/test_mode_state.py`.

**macOS constraints**
- Validation and path rules must not assume Homebrew/PATH; use `pathlib` and explicit paths only.

**Verification**
- [x] Unit tests pass for mode validation.
- [x] Record tests run and results in this file.

**Gate**
- [x] Mode presets and validation are in place.

**Phase Notes (Phase 1)**
- Date: 2026-02-02
- Tests: `.venv/bin/python -m pytest tests/test_modes_validation.py tests/test_mode_state.py`
- Issues/Deviations: Initial test expectation for encroachment default base was adjusted to match the documented default (base = common parent of inputs).

---

### Phase 2 — Home page + navigation shell
**Goal:** Home page exists and routes to the correct mode UI.

**Work items**
- [x] Build home screen UI with 3 mode cards/buttons.
- [x] Navigate to correct mode screen (Methane / Encroachment / Combined).
- [x] Persist last-selected mode.
- [x] Add a **Back** action on every mode page to return to Home without losing selections.
- [x] Ensure Back/Next never discards selections; Confirm step always reflects the latest state.
- [x] Preserve per-mode selections when switching modes (returning to a mode restores its previous inputs/options).

**Files (add/modify)**
- Add directory: `src/purway_geotagger/gui/pages/`
- Add: `src/purway_geotagger/gui/pages/__init__.py`
- Add: `src/purway_geotagger/gui/pages/home_page.py`
- Add: `src/purway_geotagger/gui/pages/methane_page.py`
- Add: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Add: `src/purway_geotagger/gui/pages/combined_wizard.py`
- Modify: `src/purway_geotagger/gui/main_window.py` (replace Run tab with stacked pages + Back wiring).
- Modify: `src/purway_geotagger/core/settings.py` (persist last-selected mode).

**macOS constraints**
- Use standard Qt widgets only; do not rely on macOS-specific UI APIs.

**Verification**
- [x] Manual UI test: mode buttons switch to correct screens.
- [x] Record verification steps and results in this file.

**Gate**
- [x] Home page is default on launch and navigation works.

**Phase Notes (required)**
- [x] Date: 2026-02-02
- [x] Tests: `python3 -m compileall src`
- [x] Verification: Manual UI navigation confirmed (Home → each mode → Back).
- [x] Notes: Home page cards expanded to fill vertical space, updated to 3 bullet points per card; mode buttons use accent styling; theme toggle moved to tab bar corner; default window size increased.
- [x] Issues/Deviations: None.

---

### Phase 3 — Methane-only mode screen
**Goal:** Dedicated methane-only UI with threshold control.

**Work items**
- [x] Methane screen UI (inputs + PPM threshold).
- [x] Show methane log output location on the page (and on Confirm), with “Change location” link if multiple roots are present.
- [x] Add KMZ toggle (off by default) and show cleaned CSV/KMZ naming preview based on the current threshold.
- [x] Integrate threshold into run config.
- [x] Ensure encroachment options are hidden.

**Files (add/modify)**
- Modify: `src/purway_geotagger/gui/pages/methane_page.py`

**macOS constraints**
- Drag/drop and file dialogs must work for Finder-launched apps (no PATH assumptions).

**Verification**
- [x] Manual run with threshold change updates run config.
- [x] Record verification steps and results in this file.

**Gate**
- [x] Methane-only UI functions end-to-end (even if cleaned CSV output is still pending).

**Phase Notes (required)**
- [x] Date: 2026-02-02
- [x] Tests: `python3 -m compileall src/purway_geotagger/gui/pages src/purway_geotagger/gui/controllers.py`
- [x] Verification: `run_config.json` shows `methane_threshold=777` for run folder `PurwayGeotagger_20260202_164412`.
- [x] Notes: Methane page now has in-app log viewer + failure popup; EXIF tool failure messaging surfaced.
- [x] Issues/Deviations: None.

---

### Phase 4 — Encroachment-only mode screen
**Goal:** Dedicated encroachment UI with renaming + output folder.

**Work items**
- [x] Encroachment screen UI (inputs + output folder + rename/template controls).
- [x] Require output folder.
- [x] Auto-fill output folder with the computed default (`Encroachment_Output` under base dir) and allow override.
- [x] Provide renaming options:
  - template selection
  - or blank fields for Client Abbreviation + Start Index (default 1)
  - a clear toggle to **disable renaming** entirely
- [x] Enforce renaming precedence: template wins; manual fields required only when renaming enabled and no template selected.
- [x] Ensure methane-specific controls are hidden.

**Files (add/modify)**
- Modify: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Reuse: `src/purway_geotagger/gui/widgets/template_editor.py` (open from encroachment UI)
 - Modify: `src/purway_geotagger/gui/controllers.py` (manual rename template when no template selected)
 - Modify: `src/purway_geotagger/gui/main_window.py` (wire controller into Encroachment page)

**macOS constraints**
- Output folder picker should default to the resolved base directory.

**Verification**
- [x] Manual run uses selected template and start index.
- [x] Record verification steps and results in this file.

**Gate**
- [x] Encroachment-only UI functions end-to-end.

**Phase Notes (required)**
- [x] Date: 2026-02-02
- [x] Tests: `python3 -m compileall src/purway_geotagger/gui/pages/encroachment_page.py src/purway_geotagger/gui/controllers.py`
- [x] Verification: Manual run confirmed (template + start index applied to encroachment output).
- [x] Notes: Encroachment UI added with required output folder, default auto-fill, rename toggle, template selection, manual client/start index fields, and Run Encroachment action wired to mode state options.
- [x] Issues/Deviations: None.

---

### Phase 5 — Combined mode UI
**Goal:** Combined mode with clearly separated methane + encroachment settings.

**Work items**
- [x] Implement Combined **wizard** (Inputs → Methane → Encroachment → Confirm).
- [x] Shared inputs, separated option panels.
- [x] Confirm step before run.
- [x] Confirm step lists **all** resolved settings (inputs, methane threshold, methane log location, cleaned CSV/KMZ naming, encroachment output folder, renaming settings, start index, and renaming enabled/disabled).
- [x] Encroachment panel supports template selection or blank Client Abbreviation + Start Index fields, and allows renaming to be disabled.
- [x] “Next” validates required inputs and scrolls to missing sections with inline red “input required” markers (only if scrolling is possible).
- [x] Enforce renaming precedence in combined mode (template wins; manual fields used only when renaming enabled and no template selected).

**Files (add/modify)**
- Modify: `src/purway_geotagger/gui/pages/combined_wizard.py`
- Add: `src/purway_geotagger/gui/widgets/required_marker.py`
 - Modify: `src/purway_geotagger/gui/main_window.py` (wire controller into Combined wizard)

**macOS constraints**
- Wizard transitions must not block the UI thread; validation only, no background work.

**Verification**
- [x] Manual test: wizard navigation and summary view validated; confirm step displays resolved settings.
- [x] Record verification steps and results in this file.

**Gate**
- [ ] Combined mode UI flow is complete.

**Phase Notes (required)**
- [x] Date: 2026-02-02
- [x] Tests: `python3 -m compileall src/purway_geotagger/gui/pages/combined_wizard.py src/purway_geotagger/gui/widgets/required_marker.py src/purway_geotagger/gui/main_window.py`
- [x] Verification: Manual review of Combined wizard steps + confirm summary (Run Combined remains disabled until Phase 6).
- [x] Notes: Added step headers for each wizard page; always-visible log browse button; output path tooltips; template preview using actual renderer; template dropdown live refresh on save/delete; manual fields hidden when template selected; muted helper text to reduce clutter.
- [x] Issues/Deviations: None.

---

### Phase 6 — Pipeline upgrades required by modes
**Goal:** Required backend features match the new UI.

**Work items**
- [x] Implement cleaned methane CSV generation with custom threshold.
- [x] Implement optional KMZ generation from cleaned methane CSVs (Placemark label text = PPM value; only rows with **PPM ≥ threshold**).
- [x] Implement chronological indexing for encroachment renaming.
- [x] Implement combined mode split behavior (methane in-place + encroachment copies).
- [x] Ensure cleaned CSV + KMZ naming match the agreed convention.
- [x] Add a per-run summary payload (e.g., `run_summary.json`) that records:
  - EXIF injection totals (success/failed/total JPGs)
  - cleaned CSV status per source CSV (success/failed/skipped)
  - KMZ status per source CSV (success/failed/skipped)
  - run settings snapshot (threshold, KMZ enabled, mode)
- [x] Update run logging to include clear “EXIF injected X/Y” and “Cleaned CSV / KMZ: success|failed|skipped” lines even if those outputs are not yet implemented.
- [x] Move `.bak` backups (overwrite mode) into a dedicated backups folder under the run folder to keep source folders clean.

**Files (add/modify)**
- Add: `src/purway_geotagger/ops/methane_outputs.py` (cleaned CSV + KMZ writer).
- Modify: `src/purway_geotagger/core/pipeline.py` (invoke methane outputs; split combined flow).
- Modify: `src/purway_geotagger/ops/renamer.py` (chronological ordering).
- Modify: `src/purway_geotagger/ops/copier.py` (write backups into run folder backups area).
- Add: `src/purway_geotagger/core/run_summary.py` (summary model + writer).
- Tests: `tests/test_methane_outputs.py`, `tests/test_kmz_writer.py`, `tests/test_renamer_chronological.py`.
 - Tests: `tests/test_run_summary.py`, `tests/test_backup_location.py`.

**Dependencies**
- Prefer **stdlib only** for KMZ (zipfile + xml.etree). If any external library is chosen, add it to `requirements.txt` (and `requirements-dev.txt` if tests need it) and ensure `scripts/macos/setup_macos.sh` installs it.

**macOS constraints**
- All file operations must use `pathlib`; avoid shell commands.

**Verification**
- [ ] Unit tests for cleaned CSV output.
- [ ] Unit tests for KMZ generation (Placemark label text and row count).
- [ ] Unit tests for chronological rename ordering.
- [ ] Unit tests for run summary content (EXIF/CSV/KMZ status fields).
- [ ] Unit tests for backup relocation into run folder backups.
- [ ] Manual combined run on sample data.
- [ ] Record tests run and results in this file.

**Gate**
- [ ] All three backend behaviors are verified.

**Phase Notes (required)**
- [ ] Update this file with date completed, tests run, and any issues/failures.
Phase Notes (in progress, 2026-02-03):
- Implemented methane cleaned CSV + KMZ generation, chronological renaming, combined split flow, run_summary.json, and backup relocation.
- Tests not run (pytest not installed in this environment). Manual combined run pending.

---

### Phase 7 — Run log/report UI + failure popup
**Goal:** Users can review results and find failures quickly.

**Work items**
- [ ] Add “Run Report / Logs” view in GUI (tab or pane).
- [ ] Parse `manifest.csv` to surface failures prominently.
- [ ] Add completion popup on failures with “View logs” button.
- [ ] Log viewer shows: run summary (from `run_summary.json`), failure list, and a collapsible raw log view (`run_log.txt`).

**Files (add/modify)**
- Add: `src/purway_geotagger/gui/widgets/run_report_view.py`
- Modify: `src/purway_geotagger/gui/main_window.py` (hook up “View logs” button).
- Tests: `tests/test_run_report_parser.py`

**macOS constraints**
- Log viewer must open inside the app (no external viewer dependency).

**Verification**
- [ ] Unit test: manifest parsing for failures.
- [ ] Manual test: failure popup appears and routes to logs.
- [ ] Record tests run and results in this file.

**Gate**
- [ ] Logs/report UI is usable and failures are easy to find.

**Phase Notes (required)**
- [ ] Update this file with date completed, tests run, and any issues/failures.

---

## 7) Open Questions (needs your input)

No open questions at this time.

---

## 8) Compatibility Checklist (preflight)

- Finder launch: don’t assume PATH for ExifTool.
- Avoid long tasks on UI thread.
- Keep ExifTool usage in `exif/`.
- Keep CSV logic in `parsers/`.
- Update `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` and `IMPLEMENTATION_PHASES.md` at phase completion.
