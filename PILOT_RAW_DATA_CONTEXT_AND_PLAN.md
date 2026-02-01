# Purway Geotagger — Pilot Raw Data Context + Plan (Methane Reports + Encroachment Patrols)

This document captures:
1) Context gathered from the latest pilot workflow requirements, and
2) Repository + sample “Raw Data” observations (folder layouts + file formats), and
3) A phased implementation plan (modeled after `IMPLEMENTATION_PHASES.md`) to close the gaps.

---

## 0) macOS-first compatibility constraints (non-negotiable)

Pilots run this on **macOS**, so implementation must assume:
- Launching from **Finder / a packaged `.app`** (PATH may not include Homebrew locations like `/opt/homebrew/bin`).
- Dropbox/macOS exports often include filesystem artifacts (AppleDouble `._*`, `.DS_Store`, `__MACOSX/`, etc.). The app must **never crash** when these are present.
- Paths will contain spaces and special characters; all subprocess usage must remain **argument-list based** (no shell-string commands).
- Any per-run config/templates data must be accessible in both **dev** and **PyInstaller macOS builds** (avoid repo-relative filesystem assumptions).

---

## 1) Pilot workflows (from your message)

The GUI must accept a pilot’s full “Raw Data” folder drop (entire project dump), and support **two deliverables**:

### A) Methane Reports (in-place, keep original structure)
- Pilot drops a project “Raw Data” folder (or many subfolders).
- **All files stay where they are**, with original folder structure + filenames unchanged.
- Photos should have **GPS EXIF/XMP injected** so pilots can quickly extract:
  - coordinates, and
  - (ideally) google maps links for report writing.
- All `Methane.csv` files should be parsed and a **new “cleaned” CSV** should be generated that filters out values **below 1000ppm**.
  - The cleaned CSV is written **next to** the original methane CSV.
  - Rows with `ppm >= 1000` are retained; `ppm <= 999` are excluded.

### B) Encroachment Patrols (copy + unify photos)
- Pilot drops the same style of folder(s).
- App injects EXIF into all photos within the dropped folders.
- App creates a **unified copy** of all JPGs into a **single output folder** (pilot-selected destination).
- If **bulk renaming + indexing** is enabled (or a template selected):
  - copied photos are renamed + indexed **before** landing in the unified folder
  - indexing order is based on **EXIF Date/Time** (chronological across *all* dropped folders)
- For any JPGs that cannot be copied/injected, **logs must include a reason**.

### C) Combined Run (single run produces both outputs)
- A single run can produce:
  - **Methane outputs** (in-place EXIF + cleaned CSVs beside original methane CSVs), and
  - **Encroachment outputs** (copied JPGs into a single pilot-selected folder).
- **Renaming templates apply only to the encroachment copies** and never alter the original methane data.

---

## 2) Sample pilot “Raw Data” folder observed in repo

Path provided/used for inspection:

```text
tests/test_data/original/Raw Data
```

### 2.1 Top-level structure
The sample looks like a “project dump” containing:
- multiple “project/segment” folders (pipeline names, areas, etc.), plus
- some non-image documents at the root (e.g., wind reports).

Observed top-level entries:
```text
Raw Data/
  KDB 20-IN/
  Kelly Bell + Gregory + Portland 10in/
  Marathon 12-IN/
  PETTUS Loop/
  Texana 6-IN/
  WindData_Targa_KDB_2026_01_28.docx
  WindData_Targa_KDB_2026_01_29.docx
```

### 2.2 Flight-folder pattern (nested)
Under each project folder are one or more “flight” folders named like:
```text
YYYYMMDDhhmmss_<Project>_Flight_<NN>
```
Examples:
- `KDB 20-IN/20260129005309_KDB_Flight_03/`
- `Kelly Bell + Gregory + Portland 10in/20260130020958_Gregory_Portland10in/`

### 2.3 File counts + types
Within this sample dataset:
- `492` JPGs
- `37` CSVs
- `4` DOCX

### 2.4 “Typical” flight folder contents
Typical flight folders contain:
- many JPGs named like `YYYYMMDD_HHMMSS.jpg`
- a large “raw” methane CSV: `methane<flightstamp>.csv`
- a smaller methane CSV: `methane<flightstamp> copy.csv` (appears to be a filtered subset)
- a track CSV: `track<flightstamp>.csv`

Example (one flight folder):
```text
20260128235719_KDB_Flight_01/
  20260128_235725.jpg
  20260128_235812.jpg
  ...
  methane20260128235719.csv          (large)
  methane20260128235719 copy.csv     (small)
  track20260128235719.csv
  ._methane20260128235719 copy.csv   (macOS AppleDouble “resource fork” artifact)
```

### 2.5 Important real-world “messiness” observed
- Some flight folders contain **0 JPGs** (only CSVs).
- macOS “AppleDouble” resource fork files exist:
  - `._methane<...> copy.csv` (binary-ish; **not UTF-8**; will crash naïve CSV readers)
- A few JPG filenames look timestamped but contain an **invalid second** value (`SS=60`):
  - `20260129_000260.jpg`
  - `20260129_005460.jpg`
  - `20260129_010560.jpg`
  - `20260129_010760.jpg`

---

## 3) Observed CSV schemas (important for matching + DateTimeOriginal)

### 3.1 Methane CSV (`methane*.csv`)
Header observed:
```csv
time,methane_concentration,...,longitude,latitude,...,file_name
```

Key observations:
- `longitude` + `latitude` are present.
- `methane_concentration` is the PPM-ish field.
- `file_name` is sometimes populated with the JPG basename (ex: `20260128_235725.jpg`).
- `time` values are in a Purway-specific format with milliseconds separated by `:`:
  - `2026-01-28_23:57:19:149`
  - `YYYY-MM-DD_HH:MM:SS:ms`

### 3.2 Track CSV (`track*.csv`)
Header observed:
```csv
time,longitude,latitude,altitude
```
And the same time format:
- `YYYY-MM-DD_HH:MM:SS:ms`

---

## 4) What the app currently does well (existing skeleton capabilities)

Based on current repo code:
- GUI supports drag/drop of folders/files, and runs jobs in a background thread.
- Recursive scanning finds JPGs + CSVs.
- CSV parsing + photo correlation exists:
  - joins by photo filename if a “photo reference” column exists (substring detection includes `file_name`)
  - timestamp-join fallback exists
- EXIF writing uses ExifTool:
  - writes GPS tags + optional XMP
  - writes `DateTimeOriginal` (if available from CSV parsing)
  - writes `ImageDescription` like `ppm=<x>; source_csv=<name>` plus optional `purway_payload=<...>`
- Output operations exist:
  - overwrite originals (with optional `.bak`) OR copy to output
  - optional renaming via templates + start index
  - optional “PPM bin” sorting (copies into `BY_PPM/`)
  - optional flatten (moves into `JPG_FLAT/`)
- Per-run artifacts exist:
  - `run_log.txt`
  - `run_config.json`
  - `manifest.csv`

---

## 5) Current issues / gaps vs. pilot workflows

### 5.1 Raw data ingestion robustness gaps (will break on real pilot folders)
1) **macOS `._*` files are treated as real CSVs**
   - `scan_inputs()` includes any `*.csv` file, including AppleDouble resource forks.
   - `PurwayCSVIndex.from_csv_files()` will crash when it tries to open these binary files as UTF-8.
2) **CSV timestamp parsing does not support Purway time format**
   - Current `parse_csv_timestamp()` fails on `YYYY-MM-DD HH:MM:SS:ms`.
   - Impact:
     - timestamp-join fallback becomes unusable for track CSVs
     - `DateTimeOriginal` is never populated from methane/track CSV timestamps
3) **Photo filename timestamp parsing can hard-crash**
   - Some filenames contain invalid seconds (`SS=60`), which will currently raise `ValueError` during `datetime(...)`.
4) **ExifTool discovery can fail on macOS when launching from Finder / a packaged app**
   - `ExifToolWriter` runs `exiftool` by name and assumes it is on `PATH`.
   - On macOS, GUI apps launched from Finder often do **not** inherit the user shell PATH, so Homebrew-installed ExifTool may not be found even when installed.
5) **Default templates path is not PyInstaller-safe**
   - `TemplateManager.DEFAULT_TEMPLATES_PATH` is repo-relative (`.../config/default_templates.json`) and may not exist in a packaged macOS `.app` even though `--add-data` is used.

### 5.2 Methane Report workflow gaps
- No “Methane Reports” mode/preset in the UI (pilots must manually configure multiple checkboxes).
- No “cleaned CSV” generation feature:
  - needs a threshold (default **1000ppm**) and a clear output location strategy
- No built-in “google maps link” generation for report-friendly output (optional but likely high value).

### 5.3 Encroachment Patrol workflow gaps
- No “Encroachment Patrols” mode/preset in the UI.
- Renaming + indexing is **not ordered by EXIF datetime** today:
  - `maybe_rename()` increments index in whatever order tasks are scanned (currently path-sorted).
  - requirement is chronological ordering across folders.
- Current “flatten” moves **SUCCESS only**:
  - for encroachment, we likely want an explicit policy for whether FAILED/unmatched photos should still be included in the unified folder (and how to name them).

### 5.4 Correlation scope risk (multi-flight / multi-folder drops)
- Current CSV index is global for the entire job:
  - all CSV records go into one pool
  - photo join is by basename
- This can become fragile if basenames ever collide across flights/projects (not present in the sample set, but plausible in general).
- We likely need a “prefer CSVs near the photo” strategy (e.g., same directory first) to reduce the chance of mismatches.

---

## 6) Resolved decisions (ready to implement)

1) **Cleaned methane CSV definition**
   - Filter the original methane CSV to keep only rows where `ppm >= 1000`.
   - Output is a **copy** in the **same folder** as the original methane CSV.
2) **EXIF injection policy**
   - Inject EXIF for **all JPGs that can be matched**, for both Methane and Encroachment modes.
3) **Encroachment output**
   - Output is a **single pilot-selected folder** containing all copied JPGs.
   - Log any missing/unprocessed JPGs with a **reason**.
   - Bulk renaming + indexing must work and be time-ordered across all folders.
4) **Combined run support**
   - One run can produce **both** Methane outputs and Encroachment copies.
   - Renaming templates affect **encroachment copies only** and never modify methane originals.

---

## 7) Implementation plan (phased, hard gates)

Modeled after `IMPLEMENTATION_PHASES.md`: do not start the next phase until the gate criteria are met.

### Phase execution rules (apply to every phase)
- **No phase skipping:** Do not start the next phase until **all** items and the Gate for the current phase are complete.
- **Update this file:** At the end of each phase, mark every checkbox, and add a short **“Phase Notes”** paragraph with:
  - date completed,
  - tests/verification run (commands + pass/fail), and
  - any deviations or follow-ups.
- **Organizational rules:** Follow the global organization rules in `IMPLEMENTATION_PHASES.md` (module boundaries, threading rules, pathlib usage, etc.).
- **Testing discipline:** Run the phase’s tests/verification or add the minimal verification steps needed for safety.

### Phase 0 — Requirements alignment + UX wireframe

**Goal:** Lock down exact behavior for Methane vs Encroachment modes and prevent later rework.

**Work items**
- [x] Confirm answers to the Open Questions in section 6.
- [x] Define modes in the app:
  - `Methane Report`
  - `Encroachment Patrol`
  - `Combined (Methane + Encroachment)`
  - `Custom` (power users only)
- [x] Define mode presets (default checkbox values + which controls are shown/enabled).
- [x] Overwrite vs copy policy:
  - Default to **copy‑then‑write** until EXIF safety is verified on sample data.
  - After validation, allow **overwrite originals** for Methane mode (with `.bak` backup default on).

**Gate**
- [x] A short “Mode behavior table” exists (inputs → outputs for each mode) and matches pilot expectations.
- [x] Phase Notes recorded (date + tests/verification + deviations).

**Phase Notes (Phase 0)**
- Date: 2026‑02‑01
- Verification: Documentation-only updates; no code execution required.
- Deviations: None.

#### Phase 0 — Mode behavior table (authoritative)

| Mode | Inputs | EXIF Injection | Methane CSV Output | Encroachment Output | Renaming Applies To | Output Folder Required |
| --- | --- | --- | --- | --- | --- | --- |
| Methane Report | Raw Data folder(s) | All matched JPGs | Cleaned CSVs (ppm ≥ 1000) next to original methane CSVs | None | N/A | No |
| Encroachment Patrol | Raw Data folder(s) | All matched JPGs | None | Single pilot‑selected folder of copied JPGs | Encroachment copies only | Yes |
| Combined (Methane + Encroachment) | Raw Data folder(s) | All matched JPGs | Cleaned CSVs (ppm ≥ 1000) next to original methane CSVs | Single pilot‑selected folder of copied JPGs | Encroachment copies only | Yes |
| Custom | Raw Data folder(s) | As configured | As configured | As configured | As configured | Depends on options |

#### Phase 0 — Default presets per mode

**Methane Report (default)**
- Overwrite originals: **TBD by EXIF safety decision** (see overwrite vs copy policy)
- Cleaned CSV threshold: **1000 ppm**
- Encroachment output: **disabled**
- Renaming/indexing: **disabled**
- Flatten/sort: **disabled**

**Encroachment Patrol**
- Copy mode: **enabled**
- Encroachment output folder: **required**
- Renaming/indexing: **off by default** (pilot can enable)
- Flatten/sort: **disabled**

**Combined (Methane + Encroachment)**
- Methane outputs: **enabled**
- Encroachment copies: **enabled**
- Encroachment output folder: **required**
- Renaming/indexing: **off by default** (pilot can enable for encroachment copies only)

**Custom**
- No preset changes; user controls all options.

### Phase 1 — Raw Data robustness (must not crash on real pilot folders)

**Goal:** The app can scan/preview/run successfully on the sample `Raw Data` folder and likely Dropbox exports.

**Work items**
- [x] Ignore/skip macOS artifacts:
  - `._*` AppleDouble
  - `.DS_Store`, `__MACOSX/` folders (and similar macOS/Dropbox artifacts)
  - Implement in `scanner.py` (preferred) and also harden CSV readers to skip+log on decode errors (belt-and-suspenders).
- [x] Extend `parse_csv_timestamp()` to support Purway format:
  - `YYYY-MM-DD_HH:MM:SS:ms` (ms optional)
  - Preserve existing supported formats.
- [x] Harden `parse_photo_timestamp_from_name()` to return `None` (not crash) on invalid times.
- [x] Make ExifTool discovery macOS-safe:
  - search common locations (e.g., `/opt/homebrew/bin/exiftool`, `/usr/local/bin/exiftool`) when `exiftool` is not on PATH
  - persist an `exiftool_path` setting and allow “Browse…” in GUI if needed
  - preflight check (before running a job) with a clear pilot-facing error message
- [x] Make default templates loading work in packaged macOS builds:
  - load `config/default_templates.json` via a packaging-safe mechanism (PyInstaller/resources), not repo-relative paths
- [x] Add/extend tests for:
  - skipping `._*` files
  - parsing Purway timestamps with milliseconds
  - invalid filename timestamps

**Gate**
- [x] `Preview matches` and `CSV schema` work on `tests/test_data/original/Raw Data` without crashing.
- [x] A dry-run job can complete on the sample folder (even if EXIFTool is not present), producing logs + manifest.
- [ ] When launched from Finder (or a packaged `.app`), the app either finds ExifTool automatically or shows a clear “install/locate ExifTool” error.
- [x] Phase Notes recorded (date + tests/verification + deviations).

**Phase Notes (Phase 1)**
- Date: 2026‑02‑01
- Verification:
  - `python -m pytest tests/test_timeparse.py tests/test_scanner.py tests/test_purway_csv_parse.py`
  - `python -m pytest tests/test_exiftool_writer.py`
  - `build_preview()` on `tests/test_data/original/Raw Data`
  - `run_job()` dry‑run on `tests/test_data/original/Raw Data` (no EXIF writes)
- Deviations:
  - Finder/packaged `.app` ExifTool preflight not verified in this environment; requires macOS manual check.

### Phase 2 — Methane Reports mode (in-place EXIF + cleaned CSV)

**Goal:** One-click workflow for methane reporting with minimal pilot decisions.

**Work items**
- [ ] Add a “Methane Reports” mode preset in the GUI:
  - overwrite originals (with `.bak` default on)
  - flatten off, rename off, PPM bin sort off (unless explicitly requested)
- [ ] Implement cleaned methane CSV generation:
  - threshold default 1000ppm, configurable
  - deterministic output naming (e.g., `*_cleaned_1000ppm.csv` or similar)
  - output **in the same folder** as the original methane CSV
- [ ] (Optional) Generate a “photo hits” CSV for reporting:
  - one row per photo where `ppm >= threshold`
  - include lat/lon + a `google_maps_url` column

**Gate**
- [ ] Running in Methane mode on sample data produces:
  - in-place EXIF (or dry-run verification)
  - cleaned CSV outputs for each methane CSV discovered
  - updated run artifacts (manifest/log/config)
- [ ] Phase Notes recorded (date + tests/verification + deviations).

### Phase 3 — Encroachment Patrol mode (copy + unify + time-ordered indexing)

**Goal:** Produce a single output folder of JPGs, optionally renamed/indexed by chronological EXIF time.

**Work items**
- [ ] Add an “Encroachment Patrol” mode preset in the GUI:
  - copy mode (no overwrite) default on
  - unify output folder selection (pilot-selected destination)
  - PPM sort off by default
- [ ] Implement chronological indexing:
  - before assigning `{index}`, sort SUCCESS (or selected set) by `DateTimeOriginal`
  - define tie-breakers (e.g., `datetime_original`, then original filename)
  - define behavior for missing datetime (append at end, or fallback to filename timestamp)
- [ ] Log any missing/unprocessed JPGs with reason (encroachment mode).
- [ ] Ensure combined runs keep methane outputs untouched while encroachment copies are renamed/indexed separately.
- [ ] Add tests for the ordering/renaming logic (non-Qt).

**Gate**
- [ ] With renaming enabled, output numbering matches chronological capture order across folders.
- [ ] Phase Notes recorded (date + tests/verification + deviations).

### Phase 4 — GUI polish for pilots (streamlined, hard-to-misconfigure)

**Goal:** Pilots can do the right thing quickly without understanding the pipeline internals.

**Work items**
- [ ] Add a clear mode selector at the top of the Run tab (Methane vs Encroachment).
- [ ] Show only mode-relevant options by default; keep advanced options behind an expandable section.
- [ ] Improve copy/overwrite language (explicitly describe in-place writes vs output copies).
- [ ] Add small “quick help” text next to threshold, output folder, and rename settings.
- [ ] Ensure preview/schema tools respect the same file skipping rules and do not crash.

**Gate**
- [ ] Manual smoke test: dropping the full sample Raw Data folder and running each mode is straightforward and does not require fiddly settings.
- [ ] Phase Notes recorded (date + tests/verification + deviations).

#### Phase 4A — Explicit GUI requirements checklist (do not skip)

**Mode selection (top of Run tab)**
- [ ] Modes shown: `Methane Report`, `Encroachment Patrol`, `Combined (Methane + Encroachment)`, `Custom`.
- [ ] Changing mode updates visible options immediately and updates a short **mode summary** text block (plain English).

**Inputs + output clarity**
- [ ] Inputs area explicitly says **“Drop Raw Data folder(s)”** and accepts mixed folders/files.
- [ ] Methane output location is implicit (in-place) and shown as a **read-only** label (“Writes cleaned CSVs next to original methane CSVs”).
- [ ] Encroachment output folder is **required** when Encroachment or Combined is selected, with a clear warning if missing.

**EXIF behavior**
- [ ] A single, always-visible note: **“EXIF is injected for all matched JPGs.”**
- [ ] If ExifTool is missing, show a blocking dialog with a **single call-to-action** (Locate / Install).

**Renaming + indexing**
- [ ] Renaming controls are shown **only** for Encroachment/Combined.
- [ ] Renaming summary text clarifies: **“Renaming affects encroachment copies only.”**
- [ ] When renaming enabled, show live preview for the next filename and the starting index.
- [ ] Sorting/indexing order note: “Ordered by capture time (EXIF DateTimeOriginal).”

**Methane cleaned CSV**
- [ ] Threshold control (default 1000) is shown only for Methane/Combined.
- [ ] One-line helper text: “Creates *_cleaned_1000ppm.csv in the same folder.”

**Safety + reassurance**
- [ ] If overwrite originals is enabled, show a **single confirmation dialog** and explain backups.
- [ ] “Dry run” (if present) is clearly labeled as “No EXIF writes”.
- [ ] A small “What happens when I click Run?” tooltip or expandable help box.

**Pilot-friendly defaults**
- [ ] Defaults set to Combined mode (if that’s your preferred flow), otherwise Methane.
- [ ] Advanced options collapsed by default.
- [ ] Output folder pre-filled with last used value.

**Visual polish / readability**
- [ ] Buttons have clear, action-first labels (e.g., “Run Now”, “Choose Encroachment Folder”).
- [ ] All critical settings are visible **without scrolling** on a standard laptop screen.
- [ ] No dense blocks of text; use short labels and helper tooltips.

**Gate for Phase 4A**
- [ ] Pilot can complete a run without reading the README or asking questions.
- [ ] Phase Notes recorded (date + tests/verification + deviations).

### Phase 5 — Docs + validation + release checklist

**Goal:** Field-ready: pilots can run it, and we can support it.

**Work items**
- [ ] Update `README.md` (or add a new “Pilot workflow” doc) for the two deliverables.
- [ ] Ensure `scripts/` match the expected install/run workflow for pilot laptops.
- [ ] Add a short troubleshooting section for common issues:
  - missing ExifTool
  - unmatched photos
  - Dropbox/macOS artifact files

**Gate**
- [ ] A new pilot can follow docs to run both deliverables end-to-end.
- [ ] Phase Notes recorded (date + tests/verification + deviations).
