# Purway Geotagger (macOS Pilot App)

Purway Geotagger is a macOS-first PySide6 desktop app for pilot workflows that process Purway raw data exports and Wind Data DOCX generation.

This README is the canonical repo map for humans and agents. Every section includes file pointers so you can jump straight to implementation code.

## What This App Does

- Methane workflow: scan dropped Raw Data folders, correlate JPGs to CSV/XLSX records, inject EXIF/XMP, generate cleaned methane CSV/XLSX files, and optionally KMZ outputs.
  - Core pipeline: `src/purway_geotagger/core/pipeline.py`
  - Methane outputs: `src/purway_geotagger/ops/methane_outputs.py`
  - Methane GUI: `src/purway_geotagger/gui/pages/methane_page.py`
- Encroachment workflow: copy JPGs into one output folder, optional chronological renaming/indexing, optional flatten/sort operations.
  - Encroachment GUI: `src/purway_geotagger/gui/pages/encroachment_page.py`
  - Rename ordering: `src/purway_geotagger/ops/renamer.py`
- Combined workflow: one run does methane outputs and encroachment copies in one pass.
  - Combined GUI: `src/purway_geotagger/gui/pages/combined_wizard.py`
  - Combined pipeline branch: `src/purway_geotagger/core/pipeline.py`
- Wind Data DOCX workflow: generate production wind docx + debug metadata sidecar; includes weather autofill.
  - Wind GUI: `src/purway_geotagger/gui/pages/wind_data_page.py`
  - Wind core formatting/validation: `src/purway_geotagger/core/wind_docx.py`
  - Wind render/writer: `src/purway_geotagger/core/wind_docx_writer.py`
  - Autofill weather providers: `src/purway_geotagger/core/wind_weather_autofill.py`

## Primary Entry Points

- App entrypoint: `src/purway_geotagger/app.py`
- Main window and tabs: `src/purway_geotagger/gui/main_window.py`
- Job orchestration controller: `src/purway_geotagger/gui/controllers.py`
- Background workers (QThread): `src/purway_geotagger/gui/workers.py`

## Run Modes and Their Outputs

### 1) Methane Mode

Behavior:
- Forces in-place EXIF injection on matched JPGs.
- Generates cleaned methane CSV/XLSX files beside their source metadata files.
- Optionally generates KMZ files from retained rows in cleaned CSV/XLSX outputs.
- Writes run artifacts (`manifest.csv`, `run_log.txt`, `run_config.json`, `run_summary.json`) to a run log folder.

Code pointers:
- Mode defaults/options mapping: `src/purway_geotagger/gui/controllers.py`
- Mode state model/validation: `src/purway_geotagger/gui/mode_state.py`
- Cleaned CSV/XLSX + KMZ generation: `src/purway_geotagger/ops/methane_outputs.py`

Output naming:
- Cleaned CSV: `*_Cleaned_<threshold>-PPM.csv`
- Cleaned XLSX: `*_Cleaned_<threshold>-PPM.xlsx`
- CSV KMZ: `*_Cleaned_<threshold>-PPM.kmz`
- Workbook KMZ: `*_Cleaned_<threshold>-PPM_XLSX.kmz`, grouped by worksheet
- Naming helper: `src/purway_geotagger/ops/methane_outputs.py`

### Calibration filtering and PAC (CSV/XLSX)

In Methane Only and Combined, **Exclude calibration readings below 1 m** starts enabled for each new job. It removes rows only when finite methane concentration is strictly greater than 0 and finite relative altitude is strictly below 1 meter. Exactly 1 meter is retained for the remaining filters. This runs before the PPM threshold and photo-presence checks; the exclusion counts do not overlap. Missing, invalid or non-finite altitude does not establish calibration and produces a warning. Disabling the checkbox restores threshold/photo-only filtering. Photo matching, geotagging and Encroachment copies still use the original input rows.

Each data sheet independently preserves any exact `PAC` header (ignoring case and surrounding whitespace), its position and all retained values, including blanks. When absent, `PAC` is appended using methane concentration divided by relative altitude, rounded to two decimals by the same calculator used for photos. Unavailable/non-finite inputs, altitude <= 0 or non-finite results produce a blank and a count. Existing spreadsheet PAC is authoritative only for cleaned tables; photo PAC is always independently calculated.

XLSX support requires no installed Excel. Every worksheet, including hidden sheets, is inspected. One table per sheet is supported; headers may follow introductory rows and columns may appear in any order. A header must contain a recognized methane field plus an altitude, photo, timestamp or coordinate field. Capitalization, surrounding whitespace, spaces, underscores and hyphens are normalized for field detection. Explicit `methane_concentration` and `relative_altitude` headers take precedence over aliases. Ambiguous mappings, duplicate headers and multiple table headers fail the workbook with a sheet-specific error. Unrelated sheets are copied as saved values and excluded from matching/filtering. Conflicting photo matches across sheets/files report ambiguity with source locations.

Cleaned workbooks are **data-focused copies**: sheet names/order/visibility, introductory rows, column order, retained values and basic date/time number formats are preserved. Literal strings stay text. Formulas become their saved results; missing results fail the entire workbook with instructions to recalculate and save it first. Cached empty-string results are accepted. Original formulas, charts, macros and styling are not preserved. Source CSV/XLSX files are never overwritten. Temporary output files replace earlier cleaned outputs only after successful completion; failed or cancelled writes leave earlier outputs intact.

Run logs/summaries report per-file and per-sheet calibration, threshold, invalid-methane, missing-photo and retained-row counts, plus preserved/calculated/unavailable PAC and altitude warnings. Preview/schema tools and manifests retain workbook, sheet and original row provenance. Legacy summary keys such as `source_csv` and `cleaned_csv` remain compatible and can now contain XLSX paths, with `source_format`, `sheets`, `counts` and `warnings` added. The saved run configuration includes `methane_exclude_calibration`.

Implementation: `parsers/table_inputs.py`, `parsers/columns.py`, `ops/table_export.py`, `ops/methane_outputs.py` and `core/pac_calculator.py` under `src/purway_geotagger/`. Dependencies are pinned to [openpyxl 3.1.5](https://pypi.org/project/openpyxl/3.1.5/) and `defusedxml==0.7.1`; the reader requires XML protection. Formula handling follows [openpyxl's cached-value loading behavior](https://openpyxl.readthedocs.io/en/stable/tutorial.html#loading-from-a-file).

### 2) Encroachment Mode

Behavior:
- Copies input JPGs into a single output area.
- Optional renaming uses template tokens and chronological ordering.
- Logs failures and preserves manifest-level failure reasons.

Code pointers:
- GUI flow: `src/purway_geotagger/gui/pages/encroachment_page.py`
- Copy behavior: `src/purway_geotagger/ops/copier.py`
- Chronological rename/indexing: `src/purway_geotagger/ops/renamer.py`

### 3) Combined Mode

Behavior:
- Runs methane outputs and EXIF pass, then generates encroachment copy output in same run.
- Renaming applies to encroachment copies, not methane originals.

Code pointers:
- GUI wizard: `src/purway_geotagger/gui/pages/combined_wizard.py`
- Combined branch in pipeline: `src/purway_geotagger/core/pipeline.py`

## Wind Data DOCX Feature

The Wind tab produces a rendered report docx from production template placeholders and also writes debug metadata for downstream automation.

Core contract:
- Required placeholders: `CLIENT_NAME`, `SYSTEM_NAME`, `DATE`, `S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`, `TZ`
- Optional placeholder: `REGION_ID` (blank-safe; replaced when present in template)
- WR3A contract lock: keep system placeholder unchanged and use `REGION_ID` for region in auto-selected templates.
- Contract validation: `src/purway_geotagger/core/wind_template_contract.py`
- Template profile auto-selector: `src/purway_geotagger/core/wind_template_selector.py`
- Payload builder and input validation: `src/purway_geotagger/core/wind_docx.py`
- DOCX render + write + debug sidecar: `src/purway_geotagger/core/wind_docx_writer.py`

Template paths:
- Bundled production template: `config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- WR3A system-only template: `config/wind_templates/System Only/WindData_ClientName_SYSTEM_YYYY_MM_DD.docx`
- WR3A region-only template: `config/wind_templates/Region Only/WindData_ClientName_Region_YYYY_MM_DD.docx`
- WR3A system+region template: `config/wind_templates/System-Region/WindData_ClientName_REGION_SYSTEM_YYYY_MM_DD.docx`
- Dev fallback template path candidate: `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- Resolution logic: `src/purway_geotagger/gui/pages/wind_data_logic.py`

WR3A template filename token mapping:
- `ClientName` -> filename-safe client value from GUI.
- `SYSTEM` -> filename-safe system value from GUI.
- `Region`/`REGION` -> filename-safe region value from GUI.
- `YYYY_MM_DD` -> normalized report date.

Generated artifacts:
- DOCX output: `WindData_<ClientName>_<YYYY_MM_DD>.docx` (collision-safe suffixes `_01`, `_02`, ...)
- Debug JSON sidecar: `<output>.debug.json`
- Embedded custom XML metadata in DOCX: `customXml/purway_wind_metadata.xml`

### Wind Autofill Data Sources (Current Hierarchy)

Provider order for full-row fetch:
1. NOAA/NWS observations (`api.weather.gov`)
2. AviationWeather METAR observations (`aviationweather.gov`)
3. Open-Meteo historical archive (`archive-api.open-meteo.com`)

Missing-field backfill order:
- Partial rows from either NWS or METAR continue through the remaining providers, independently for Start and End.
- Start/End time boxes on both the main Wind Data page and the autofill dialog can be fully selected, cleared, pasted into and retyped. Complete entries like `09:30` / `0930` become `9:30 AM`, and `15:30` / `1530` become `3:30 PM`. Explicit `3:30 PM` input and manual AM/PM selection also work. Blank, incomplete and invalid entries block report generation or lookup without restoring the old value. DOCX times remain in 12-hour format.
- Station readings default to a maximum **25-mile radial distance** and **60-minute time difference** from each requested time. The lookup dialog can adjust these limits; they are application defaults, not a guarantee of site conditions.
- Open-Meteo fallback fields are explicitly labeled **estimated** (historical model/reanalysis data).
- **View Weather Sources** expands each field's station/model, distance, actual measurement time and source link. Mixed sources and unresolved fields are disclosed; manual values remain editable.
- Changing a report date/time/timezone flags previously imported values for review. Autofill derives CST/CDT (or the applicable zone) from the selected location and report date.
- Per-field evidence, lookup context, original imported values and manual-edit status are saved in `.debug.json` and DOCX `customXml/purway_wind_metadata.xml`.
- Manual generation remains available when weather lookup fails. Missing gusts are never assumed to be zero.

Code pointers:
- Provider clients + merge logic: `src/purway_geotagger/core/wind_weather_autofill.py`
- Autofill dialog UI: `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`

### Calibration/XLSX verification (2026-09-28)

- Full regression suite: **232 passed**; source log: `build/calibration-xlsx-tests.log`.
- Real ExifTool verification covered CSV/XLSX inputs, calibration photo retention, independently calculated photo PAC and Encroachment copies. Source tables remained unchanged.
- Methane/Combined controls and populated reports reviewed in light/dark themes; wheel protection retained.
- Latest Windows build: **2026-09-28T16:34:27.6167969Z**, at the stable `dist/windows/PurwayGeotagger/PurwayGeotagger.exe` path used by `methane`. Executable hash, all 69 source hashes, embedded changed modules, XLSX/XML dependencies and native startup/clean exit verified. Full results are in `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`.

## Input Scanning and Correlation

Scanner:
- Recursively scans folders for JPG/JPEG, CSV and XLSX. Excel lock files (`~$*`), generated `_Cleaned_<threshold>-PPM` tables, `.xls` and `.xlsm` are excluded.
- Skips macOS artifacts (`._*`, `.DS_Store`, `__MACOSX`).
- Implementation: `src/purway_geotagger/core/scanner.py`
- Artifact filter helpers: `src/purway_geotagger/util/paths.py`

CSV/XLSX parsing and photo matching:
- Column heuristics for photo/lat/lon/time/ppm + extended telemetry.
- Filename join preferred; timestamp join fallback with threshold and ambiguity handling.
- Implementation: `src/purway_geotagger/parsers/purway_csv.py`
- Time parsing utilities: `src/purway_geotagger/util/timeparse.py`

Preview/schema tools:
- Preview builder: `src/purway_geotagger/core/preview.py`
- CSV/XLSX schema dialog plumbing: `src/purway_geotagger/gui/widgets/schema_dialog.py`

## EXIF/XMP Injection Contract

EXIF writing engine:
- Uses ExifTool import CSV write pass + verification read pass.
- Writer: `src/purway_geotagger/exif/exiftool_writer.py`

Required GPS tags:
- `GPSLatitude`, `GPSLongitude`, `GPSLatitudeRef`, `GPSLongitudeRef`

Optional/default tags:
- `DateTimeOriginal`
- `ImageDescription`
- `XMP:GPSLatitude`, `XMP:GPSLongitude`, `XMP:Description` (when enabled)

Extended custom XMP namespace fields:
- Written under `XMP-ArchAerial:*` keys (methane concentration, PAC, UAV/gimbal values, capture time, focal length, zoom).
- CSV field map and write contract: `src/purway_geotagger/exif/exiftool_writer.py`

ExifTool resolution order:
1. `PURWAY_EXIFTOOL_PATH`
2. bundled app binary path (`bin/exiftool`)
3. PATH lookup
4. common macOS locations

## Pipeline Stages and Run Artifacts

Pipeline stage sequence:
- `SCAN -> PARSE -> METHANE_OUTPUTS (mode-dependent) -> COPY/PREPARE -> MATCH -> WRITE -> ENCROACHMENT_COPY (combined) -> RENAME -> SORT -> FLATTEN -> DONE`
- Pipeline orchestration: `src/purway_geotagger/core/pipeline.py`

Per-run files (always expected even on cancel/failure):
- `run_config.json`
- `run_log.txt`
- `manifest.csv`
- `run_summary.json`

Writers/models:
- Manifest writer/model: `src/purway_geotagger/core/manifest.py`
- Run logger: `src/purway_geotagger/core/run_logger.py`
- Run summary model/writer: `src/purway_geotagger/core/run_summary.py`

Run report UI:
- Reads summary + manifest + logs and shows outputs/failures table.
- `src/purway_geotagger/gui/widgets/run_report_view.py`

## GUI Structure Map

Top-level tabs in main window:
- Run
- Jobs
- Templates
- Wind Data
- Help

File pointers:
- Window shell and tab wiring: `src/purway_geotagger/gui/main_window.py`
- Home mode picker: `src/purway_geotagger/gui/pages/home_page.py`
- Jobs table/filter models: `src/purway_geotagger/gui/models/job_table_model.py`, `src/purway_geotagger/gui/models/jobs_filter_proxy_model.py`
- Theme + styles: `src/purway_geotagger/gui/theme.py`, `src/purway_geotagger/gui/style_sheet.py`

Reusable widgets:
- Drop zone: `src/purway_geotagger/gui/widgets/drop_zone.py`
- Sticky nav row: `src/purway_geotagger/gui/widgets/sticky_nav_row.py`
- Template editor: `src/purway_geotagger/gui/widgets/template_editor.py`
- Settings dialog: `src/purway_geotagger/gui/widgets/settings_dialog.py`
- Wind entry grid: `src/purway_geotagger/gui/widgets/wind_entry_grid.py`

## Template System (Photo Renaming)

Template data model:
- `src/purway_geotagger/templates/models.py`

Template manager:
- Default templates from `config/default_templates.json`
- User template overrides in user config dir (`templates.json`)
- Implementation: `src/purway_geotagger/templates/template_manager.py`

Supported rename tokens:
- `{client}`, `{date}`, `{time}`, `{index}`, `{index:05d}`, `{ppm}`, `{lat}`, `{lon}`, `{orig}`

## Config, Resource Paths, and Persistence

Settings:
- Model: `src/purway_geotagger/core/settings.py`
- Stored at macOS user config path (`~/Library/Application Support/PurwayGeotagger/settings.json`)

Resource path helpers:
- GUI/core helper: `src/purway_geotagger/core/utils.py`
- Utility helper: `src/purway_geotagger/util/paths.py`

Bundled static resources:
- app config: `config/default_templates.json`, `config/exiftool_config.txt`, `config/wind_templates/...`
- assets: `assets/`

## macOS Scripts, Build, Signing

Local dev scripts:
- Setup machine/venv: `scripts/macos/setup_macos.sh`
- Run GUI: `scripts/macos/run_gui.sh`
- Run tests: `scripts/macos/run_tests.sh`

Build and packaging:
- PyInstaller build: `scripts/macos/build_app.sh`
- Optional spec-based build config: `PurwayGeotagger.spec`

Signing/notarization docs/scripts:
- Setup guide: `scripts/macos/APPLE_SIGNING_NOTARIZATION_SETUP.md`
- Sign/notarize script: `scripts/macos/sign_and_notarize.sh`
- CI pipeline docs/scripts: `scripts/ci/README.md`, `scripts/ci/macos_build.sh`, `scripts/ci/macos_package.sh`, `scripts/ci/macos_sign_and_package.sh`
- Workflow: `.github/workflows/macos-build.yml`

## Canonical Planning and Tracking Docs

Use these as source-of-truth planning artifacts:
- Global phase gates: `IMPLEMENTATION_PHASES.md`
- Pilot workflow context + phased gaps: `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`
- Wind feature phased gates: `WIND_DATA_IMPLEMENTATION_PHASES.md`
- Wind Region/System variant track: `WIND_DATA_REGION_FIELD_IMPLEMENTATION_PHASES.md`
- Wind autofill spike tracker: `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md`
- Wind feature/change logs: `WIND_DATA_DOCX_FEATURE_PLAN.md`, `WIND_DATA_CHANGESET_NOTES.md`

## Development Commands

Install dependencies:

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
```

Run the app from source:

```bash
bash scripts/macos/run_gui.sh
```

Run tests:

```bash
python3 -m pytest -q
```

Build macOS app:

```bash
bash scripts/macos/build_app.sh
```

## Troubleshooting

- ExifTool missing at runtime:
  - Check Settings > Tool Paths (`src/purway_geotagger/gui/widgets/settings_dialog.py`)
  - Resolver logic/order: `src/purway_geotagger/exif/exiftool_writer.py`
  - macOS setup/build notes: `scripts/macos/README.md`
- Many unmatched photos:
  - Validate CSV/XLSX schema detection and join inputs in Preview/Schema tools
  - Matching logic: `src/purway_geotagger/parsers/purway_csv.py`
  - Preview builder: `src/purway_geotagger/core/preview.py`
  - Run report failure table: `src/purway_geotagger/gui/widgets/run_report_view.py`
- Dropbox/macOS artifact files (`._*`, `.DS_Store`, `__MACOSX`):
  - Scanner skip logic: `src/purway_geotagger/core/scanner.py`
  - Artifact detection helper: `src/purway_geotagger/util/paths.py`

## Test Suite Map

Representative test coverage pointers:
- Scanner/macOS artifact handling: `tests/test_scanner.py`
- Calibration/XLSX/PAC integration: `tests/test_table_workflows.py`, `tests/test_calibration_gui.py`
- CSV parsing + join logic: `tests/test_purway_csv_parse.py`, `tests/test_join_logic.py`
- EXIF writer contract: `tests/test_exiftool_writer.py`, `tests/test_exif_extended.py`
- Pipeline and outputs: `tests/test_pipeline_artifacts.py`, `tests/test_pipeline_phase3_e2e.py`, `tests/test_methane_outputs.py`
- Renaming chronology: `tests/test_renamer_chronological.py`
- Wind template/docx/autofill: `tests/test_wind_template_contract.py`, `tests/test_wind_docx_writer.py`, `tests/test_wind_weather_autofill.py`
- GUI logic tests: `tests/test_wind_page_logic.py`, `tests/test_wind_autofill_dialog.py`, `tests/test_main_window_startup.py`

## Repository Layout

```text
purway_geotagger_app/
  AGENTS.md
  README.md
  IMPLEMENTATION_PHASES.md
  PILOT_RAW_DATA_CONTEXT_AND_PLAN.md
  WIND_DATA_IMPLEMENTATION_PHASES.md
  config/
  assets/
  scripts/
    macos/
    windows/
    ci/
  src/purway_geotagger/
    app.py
    core/
    parsers/
    exif/
    ops/
    gui/
    templates/
    util/
  tests/
```

## Notes for New Agents

- Read `AGENTS.md` first.
- Treat this README as the navigation index, then jump to the file pointers in the section relevant to your task.
- Keep macOS/Finder-launch behavior as default assumption for packaging/runtime decisions.

## Deferred Manual Gates (To Revisit)

The following are intentionally deferred manual checks to complete before final distribution:

- `IMPLEMENTATION_PHASES.md`
  - Phase 0 GUI startup/manual run check
  - Phase 4 manual smoke
  - Phase 5 packaged app launch smoke
- `WIND_DATA_IMPLEMENTATION_PHASES.md`
  - W3 manual macOS smoke and visual QA gate
  - Remaining release/manual signoff gates
- `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`
  - Finder-launch ExifTool preflight gate
  - Phase 4 and 4A pilot-manual UX gates
  - Phase 5 new-pilot end-to-end manual gate


### Scrolling and form inputs

Form values throughout the app (including number, date/time and dropdown fields)
ignore the mouse wheel and trackpad scrolling, even while focused. Scrolling over
a field scrolls its containing page. Type values or use keyboard arrows, clickable
steppers, calendar buttons and dropdown selections to make intentional changes.
This policy is installed centrally in `gui/input_wheel_guard.py` at app startup
and also covers dialogs opened later.

### Rebuild the Windows app locally

After installing the pinned requirements and Windows `tzdata`, run the tests, then:

```powershell
./scripts/windows/build_exe.ps1 -PythonExe ./build/ci-venv311/Scripts/python.exe
```

Use `-PythonExe python` for another configured build environment. The same script is used by
both Windows CI workflows. It builds in staging, validates bundled resources and ExifTool,
then replaces `dist/windows/PurwayGeotagger`, preserving the previous folder with a timestamp.
`build-info.json` records the executable hash and Python source hashes used for verification.
Keep `PurwayGeotagger.exe` and its `_internal` folder together.

Every Windows build must publish the newest successful app to this stable path:
`dist/windows/PurwayGeotagger/PurwayGeotagger.exe`. Always use the script above; do not
leave a new build only in staging or a versioned directory. Verify the output and
`build-info.json` before declaring the build complete.

On this workstation, Git Bash's `~/.bashrc` defines `methane` to launch that executable:

```bash
alias methane='"/c/Users/rbake/Desktop/VS Code Shortcuts/purway_geotagger_app/dist/windows/PurwayGeotagger/PurwayGeotagger.exe"'
```

Open a new Git Bash terminal, or run `source ~/.bashrc`, then type `methane`.
The alias always uses the latest successful local build without needing edits.
If the repository moves, update the absolute path in the alias.

Local builds are manual; saving code does not rebuild the app. The `windows-exe`
GitHub workflow is manually triggered, while `windows-installer` runs on pushes to
`main` or manual dispatch. Those workflows build on GitHub and do not update this
workstation's executable. Run the local build command above to refresh it.


### Verifying and sharing the local Windows build

The window title displays the app version and unique build ID (UTC build stamp plus an input fingerprint). Hover over the header version for the base Git commit, exact UTC build time, full fingerprint and whether local source changes were included. Development launches explicitly show `development`; older/missing package metadata shows `build unknown`.

Use `scripts/windows/build_exe.ps1` for Windows builds. It snapshots Python sources, configuration, assets, Windows build scripts and dependency requirements before packaging, embeds `build-info.json`, and rejects promotion if those inputs change during the build. The complete successful app replaces the stable directory used by the `methane` alias. Merely committing or pulling source does not refresh that executable.

After verifying the app, run `python scripts/windows/package_portable.py` using the build Python environment. It creates a version/build-named ZIP under `dist/share/`, checks the EXE against its build record, verifies ZIP integrity and every packaged application file, and includes launch instructions and checksums. Recipients must **Extract All**, keep `_internal` beside `PurwayGeotagger.exe`, and run the extracted EXE. Python, Git Bash and GitHub Actions are unnecessary on their workstations.


November 23 maintenance: Partial edits to an already formatted time preserve its AM/PM selection; selecting all and replacing or clearing/retyping interprets bare input as 24-hour time. This applies to both main Wind Data and autofill time controls. Source-table discovery excludes app-generated `manifest.csv` and `_exiftool_import.csv` as well as cleaned outputs, so a folder can be processed again with previous run logs beneath it.
