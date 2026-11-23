# WWM Methane Metadata Output Handoff

## Purpose
This document hands off the verified Purway Geotagger output set for downstream WWM methane XLSX and Methane Workspace ingestion work.

The prior implementation request is satisfied for valid rows: processed JPGs now carry WWM-ready methane target, distance, provenance, payload, run, and diagnostic metadata directly in `XMP-ArchAerial` tags, while standard EXIF GPS remains the aircraft/image position.

## Source References

Repo-relative implementation and requirement references:

- Requirement source: `docs/methane-geotagger-extension-request/planning/METHANE_GEOTAGGER_APP_HANDOFF.md`
- Implemented plan summary: `docs/methane-geotagger-extension-request/planning/METHANE_GEOTAGGER_EXTENSION_PREPLAN.md`
- XMP tag definitions: `config/exiftool_config.txt`
- ExifTool import writer: `src/purway_geotagger/exif/exiftool_writer.py`
- Manifest schema: `src/purway_geotagger/core/manifest.py`
- Run summary schema: `src/purway_geotagger/core/run_summary.py`
- Metadata validation/counting: `src/purway_geotagger/core/methane_metadata_contract.py`

External processed-output root:

```text
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2
```

## Satisfied Requirements

- Successful processed JPGs include explicit methane target/distance fields:
  - `XMP-ArchAerial:TargetLongitude`
  - `XMP-ArchAerial:TargetLatitude`
  - `XMP-ArchAerial:Distance`
  - `XMP-ArchAerial:Altitude`
- Successful processed JPGs include provenance and join fields:
  - `XMP-ArchAerial:SourceFileName`
  - `XMP-ArchAerial:SourceCSV`
  - `XMP-ArchAerial:JoinMethod`
  - `XMP-ArchAerial:JoinDeltaSeconds`
- Successful processed JPGs include payload/run fields:
  - `XMP-ArchAerial:PayloadModel`
  - `XMP-ArchAerial:GeotaggerVersion`
  - `XMP-ArchAerial:GeotaggerRunId`
- Successful processed JPGs include diagnostics:
  - shared: `XMP-ArchAerial:Status`, `ErrCode`, `SNR`
  - Model II: `XMP-ArchAerial:Reliability`
  - Model III: `XMP-ArchAerial:FlightStatus`, `DisCode`, `HomeDistance`, `Speed`
- Existing EXIF/XMP fields continue to be written, including standard GPS, `GPSAltitude`, `DateTimeOriginal`, `ImageDescription`, `XMP-dc:Description`, `XMP-exif:GPSLatitude`, and `XMP-exif:GPSLongitude`.
- Standard EXIF GPS remains aircraft/image position from manifest `lat` and `lon`; target coordinates are not overloaded into standard GPS and are available only through `XMP-ArchAerial:TargetLatitude` and `XMP-ArchAerial:TargetLongitude`.
- Sidecar artifacts include the new audit columns and counts:
  - `manifest.csv`
  - `_exiftool_import.csv`
  - `run_summary.json`
  - `run_config.json`
  - `run_log.txt`

## Output Overview

### Purway Model II

- Direct JPGs: 5
- Tagged successfully: 5
- Failed/skipped: 0
- Run ID: `bf932b20-22e9-449e-a894-f03e17ee0d7b`
- Metadata schema version: `wwm-methane-xmp-v1`
- Join methods: `FILENAME: 5`

Direct processed JPGs:

```text
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\20260506_113534.JPG
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\20260506_113549.JPG
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\20260506_113554.JPG
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\20260506_113600.JPG
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\20260506_113612.JPG
```

Proof artifacts:

```text
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\PurwayGeotagger_20260508_133813\manifest.csv
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\PurwayGeotagger_20260508_133813\_exiftool_import.csv
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\PurwayGeotagger_20260508_133813\run_summary.json
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\PurwayGeotagger_20260508_133813\run_config.json
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\PurwayGeotagger_20260508_133813\run_log.txt
```

### Purway Model III

- Direct JPGs: 5
- Tagged successfully: 4
- Failed/skipped: 1
- Run ID: `077ea57a-23b2-4cf1-9eb8-508089f0f09c`
- Metadata schema version: `wwm-methane-xmp-v1`
- Join methods: `FILENAME: 5`
- Intentional validation failure count: 1

Direct processed JPGs:

```text
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_015818.jpg
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_015822.jpg
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_015825.jpg
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_020206.jpg
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_020210.jpg
```

Successful tagged Model III JPGs:

```text
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_015818.jpg
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_015822.jpg
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_020206.jpg
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_020210.jpg
```

Intentional failed validation case:

```text
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_015825.jpg
```

Failure reason from `manifest.csv`:

```text
missing required methane target/distance metadata: distance is blank, zero, or invalid
```

This failed row has `distance=0.0` in the parsed metadata and was intentionally blocked by Methane strict validation before EXIF/XMP writing. Downstream ingestion should treat this sample as a validation/failure fixture, not as a successful tagged-image fixture.

Proof artifacts:

```text
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\PurwayGeotagger_20260508_133826\manifest.csv
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\PurwayGeotagger_20260508_133826\_exiftool_import.csv
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\PurwayGeotagger_20260508_133826\run_summary.json
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\PurwayGeotagger_20260508_133826\run_config.json
F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\PurwayGeotagger_20260508_133826\run_log.txt
```

## Verification Results

ExifTool audit was run with this repo's custom config:

```text
config/exiftool_config.txt
```

Results:

- Model II direct JPGs: 5 checked, 5 successful, 0 missing required metadata cells, 0 embedded-vs-manifest mismatches.
- Model III direct JPGs: 5 checked, 4 successful, 1 expected failed row, 0 embedded-vs-manifest mismatches on successful rows.
- `_exiftool_import.csv` includes all required new `XMP-ArchAerial:*` columns for both models.
- `_exiftool_import.csv` has no blank target/distance rows:
  - Model II import rows: 5
  - Model III import rows: 4
- Signed standard GPS values match manifest aircraft/image `lat` and `lon` on all successful rows.
- Model-specific diagnostics are present on successful rows:
  - Model II: `XMP-ArchAerial:Reliability`
  - Model III: `XMP-ArchAerial:FlightStatus`, `XMP-ArchAerial:DisCode`, `XMP-ArchAerial:HomeDistance`, `XMP-ArchAerial:Speed`

Representative successful Model II embedded values:

```text
SourceFile: F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model II\20260506_113534.JPG
XMP-ArchAerial:TargetLatitude: 31.5127067
XMP-ArchAerial:TargetLongitude: -104.0075673
XMP-ArchAerial:Distance: 79.9
XMP-ArchAerial:PayloadModel: Purway Model II
XMP-ArchAerial:SourceCSV: methane202605061059.csv
XMP-ArchAerial:JoinMethod: FILENAME
XMP-ArchAerial:GeotaggerRunId: bf932b20-22e9-449e-a894-f03e17ee0d7b
```

Representative successful Model III embedded values:

```text
SourceFile: F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App v2\Purway Model III\20260428_015818.jpg
XMP-ArchAerial:TargetLatitude: 32.7873992
XMP-ArchAerial:TargetLongitude: -94.9414979
XMP-ArchAerial:Distance: 5.0
XMP-ArchAerial:PayloadModel: Purway Model III
XMP-ArchAerial:SourceCSV: methane20260428015755.csv
XMP-ArchAerial:JoinMethod: FILENAME
XMP-ArchAerial:GeotaggerRunId: 077ea57a-23b2-4cf1-9eb8-508089f0f09c
```

## Downstream Inspection Notes

Downstream code can inspect the successful JPGs directly and does not need the source methane CSV for WWM methane fields. The sidecar files remain useful as audit/proof artifacts and for understanding validation failures.

Recommended downstream behavior:

- Parse `XMP-ArchAerial:TargetLatitude`, `TargetLongitude`, and `Distance` from the JPG for WWM methane target data.
- Parse standard EXIF GPS as image/aircraft position, not as methane target position.
- Treat missing required XMP target/distance fields as an invalid row.
- Use `manifest.csv` only as optional audit context; successful JPGs are self-contained for the required WWM methane metadata.
- Keep `20260428_015825.jpg` as a negative fixture for missing/invalid required target-distance metadata.

## Acceptance Status

- New `XMP-ArchAerial` target/distance/provenance fields are written to processed JPGs: satisfied for successful rows.
- Sidecar manifest/import CSVs include the new fields: satisfied.
- Missing/invalid target-distance metadata is validated before EXIF writing: satisfied.
- Processed JPGs can provide WWM methane metadata without reading original methane CSVs: satisfied for successful rows.

## Remaining External Verification

The downstream `pyweb-local` WWM ingestion code is not present in this repository. This handoff verifies the producer-side JPG metadata and sidecar artifacts. The downstream repo should now verify its own parser/mapping against the sample paths listed above.
