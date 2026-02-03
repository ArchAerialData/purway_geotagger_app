# Purway Photo Geotagger (macOS field app) — Implementation Guide + Skeleton Repo

This repo is a **modular** Python desktop application intended for macOS pilot laptops (MacBooks) to:
- ingest Purway CH-4 payload flight outputs (folders containing **JPG + CSV**),
- **inject GPS EXIF/XMP** (and optional additional tags) into the JPGs using **ExifTool**,
- optionally **copy vs overwrite originals**,
- optionally **flatten/move** all resulting JPGs into a single folder,
- optionally **rename** with client-specific templates + configurable starting index,
- optionally **sort into concentration (PPM) bins**,
- show **progress**, job results, and **open output folder** actions.

This guide is written so a VS Code CODEX agent can implement the full application without inventing requirements.
All “TODO”s in code are **explicit** and bounded.

---

## 0) Non-negotiable implementation decisions (do not deviate)

1. **GUI toolkit**: Use **PySide6 (Qt)**.
   - Reason: robust drag-and-drop, threads, native macOS feel, long-term maintainability.
2. **EXIF/XMP writing**: Use **ExifTool** as the canonical writer.
   - Reason: reliable for GPS + XMP, handles JPEG metadata edge cases better than pure-Python.
3. **No reverse engineering of payload**.
   - This app only processes exported artifacts (JPG/CSV) from Purway outputs.

---

## 1) Supported input layouts (must support all)

The pilot can drag/drop either:
- A **single parent folder** containing multiple flight subfolders, OR
- **many individual folders** (each may contain subfolders), OR
- A mixture of both.

The app must recursively scan dropped folders and find:
- JPG files (extensions: `.jpg`, `.jpeg`, case-insensitive)
- CSV files (extension: `.csv`)

**Expected Purway patterns** (do not hardcode exact names; handle variants):
- CSVs may include `Methane.csv` and/or other CSV(s) with coordinate + PPM fields.
- Some CSVs may include a column pointing to an image filename (e.g. `Photo`).
- Some outputs may only correlate by **timestamp**.

If a photo cannot be matched to a CSV record, the photo must be marked **FAILED** with a reason; do not silently skip.

---

## 2) Correlation logic (photo ⇄ CSV row) — exact algorithm

For each discovered JPG:

### Step A: Prefer explicit filename join if possible
If any parsed CSV row contains a column that looks like an image reference (one of):
- `Photo`, `photo`, `Image`, `image`, `Filename`, `filename`, `File`, `file`, `SourceFile`

Then join by:
- `basename(row[photo_col]) == basename(photo_path)`

### Step B: Timestamp join (fallback)
If Step A fails, and CSV contains a time column (one of):
- `Timestamp`, `timestamp`, `Time`, `time`, `DateTime`, `datetime`, `Date`

Then:
1. Parse CSV time -> `datetime` (support common formats; see `util/timeparse.py`)
2. Attempt to parse a timestamp from the photo filename (common patterns):
   - `YYYY-MM-DD_HH-MM-SS` / `YYYY-MM-DD HH-MM-SS` / `YYYYMMDD_HHMMSS`
3. If photo timestamp exists:
   - choose the CSV row with the **smallest absolute time delta**
   - accept if delta ≤ `max_join_delta_seconds` (default: **3 seconds**)
4. If photo timestamp does not exist:
   - mark FAILED: “no filename timestamp and no explicit Photo column correlation”.

### Step C: Ambiguity handling
If multiple rows have the same minimal delta within 0.1s (ties), mark FAILED: “ambiguous timestamp join”.

---

## 3) EXIF/XMP fields to write (exact, default behavior)

For each matched photo, write:

### Required
- EXIF GPS:
  - `GPSLatitude`
  - `GPSLongitude`
  - `GPSLatitudeRef` (N/S)
  - `GPSLongitudeRef` (E/W)
- XMP GPS (optional but enabled by default):
  - `XMP:GPSLatitude`
  - `XMP:GPSLongitude`

### Recommended additional (configurable)
- `DateTimeOriginal` (if a reliable time exists)
- `ImageDescription` (append structured key/value for downstream parsing)
  - include at least:
    - `ppm=<value>`
    - `source_csv=<csv name>`
    - `purway_payload=<user-entered string, optional>`
- `XMP:Description` mirrors ImageDescription (optional)

**Do not change visible burned-in overlays**; this app cannot alter pixels.

---

## 4) Output behaviors (all must be configurable in GUI)

### 4.1 Output root folder selection
- User selects a destination folder.
- The app creates a run subfolder:
  - `<output_root>/PurwayGeotagger_<YYYYMMDD_HHMMSS>/`

### 4.2 Overwrite vs Copy
Two mutually exclusive modes:
- **Overwrite originals**: write metadata into source JPGs in place.
- **Copy then write**: copy JPGs to output run folder first, then write metadata into copies.

### 4.3 Optional “Flatten / Strip JPGs”
If enabled:
- After successful injection, move all processed JPGs into:
  - `<run_folder>/JPG_FLAT/`
- Optionally remove now-empty source folders (only if user checks “cleanup empty dirs”).

### 4.4 Renaming templates (client profiles)
If enabled:
- Rename output JPGs according to a selected template.
- Templates must be creatable/editable/deletable inside the GUI.
- Provide a start index value per job to prevent duplicates.

Template tokens (must implement):
- `{client}`: client name (from template profile)
- `{date}`: run date `YYYYMMDD`
- `{time}`: run time `HHMMSS`
- `{index}`: incrementing integer starting at job start value
- `{index:05d}`: python format spec support (zero pad etc.)
- `{ppm}`: methane concentration numeric (rounded int by default)
- `{lat}`, `{lon}`: decimal degrees (6 decimals)
- `{orig}`: original base filename (no extension)

On collisions: append `_dupN` suffix (N starts at 1).

### 4.5 Sorting by concentration (PPM)
If enabled, output JPGs are additionally placed into bins:
- bins default:
  - `0000-0999ppm`
  - `1000+ppm`
Configurable in Settings UI (list of bin edges).

Note: sorting should operate on the **output JPG path** after copy/rename.

---

## 5) Job model + progress requirements

The GUI must support multiple jobs queued in a session.

For each job:
- Display:
  - Job name
  - Input folder count
  - Photo count
  - Matched count
  - Success count
  - Failed count
  - Current stage (SCAN / PARSE / MATCH / WRITE / SORT / RENAME / DONE)
  - Progress bar (0–100)
- Provide buttons:
  - Cancel
  - Open output folder (enabled on DONE)
  - Export manifest CSV (enabled on DONE)

Progress must update at least once per 25 files or once per second.

---

## 6) Logs + manifests (must implement)

For each run, write:
- `manifest.csv` containing one row per discovered photo:
  - `source_path, output_path, status, reason, lat, lon, ppm, csv_path, join_method, exif_written`
- `run_log.txt` (human-readable)
- `run_config.json` snapshot of settings used

---

## 7) macOS setup + packaging (must implement)

### 7.1 Field setup script (run once per pilot laptop)
Provide `scripts/macos/setup_macos.sh` that:
- installs Homebrew if missing
- installs Python (3.11 recommended) via brew if missing
- installs ExifTool via brew
- creates a venv
- installs pip requirements
- verifies:
  - `python3 --version`
  - `exiftool -ver`
- `python -c "import PySide6"`

### 7.2 Running during development
Provide `scripts/macos/run_gui.sh` to activate venv and run the GUI.

### 7.3 Building a `.app`
Provide `scripts/macos/build_app.sh` using **PyInstaller**:
- produce `dist/PurwayGeotagger.dmg` (containing .app)

## 7.5 Running the Unsigned App (Important)

Since this application is not signed with an Apple Developer ID, macOS Gatekeeper may block it from opening with a "damaged" or "malicious software" error.

**To run the app:**

1.  **Option A (GUI):**
    - Right-click (or Control-click) the `PurwayGeotagger` app in Finder.
    - Select **Open**.
    - Click **Open** in the warning dialog.

2.  **Option B (Terminal - Guaranteed):**
    - Drag the app to your Applications folder.
    - Run this command in Terminal to remove the quarantine attribute:
      ```bash
      xattr -cr /Applications/PurwayGeotagger.app
      ```

---

## 7.4 Windows dev setup (optional)

For local development on Windows, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\setup_windows.ps1
```

This creates `.venv` and installs `requirements.txt` (+ `requirements-dev.txt` if present).

Run the GUI (Windows):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\run_gui.ps1
```

Run tests (Windows):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\run_tests.ps1
```

---

## 8) Suggested extra features (implement if time allows, but skeletons included)

1. **Dry run** mode: scan+match only; do not write EXIF.
2. **Validation view**: preview a sample of matched rows (first 20) before running.
3. **Auto-detect client profile** from folder naming rules (optional).
4. **CSV schema inspector** tab: show detected columns and which were used.
5. **“Re-run failed only”** button to retry after settings adjustments.

---

## 9) Repository layout (final)

```
purway_geotagger_app/
  README.md
  requirements.txt
  src/
    purway_geotagger/
      app.py
      __init__.py
      core/
        job.py
        photo_task.py
        pipeline.py
        settings.py
        scanner.py
        manifest.py
        run_logger.py
      parsers/
        purway_csv.py
      exif/
        exiftool_writer.py
      ops/
        copier.py
        sorter.py
        renamer.py
        flattener.py
      templates/
        template_manager.py
        models.py
      gui/
        main_window.py
        controllers.py
        workers.py
        models/
          job_table_model.py
        widgets/
          drop_zone.py
          template_editor.py
      util/
        timeparse.py
        paths.py
        errors.py
        platform.py
  config/
    default_templates.json
  scripts/
    setup_macos.sh
    run_gui.sh
    build_macos_app.sh
  tests/
    test_timeparse.py
    test_template_tokens.py
```

---

## 10) Implementation notes for CODEX agent

- Do not invent additional file formats.
- Do not assume fixed CSV headers; use heuristics in `parsers/purway_csv.py`.
- All I/O must be robust: handle spaces, unicode paths, deep directories.
- All long-running work must be off the UI thread (`QThread` + signals).
- Always keep originals safe:
  - when overwrite mode is enabled, create a **.bak** copy option (checkbox) OR at minimum warn user in UI.
- Use `pathlib` everywhere.

---

## 11) Minimal commands

After setup:

```bash
./scripts/macos/run_gui.sh
```

Build .app:

```bash
./scripts/macos/build_app.sh
```

Notes:
- The build uses `--onedir` to bundle Qt plugins more reliably.
- Default templates are bundled from `config/default_templates.json` into the app.

---

## 11.1) Development & tests

Install dev/test dependencies:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Run tests (includes `compileall`):

```bash
./scripts/macos/run_tests.sh
```

---

## 12) ExifTool invocation contract (must use)

Writing metadata is performed by creating a temporary “import CSV” with columns:
- `SourceFile, GPSLatitude, GPSLongitude, DateTimeOriginal, XMP:GPSLatitude, XMP:GPSLongitude, ImageDescription`

Then invoke:

```bash
exiftool -overwrite_original -csv="<import.csv>"
```

In overwrite-originals mode, `SourceFile` points to originals.
In copy mode, `SourceFile` points to copied files.

Note: ExifTool CSV mode has weak per-file status; implement a verification pass if needed.

---

## 13) Concentration units
Assume CSV concentration values are **PPM** unless CSV explicitly indicates otherwise.
Store as float in internal model; show in UI rounded integer by default.

---

End of guide.
