# Purway Geotagger (macOS Pilot App)

Purway Geotagger is a macOS-first PySide6 desktop app for pilot workflows that process Purway raw data exports and Wind Data DOCX generation.

This README is the canonical repo map for humans and agents. Every section includes file pointers so you can jump straight to implementation code.

## What This App Does

- Methane workflow: scan dropped Raw Data folders, correlate JPGs to CSV records, inject EXIF/XMP, generate cleaned methane CSVs, and optionally KMZ outputs.
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
- Generates cleaned methane CSV files beside source methane CSVs.
- Optionally generates KMZ files from cleaned CSV outputs.
- Writes run artifacts (`manifest.csv`, `run_log.txt`, `run_config.json`, `run_summary.json`) to a run log folder.

Code pointers:
- Mode defaults/options mapping: `src/purway_geotagger/gui/controllers.py`
- Mode state model/validation: `src/purway_geotagger/gui/mode_state.py`
- Cleaned CSV + KMZ generation: `src/purway_geotagger/ops/methane_outputs.py`

Output naming:
- Cleaned CSV: `*_Cleaned_<threshold>-PPM.csv`
- KMZ: same stem with `.kmz`
- Naming helper: `src/purway_geotagger/ops/methane_outputs.py`

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
- Contract validation: `src/purway_geotagger/core/wind_template_contract.py`
- Payload builder and input validation: `src/purway_geotagger/core/wind_docx.py`
- DOCX render + write + debug sidecar: `src/purway_geotagger/core/wind_docx_writer.py`

Template paths:
- Bundled production template: `config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- Dev fallback template path candidate: `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- Resolution logic: `src/purway_geotagger/gui/pages/wind_data_logic.py`

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
- NWS primary rows are backfilled field-by-field from METAR, then Open-Meteo when fields are missing.

Code pointers:
- Provider clients + merge logic: `src/purway_geotagger/core/wind_weather_autofill.py`
- Autofill dialog UI: `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`

## Input Scanning and Correlation

Scanner:
- Recursively scans folders for JPG and CSV.
- Skips macOS artifacts (`._*`, `.DS_Store`, `__MACOSX`).
- Implementation: `src/purway_geotagger/core/scanner.py`
- Artifact filter helpers: `src/purway_geotagger/util/paths.py`

CSV parsing and photo matching:
- Column heuristics for photo/lat/lon/time/ppm + extended telemetry.
- Filename join preferred; timestamp join fallback with threshold and ambiguity handling.
- Implementation: `src/purway_geotagger/parsers/purway_csv.py`
- Time parsing utilities: `src/purway_geotagger/util/timeparse.py`

Preview/schema tools:
- Preview builder: `src/purway_geotagger/core/preview.py`
- CSV schema dialog plumbing: `src/purway_geotagger/gui/widgets/schema_dialog.py`

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
  - Validate CSV schema detection and join inputs in Preview/Schema tools
  - Matching logic: `src/purway_geotagger/parsers/purway_csv.py`
  - Preview builder: `src/purway_geotagger/core/preview.py`
  - Run report failure table: `src/purway_geotagger/gui/widgets/run_report_view.py`
- Dropbox/macOS artifact files (`._*`, `.DS_Store`, `__MACOSX`):
  - Scanner skip logic: `src/purway_geotagger/core/scanner.py`
  - Artifact detection helper: `src/purway_geotagger/util/paths.py`

## Test Suite Map

Representative test coverage pointers:
- Scanner/macOS artifact handling: `tests/test_scanner.py`
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
