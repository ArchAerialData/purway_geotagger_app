# Methane Metadata Extension Pre-Plan

## Purpose
Plan and track the implementation needed for Purway Geotagger to write WWM-ready methane target, distance, provenance, and diagnostic metadata directly into processed JPGs.

Primary source:
- `docs/methane-geotagger-extension-request/planning/METHANE_GEOTAGGER_APP_HANDOFF.md`

Locally verified implementation anchors:
- Parser and join model: `src/purway_geotagger/parsers/purway_csv.py`
- Per-photo pipeline state: `src/purway_geotagger/core/photo_task.py`
- Methane metadata validation/counting: `src/purway_geotagger/core/methane_metadata_contract.py`
- Pipeline orchestration and artifacts: `src/purway_geotagger/core/pipeline.py`
- Manifest schema: `src/purway_geotagger/core/manifest.py`
- Run summary schema: `src/purway_geotagger/core/run_summary.py`
- ExifTool import CSV writer: `src/purway_geotagger/exif/exiftool_writer.py`
- Custom ExifTool tag config: `config/exiftool_config.txt`
- GUI version label: `src/purway_geotagger/gui/main_window.py`

## Implemented Contract
- Standard EXIF GPS fields remain image/aircraft coordinates from CSV `longitude` and `latitude`; target coordinates are written only to explicit `XMP-ArchAerial` target fields.
- `XMP-ArchAerial:TargetLongitude`, `TargetLatitude`, `Distance`, `Altitude`, provenance fields, payload model, app version, run ID, join method/delta, and source CSV diagnostics are represented in parser records, `PhotoTask`, manifest rows, and ExifTool import CSV rows.
- Model detection is column-based: `reliability` selects `Purway Model II`; Model III-only diagnostic columns select `Purway Model III`.
- `SourceFileName` uses CSV `file_name` when present and falls back to the matched JPG basename for timestamp joins.
- `JoinDeltaSeconds` is `0.0` for filename joins and the nearest timestamp delta for timestamp joins.
- Methane strictness is mode-scoped: Methane and Combined runs fail matched rows when target coordinates or distance are missing, zero, or invalid; Encroachment-only runs keep legacy success behavior and still report metadata gaps in summaries.

## Output Artifacts
- `_exiftool_import.csv` includes the new `XMP-ArchAerial:*` columns used by ExifTool.
- `manifest.csv` includes:
  - `target_lat`, `target_lon`, `distance`
  - `source_file_name`, `source_csv`, `join_delta_seconds`
  - `payload_model`, `geotagger_version`, `geotagger_run_id`
  - `csv_status`, `err_code`, `snr`, `reliability`, `flight_status`, `dis_code`, `home_distance`, `speed`
- `run_summary.json` includes `methane_metadata` with:
  - `schema_version`
  - `target_coordinates_written`
  - `distance_written`
  - `invalid_target_distance_rows`
  - `join_method_counts`

## Tests
Focused verification lives in:
- `tests/test_purway_csv_parse.py`
- `tests/test_methane_metadata_contract.py`
- `tests/test_exif_extended.py`
- `tests/test_pipeline_artifacts.py`
- `tests/test_run_summary.py`

Canonical focused command:

```bash
python -m pytest tests/test_purway_csv_parse.py tests/test_exif_extended.py tests/test_exiftool_writer.py tests/test_methane_metadata_contract.py tests/test_pipeline_artifacts.py tests/test_pipeline_phase3_e2e.py tests/test_run_summary.py
```

## External References Not Locally Verified
The handoff references downstream `pyweb-local` WWM files that are not present in this repository. This implementation therefore preserves the handoff's field contract and records the local metadata schema version, but downstream WWM parsing behavior must be verified in the downstream repository.
