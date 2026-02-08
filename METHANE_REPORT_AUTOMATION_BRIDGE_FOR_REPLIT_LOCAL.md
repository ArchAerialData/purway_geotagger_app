# Methane Report Automation Bridge (purway_geotagger_app -> replit-local)

Date: 2026-02-08  
Prepared in: `/Users/archaerialtesting/Documents/purway_geotagger_app`  
Reviewed planning source: `/Users/archaerialtesting/Documents/replit-local/.future-tasks`

## Purpose

Align methane report automation planning in `replit-local` with the actual implemented data contracts in this repo, so pilot-generated artifacts hand off cleanly with no hidden assumptions.

This document is intentionally implementation-focused and can be handed to an agent working natively inside `replit-local`.

## Scope Reviewed

- Other repo planning docs (read-only):
  - `/Users/archaerialtesting/Documents/replit-local/.future-tasks/methane integration planning/markdown_files/2026-02-04_methane-report-automation-integration-brainstorm.md`
  - `/Users/archaerialtesting/Documents/replit-local/.future-tasks/methane_reporting_image_creator/pyweb_local_delivery_options_ranked.md`
  - plus non-methane `.future-tasks` markdowns for context
- This repo source-of-truth implementation:
  - EXIF/XMP injection, CSV correlation, methane cleaned CSV/KMZ outputs
  - Wind DOCX generation + embedded metadata
  - Run artifacts (manifest/run_summary) and mode behavior

## Source-of-Truth Contracts in This Repo

### 1) Methane photo metadata injection contract

Authoritative files:
- `src/purway_geotagger/exif/exiftool_writer.py`
- `config/exiftool_config.txt`
- `src/purway_geotagger/parsers/purway_csv.py`
- `src/purway_geotagger/core/pac_calculator.py`

Written tags for matched photos:
- EXIF:
  - `GPSLatitude`
  - `GPSLongitude`
  - `GPSLatitudeRef`
  - `GPSLongitudeRef`
  - `GPSAltitude`
  - `DateTimeOriginal` (when available from CSV/time parse)
  - `ImageDescription`
- Custom XMP namespace:
  - Namespace URI: `http://ns.archaerial.com/1.0/`
  - Tags:
    - `XMP-ArchAerial:MethaneConcentration`
    - `XMP-ArchAerial:PAC`
    - `XMP-ArchAerial:RelativeAltitude`
    - `XMP-ArchAerial:LightIntensity`
    - `XMP-ArchAerial:UAVPitch`
    - `XMP-ArchAerial:UAVRoll`
    - `XMP-ArchAerial:UAVYaw`
    - `XMP-ArchAerial:GimbalPitch`
    - `XMP-ArchAerial:GimbalRoll`
    - `XMP-ArchAerial:GimbalYaw`
    - `XMP-ArchAerial:CaptureTime`
    - `XMP-ArchAerial:CameraFocalLength`
    - `XMP-ArchAerial:CameraZoom`
- Optional XMP GPS/description (enabled by default in app settings):
  - `XMP:GPSLatitude`
  - `XMP:GPSLongitude`
  - `XMP:Description`

Important details:
- `ImageDescription` is generated as `ppm=<rounded_int>; source_csv=<csv_name>` (+ optional `purway_payload=...`).
- PAC is computed as `ppm / relative_altitude` with 2-decimal rounding when altitude > 0; otherwise null.
- Writes are verified post-write for GPS presence.

### 2) Photo <-> CSV matching contract

Authoritative files:
- `src/purway_geotagger/parsers/purway_csv.py`
- `src/purway_geotagger/util/timeparse.py`

Matching order:
1. Filename join if CSV has a photo/file-like column.
2. Timestamp nearest-neighbor join if filename timestamp and CSV timestamp exist.
3. Failure with explicit reasons when neither works or join is ambiguous/out-of-threshold.

Key operational behavior:
- Photo filename parsing supports common timestamp formats.
- CSV timestamp parsing supports Purway format with optional milliseconds.
- Max join delta is configurable (default 3 seconds).

### 3) Methane cleaned CSV + KMZ outputs

Authoritative file:
- `src/purway_geotagger/ops/methane_outputs.py`

Contract:
- Cleaned CSV naming:
  - `<source_stem>_Cleaned_<threshold>-PPM.csv`
- KMZ naming:
  - same stem as cleaned CSV, `.kmz`
- Location:
  - written next to the source methane CSV (not into a new methane export root)
- Filtering:
  - keep rows where ppm column value >= threshold
  - if a photo column exists, rows are additionally filtered to rows whose photo value matches a JPG in the same folder
- KMZ content:
  - simple placemarks from cleaned CSV lat/lon with placemark name set from ppm value

### 4) Run artifacts contract

Authoritative files:
- `src/purway_geotagger/core/pipeline.py`
- `src/purway_geotagger/core/manifest.py`
- `src/purway_geotagger/core/run_summary.py`
- `src/purway_geotagger/core/settings.py`

Per-run artifacts written under:
- `PurwayGeotagger_<YYYYMMDD_HHMMSS>/`

Always produced:
- `run_config.json`
- `run_log.txt`
- `manifest.csv`
- `run_summary.json`

Manifest columns include methane telemetry and correlation diagnostics:
- `source_path`, `output_path`, `status`, `reason`, `lat`, `lon`, `ppm`, `csv_path`, `join_method`, `exif_written`
- plus extended fields:
  - `altitude`, `relative_altitude`, `light_intensity`, `pac`
  - `uav_pitch`, `uav_roll`, `uav_yaw`
  - `gimbal_pitch`, `gimbal_roll`, `gimbal_yaw`
  - `camera_focal_length`, `camera_zoom`
  - `capture_time`

### 5) Wind DOCX output contract (for methane report context fields)

Authoritative files:
- `src/purway_geotagger/core/wind_docx.py`
- `src/purway_geotagger/core/wind_docx_writer.py`
- `src/purway_geotagger/core/wind_template_contract.py`
- `src/purway_geotagger/gui/pages/wind_data_page.py`

Generation contract:
- Filename:
  - `WindData_<ClientNoSpaces>_<YYYY_MM_DD>.docx`
- Sidecar debug JSON:
  - `<same_stem>.debug.json`
- Template placeholders rendered:
  - `CLIENT_NAME`, `SYSTEM_NAME`, `DATE`, `TZ`, `S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`
- Embedded metadata inside generated DOCX:
  - ZIP path: `customXml/purway_wind_metadata.xml`
  - Root: `<purwayWindMetadata schemaVersion="1">`
  - Sections:
    - `templatePlaceholders` entries for the 8 rendered placeholders
    - `componentValues` entries:
      - `S_WIND`, `S_SPEED`, `S_GUST`, `S_TEMP`
      - `E_WIND`, `E_SPEED`, `E_GUST`, `E_TEMP`

Autofill provider hierarchy currently implemented:
- NWS station observations -> AviationWeather METAR -> Open-Meteo archive
- Missing fields are backfilled in that order.

## Gaps/Mismatches to Fix in replit-local Planning

## Critical

1. Do not assume `_H` filename suffix exists in outputs from this app.
- This app currently does not add `_H` in methane mode.
- If `_H` policy is used in `replit-local`, it must be optional and not required for ingestion.

2. Do not assume pipeline ID is encoded in methane photo filenames from this app.
- Methane mode writes metadata in place and keeps original names.
- Pipeline context should come from coordinate/KMZ matching or explicit run inputs.

3. Treat XMP methane fields as the primary methane telemetry source.
- Use `ArchAerial:MethaneConcentration` and `ArchAerial:PAC` first.
- `ImageDescription` contains rounded `ppm` and is better as fallback/audit text, not primary numeric source.

4. Parse wind context from embedded DOCX metadata, not free-form paragraph text, when using this app's wind DOCX.
- Read `customXml/purway_wind_metadata.xml` first.
- Fall back to manual/legacy parsing only when this custom XML is absent.

5. Camera focal/zoom assumptions in planning need correction.
- Current source app writes `XMP-ArchAerial:CameraFocalLength` and `XMP-ArchAerial:CameraZoom`.
- Do not rely on EXIF `FocalLength` / `DigitalZoomRatio` being populated by this app.

## High Priority

6. Add ingestion support for run artifacts (`manifest.csv` and `run_summary.json`) as an optional fast path.
- These contain ready-to-use matched telemetry and output bookkeeping.
- They should be used when present, with direct metadata parse as fallback.

7. Explicitly support missing PAC.
- PAC can legitimately be absent (e.g., missing/invalid relative altitude in source data).
- Template behavior for missing PAC must be deterministic (blank or `N/A`, per client policy).

8. Time handling should stay dual-source and auditable.
- `XMP-ArchAerial:CaptureTime` is high precision but may be timezone-naive.
- `EXIF DateTimeOriginal` should remain available for reconciliation.

## Recommended Ingestion Contract for replit-local

Use this as the handoff interface between the repos.

### Required inputs (default profile)

- Injected methane JPGs from this app.
- Wind DOCX generated by this app (`WindData_*.docx`) when methane templates need START/END wind rows.

### Not required for default runs

- `manifest.csv`
- `run_summary.json`
- `run_log.txt`
- methane source CSV sidecars

These files can still be supported as optional diagnostics/fast-path helpers, but they should not be required for normal ingestion.

### Sister-repo GUI inputs (explicitly user-entered there)

The following values are not expected from this repo output and should be entered/selected in `replit-local`:

- `PILOT_SELECTED` / `PILOTS`
- `AOI_NUM` / `AOI_TEXT`
- `SYSTEM_ID` / report-level client context overrides
- hit policy controls (threshold-only / `_H` / hybrid) and threshold overrides
- manual pipeline/system selection fallback when KMZ coordinate matching is unavailable

### Field precedence (recommended)

PPM:
1. `XMP-ArchAerial:MethaneConcentration`
2. Parse `ppm=` from `ImageDescription` fallback

PAC:
1. `XMP-ArchAerial:PAC`
2. Derive from ppm/relative altitude only if both values are available and positive

Capture time:
1. `XMP-ArchAerial:CaptureTime`
2. `EXIF DateTimeOriginal`
3. Filename timestamp fallback

Coordinates:
1. EXIF GPS (`GPSLatitude`, `GPSLongitude`)
2. XMP GPS fallback if needed

Wind start/end context:
1. DOCX `customXml/purway_wind_metadata.xml`
2. DOCX debug sidecar JSON (if present with same stem)
3. Manual UI entry fallback

## Planning Updates to Apply in replit-local Markdown

Target file:
- `/Users/archaerialtesting/Documents/replit-local/.future-tasks/methane integration planning/markdown_files/2026-02-04_methane-report-automation-integration-brainstorm.md`

Add/update these points:

1. Add a "Purway app handoff contract" section with exact keys listed in this bridge doc.
2. In hit-selection section, mark `_H` as optional policy, not assumed input convention.
3. In filename/pipeline sections, state methane filenames from source app may be untouched raw capture names.
4. In wind parsing section, prioritize `customXml/purway_wind_metadata.xml` parsing and fallback rules.
5. In telemetry extraction section, define authoritative field precedence (XMP first, description fallback).
6. In open items, add explicit handling policy for missing PAC and timezone-naive timestamps.
7. In validation plan, add fixture-based tests using:
   - sample injected JPGs
   - sample injected wind DOCX containing custom XML metadata

## Suggested Validation Matrix for replit-local

1. Parse one injected JPG with full telemetry:
- assert ppm/pac/lat/lon/time are correctly extracted.

2. Parse one injected JPG with missing PAC:
- assert report behavior is deterministic and non-crashing.

3. Parse generated wind DOCX custom XML:
- assert `S_TIME`, `E_TIME`, `S_STRING`, `E_STRING`, and `componentValues` are extracted exactly.

4. Run with methane filenames that do not include pipeline IDs:
- assert pipeline/system resolution still succeeds via KMZ/manual fallback.

5. Run with and without `manifest.csv`:
- assert same final placeholder values are produced.

6. Validate legacy fallback path:
- if custom wind XML missing, require explicit warning and manual override path.

7. Validate strict JPG+DOCX mode:
- with no manifest/run_summary/CSV present, assert the report still renders correctly using photo metadata + wind DOCX + GUI-entered report fields.

## Decisions Still Open (Product/Workflow)

These remain open in the other repo planning and should be resolved before implementation lock:

1. Final hit-policy precedence (threshold-only vs `_H` vs hybrid default behavior).
2. Timezone display policy for report date/time normalization.
3. Methane deliverables folder structure/root naming conventions.
4. Template-specific fillable field bounding boxes for methane PDFs.

## Final Notes

- No changes were made in `/Users/archaerialtesting/Documents/replit-local/`.
- This bridge file is designed to be consumed by an agent working in that repo so implementation can proceed with minimal ambiguity.
