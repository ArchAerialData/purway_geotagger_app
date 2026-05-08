# Methane Geotagger App Handoff

## Purpose
Provide implementation instructions for the methane JPG processing/geotagging app so this repo can consume processed Purway methane JPGs directly for WWM XLSX output and Methane Workspace features.

## Scope
- Applies to the external geotagger app that reads Purway methane CSVs and writes metadata into JPG images.
- Covers Purway Model II and Purway Model III.
- Defines required metadata tags, sidecar outputs, compatibility requirements, and validation expectations.

## Source Of Truth Files
- This repo's raw methane XLSX contract: `pyweb-local/docs/OPEN TASKS/customer_xlsx_outputs/wwm_requested_fields/source_references/ENCROACHMENT_REPORT_REPO_HANDOFF.md`
- This repo's processed image mapping plan: `pyweb-local/docs/OPEN TASKS/customer_xlsx_outputs/wwm_requested_fields/planning/METHANE_GEOTAGGED_IMAGE_MAPPING.md`
- Current Model II processed output proof: `F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App\Purway Model II\sidecar files\PurwayGeotagger_20260508_101137\manifest.csv`
- Current Model III processed output proof: `F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App\Purway Model III\sidecar_files\PurwayGeotagger_20260508_101150\manifest.csv`
- Current Model II ExifTool import proof: `F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App\Purway Model II\sidecar files\PurwayGeotagger_20260508_101137\_exiftool_import.csv`
- Current Model III ExifTool import proof: `F:\Payload Metadata List\Payload Example Data\Methane After Geotagging App\Purway Model III\sidecar_files\PurwayGeotagger_20260508_101150\_exiftool_import.csv`

## Constraints / Contracts
- Do not break existing processed JPG ingestion in this repo. Keep writing current standard EXIF GPS/time and current `XMP-ArchAerial` fields.
- Do not overload standard EXIF GPS to mean target coordinates unless explicitly coordinated later.
- Add explicit `XMP-ArchAerial` target/distance fields so WWM XLSX export can use processed JPGs without sidecar CSVs.
- Keep sidecar manifest and ExifTool import CSV outputs stable enough for test fixtures and audit.
- Use decimal-degree values for target coordinates in XMP fields.

## Required Metadata Writes
Continue writing the current fields:
- `GPSLatitude`
- `GPSLongitude`
- `GPSLatitudeRef`
- `GPSLongitudeRef`
- `GPSAltitude`
- `DateTimeOriginal`
- `ImageDescription`
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
- `XMP-dc:Description`
- `XMP-exif:GPSLatitude`
- `XMP-exif:GPSLongitude`

Add these required fields:
- `XMP-ArchAerial:TargetLongitude`: source CSV `dest_longitude`.
- `XMP-ArchAerial:TargetLatitude`: source CSV `dest_latitude`.
- `XMP-ArchAerial:Distance`: source CSV `distance`.
- `XMP-ArchAerial:Altitude`: source CSV `altitude`.
- `XMP-ArchAerial:SourceFileName`: source CSV `file_name` when present; otherwise the matched JPG filename.
- `XMP-ArchAerial:SourceCSV`: basename of the source methane CSV.
- `XMP-ArchAerial:JoinMethod`: `FILENAME`, `TIMESTAMP`, `NEAREST_TIME`, or another documented stable enum.
- `XMP-ArchAerial:JoinDeltaSeconds`: numeric delta for time-based joins; blank or `0` for exact filename joins.

Add these recommended fields:
- `XMP-ArchAerial:PayloadModel`: `Purway Model II` or `Purway Model III`.
- `XMP-ArchAerial:GeotaggerVersion`: app version or build identifier.
- `XMP-ArchAerial:GeotaggerRunId`: run ID from the run summary.
- `XMP-ArchAerial:Status`: CSV `status`.
- `XMP-ArchAerial:ErrCode`: CSV `err_code`.
- `XMP-ArchAerial:SNR`: CSV `SNR`.
- `XMP-ArchAerial:Reliability`: Model II CSV `reliability`, when present.
- `XMP-ArchAerial:FlightStatus`: Model III CSV `flight_status`, when present.
- `XMP-ArchAerial:DisCode`: Model III CSV `dis_code`, when present.
- `XMP-ArchAerial:HomeDistance`: Model III CSV `home_distance`, when present.
- `XMP-ArchAerial:Speed`: Model III CSV `speed`, when present.

## CSV Source Mapping
For both Purway Model II and III:
- `CaptureTime` from CSV `time`.
- `MethaneConcentration` from CSV `methane_concentration`.
- `TargetLongitude` from CSV `dest_longitude`.
- `TargetLatitude` from CSV `dest_latitude`.
- `Distance` from CSV `distance`.
- `Altitude` from CSV `altitude`.
- `RelativeAltitude` from CSV `relative_altitude`.
- `LightIntensity` from CSV `light_intensity`.
- `UAVPitch`, `UAVRoll`, `UAVYaw` from CSV `uav_pitch`, `uav_roll`, `uav_yaw`.
- `GimbalPitch`, `GimbalRoll`, `GimbalYaw` from CSV `gimbal_pitch`, `gimbal_roll`, `gimbal_yaw`.
- `CameraFocalLength`, `CameraZoom` from CSV `camera_focal_length`, `camera_zoom`.
- `SourceFileName` from CSV `file_name`, with matched JPG fallback.
- `SourceCSV` from source CSV basename.

For standard EXIF GPS:
- Keep current behavior unless otherwise coordinated. Based on the current processed examples, standard GPS appears to represent image/aircraft coordinates from CSV `longitude` and `latitude`.
- If the geotagger app wants to add target-position standard GPS as an option, make it opt-in and write a separate manifest flag; do not change default behavior silently.

## Sidecar Output Requirements
Keep writing:
- `manifest.csv`
- `_exiftool_import.csv`
- `run_summary.json`
- `run_config.json`
- `run_log.txt`
- backups when overwriting originals.

Add to `manifest.csv`:
- `target_lat`
- `target_lon`
- `distance`
- `source_file_name`
- `source_csv`
- `join_delta_seconds`
- `payload_model`
- `geotagger_version`
- `geotagger_run_id`
- diagnostics fields written for each payload.

Add to `_exiftool_import.csv`:
- Columns for every new `XMP-ArchAerial:*` field.
- Stable column names matching the intended ExifTool import tag names.

Add to `run_summary.json`:
- Counts for images with target coordinates written.
- Counts for images with distance written.
- Counts for rows skipped because target/distance data was blank, zero, or invalid.
- Counts by `JoinMethod`.
- The schema/version of geotagger metadata written.

## Validation Rules
- Treat blank target coordinates as invalid.
- Treat `(0, 0)` target coordinates as invalid unless an explicit debug/test mode allows them.
- Treat blank `distance` as invalid for final WWM XLSX output.
- Preserve row-level `status=SUCCESS` only when required standard fields and required new target/distance fields are written.
- If the source CSV has `file_name` blanks, match by timestamp or nearest time and record `JoinMethod` plus `JoinDeltaSeconds`.
- Do not silently substitute `relative_altitude` for `distance`.

## Acceptance Criteria
- A processed JPG can produce all WWM methane metadata fields without reading the original methane CSV.
- The same processed JPG remains compatible with current Methane Workspace photo preflight and hits processing.
- Model II and Model III both include explicit target coordinates and methane distance in `XMP-ArchAerial`.
- Manifest/import CSVs prove which values were written and how each JPG was joined to CSV data.
- The app emits warnings or failed rows when required target/distance data is unavailable.

## Tests
- Golden ExifTool JSON or CSV test for one processed Model II JPG with all required fields.
- Golden ExifTool JSON or CSV test for one processed Model III JPG with all required fields.
- Test that `TargetLongitude`, `TargetLatitude`, and `Distance` are present and equal to CSV `dest_longitude`, `dest_latitude`, and `distance`.
- Test that standard GPS remains unchanged from current default semantics.
- Test filename join and timestamp/nearest-time join behavior.
- Test manifest counts for written target/distance fields and invalid/skipped rows.

## Done When
- [ ] New `XMP-ArchAerial` target/distance/provenance fields are written to processed JPGs.
- [ ] Sidecar manifest/import CSVs include the new fields.
- [ ] The app validates missing/invalid target and distance data.
- [ ] This repo can parse processed JPGs without sidecar CSVs for WWM XLSX rows.

## Risks / Open Questions
- Confirm the exact geotagger app version field name.
- Confirm whether standard EXIF GPS should stay aircraft/image position permanently or become configurable.
- Confirm whether source CSV `altitude` should always be mirrored to both `GPSAltitude` and `XMP-ArchAerial:Altitude`.

## Agent Completion Notes
- 2026-05-08: Added external handoff instructions for updating the methane geotagger app to support WWM XLSX processed-JPG output.
