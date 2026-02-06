# Extended EXIF Injection Implementation Plan

## Overview

Extend the Purway Geotagger EXIF injection system to embed additional methane CSV fields and derived values (PAC) into photo metadata. These custom fields can be read downstream by external report generation applications.

---

## Open Questions

> [!IMPORTANT]
> **The following questions require clarification before implementation:**

1. **XMP Namespace**: Should custom fields use a dedicated XMP namespace (e.g., `XMP-ArchAerial:` or `XMP-Purway:`) for downstream compatibility? Or should they be stored in `UserComment` / `ImageDescription` as serialized key-value pairs?

2. **Column Name Variations**: The CSV columns you listed may have variations in actual files. Please confirm exact column headers or common alternatives for:
   - `light_intensity` (e.g., `lux`, `light`, `brightness`?)
   - `gimbal_pitch/roll/yaw` (e.g., `gimbal.pitch`, `gimbal_p`?)
   - `camera_focal_length` (e.g., `focal_length`, `lens_focal`?)
   - `camera_zoom` (e.g., `zoom_level`, `digital_zoom`?)

3. **PAC Precision**: What decimal precision should the PAC value have? (e.g., 2 decimal places → `125.67`)

4. **Optional Fields Handling**: If a CSV is missing some columns (e.g., no `gimbal_yaw`), should we:
   - (A) Skip that field silently?
   - (B) Write an empty/null value?
   - (C) Show a warning in the UI?

5. **Backwards Compatibility**: Should the existing `ImageDescription` format (`ppm=123; source_csv=file.csv`) be preserved, extended, or replaced?

---

## Target Fields

### From CSV (Direct Injection)

| Field | EXIF/XMP Tag | Notes |
|-------|--------------|-------|
| `time` | `XMP-ArchAerial:CaptureTime` | UTC timestamp from CSV |
| `methane_concentration` | `XMP-ArchAerial:MethaneConcentration` | PPM value |
| `light_intensity` | `XMP-ArchAerial:LightIntensity` | Lux or sensor value |
| `longitude` | Already injected | GPS EXIF tag |
| `latitude` | Already injected | GPS EXIF tag |
| `altitude` | `GPSAltitude` | Standard EXIF GPS altitude |
| `relative_altitude` | `XMP-ArchAerial:RelativeAltitude` | AGL altitude |
| `uav_pitch` | `XMP-ArchAerial:UAVPitch` | Degrees |
| `uav_roll` | `XMP-ArchAerial:UAVRoll` | Degrees |
| `uav_yaw` | `XMP-ArchAerial:UAVYaw` | Degrees |
| `gimbal_pitch` | `XMP-ArchAerial:GimbalPitch` | Degrees |
| `gimbal_roll` | `XMP-ArchAerial:GimbalRoll` | Degrees |
| `gimbal_yaw` | `XMP-ArchAerial:GimbalYaw` | Degrees |
| `camera_focal_length` | `FocalLength` | Standard EXIF tag (mm) |
| `camera_zoom` | `DigitalZoomRatio` | Standard EXIF tag |

### Derived Fields (Calculated)

| Field | EXIF/XMP Tag | Formula |
|-------|--------------|---------|
| `pac` (Path Average Concentration) | `XMP-ArchAerial:PAC` | `methane_concentration / relative_altitude` |

---

## Phase 1: Data Model Extension

### Objective
Extend `PhotoTask` and `PurwayRecord` dataclasses to carry additional CSV fields.

### Files to Modify

#### [MODIFY] [photo_task.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/core/photo_task.py)

Add new optional fields to `PhotoTask`:

```python
# New fields to add after existing ones:
altitude: float | None = None
relative_altitude: float | None = None
light_intensity: float | None = None
uav_pitch: float | None = None
uav_roll: float | None = None
uav_yaw: float | None = None
gimbal_pitch: float | None = None
gimbal_roll: float | None = None
gimbal_yaw: float | None = None
camera_focal_length: float | None = None
camera_zoom: float | None = None
timestamp_raw: str | None = None  # Original CSV timestamp string
pac: float | None = None  # Derived: methane_concentration / relative_altitude
```

---

#### [MODIFY] [purway_csv.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/parsers/purway_csv.py)

1. Add new column candidate lists:
```python
ALT_COL_CANDIDATES = ["altitude", "alt", "gpsaltitude"]
REL_ALT_COL_CANDIDATES = ["relative_altitude", "rel_alt", "agl", "height_agl"]
LIGHT_COL_CANDIDATES = ["light_intensity", "light", "lux", "brightness"]
UAV_PITCH_CANDIDATES = ["uav_pitch", "uav.pitch", "pitch"]
UAV_ROLL_CANDIDATES = ["uav_roll", "uav.roll", "roll"]
UAV_YAW_CANDIDATES = ["uav_yaw", "uav.yaw", "yaw", "heading"]
GIMBAL_PITCH_CANDIDATES = ["gimbal_pitch", "gimbal.pitch", "cam_pitch"]
GIMBAL_ROLL_CANDIDATES = ["gimbal_roll", "gimbal.roll", "cam_roll"]
GIMBAL_YAW_CANDIDATES = ["gimbal_yaw", "gimbal.yaw", "cam_yaw"]
FOCAL_LENGTH_CANDIDATES = ["camera_focal_length", "focal_length", "focal", "lens_focal"]
ZOOM_CANDIDATES = ["camera_zoom", "zoom", "digital_zoom", "zoom_ratio"]
```

2. Extend `PurwayRecord` dataclass with new fields.

3. Update `_parse_single_csv()` to extract new columns.

4. Update `PhotoMatch` and `_to_match()` to carry new fields.

---

### Verification Gate

```bash
# Run unit tests for CSV parsing
python -m pytest tests/test_purway_csv.py -v

# Manual check: Inspect a sample CSV and confirm all columns are detected
python -c "from purway_geotagger.parsers.purway_csv import inspect_csv_schema; from pathlib import Path; print(inspect_csv_schema(Path('path/to/sample.csv')))"
```

---

## Phase 2: PAC Calculation

### Objective
Implement PAC (Path Average Concentration) derivation and attach to `PhotoTask`.

### Files to Modify

#### [NEW] [pac_calculator.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/core/pac_calculator.py)

Create a utility module for PAC calculation:

```python
def calculate_pac(methane_concentration: float | None, relative_altitude: float | None) -> float | None:
    """
    Calculate Path Average Concentration.
    
    PAC = methane_concentration / relative_altitude
    
    Returns None if inputs are invalid (None, zero altitude, negative values).
    """
    if methane_concentration is None or relative_altitude is None:
        return None
    if relative_altitude <= 0:
        return None  # Avoid division by zero
    return round(methane_concentration / relative_altitude, 2)
```

---

#### [MODIFY] [purway_csv.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/parsers/purway_csv.py)

Import and call `calculate_pac()` in `_to_match()`:

```python
from purway_geotagger.core.pac_calculator import calculate_pac

def _to_match(r: PurwayRecord, join_method: str) -> PhotoMatch:
    # ... existing code ...
    pac = calculate_pac(r.ppm, r.relative_altitude)
    # ... add pac to PhotoMatch ...
```

---

### Verification Gate

```bash
# Run unit tests for PAC calculation
python -m pytest tests/test_pac_calculator.py -v
```

#### Test Cases to Implement

| Input | Expected Output |
|-------|-----------------|
| `ppm=500, rel_alt=10` | `50.0` |
| `ppm=1000, rel_alt=25` | `40.0` |
| `ppm=None, rel_alt=10` | `None` |
| `ppm=500, rel_alt=0` | `None` |
| `ppm=500, rel_alt=-5` | `None` |

---

## Phase 3: EXIF Writer Extension

### Objective
Update the ExifTool CSV export to include all new fields.

### Files to Modify

#### [MODIFY] [exiftool_writer.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/exif/exiftool_writer.py)

1. Update `_write_import_csv()` to include new CSV columns:

```python
fields = [
    "SourceFile",
    # Existing GPS fields
    "GPSLatitude", "GPSLongitude", "GPSLatitudeRef", "GPSLongitudeRef",
    "GPSAltitude",  # NEW
    "DateTimeOriginal",
    "ImageDescription",
    "FocalLength",  # NEW
    "DigitalZoomRatio",  # NEW
]

# XMP custom namespace fields (requires ExifTool config or UserComment approach)
xmp_fields = [
    "XMP-ArchAerial:MethaneConcentration",
    "XMP-ArchAerial:PAC",
    "XMP-ArchAerial:RelativeAltitude",
    "XMP-ArchAerial:LightIntensity",
    "XMP-ArchAerial:UAVPitch",
    "XMP-ArchAerial:UAVRoll",
    "XMP-ArchAerial:UAVYaw",
    "XMP-ArchAerial:GimbalPitch",
    "XMP-ArchAerial:GimbalRoll",
    "XMP-ArchAerial:GimbalYaw",
    "XMP-ArchAerial:CaptureTime",
]
```

2. Update row generation to populate new values from `PhotoTask`.

3. Handle `None` values gracefully (write empty string or skip).

---

#### [NEW] [exiftool_config.txt](file:///Users/archaerialtesting/Documents/purway_geotagger_app/config/exiftool_config.txt)

Create an ExifTool configuration file to define the custom XMP namespace:

```perl
%Image::ExifTool::UserDefined = (
    'Image::ExifTool::XMP::Main' => {
        ArchAerial => {
            SubDirectory => {
                TagTable => 'Image::ExifTool::UserDefined::ArchAerial',
            },
        },
    },
);

%Image::ExifTool::UserDefined::ArchAerial = (
    GROUPS => { 0 => 'XMP', 1 => 'XMP-ArchAerial', 2 => 'Other' },
    NAMESPACE => { 'ArchAerial' => 'http://ns.archaerial.com/1.0/' },
    WRITABLE => 'string',
    MethaneConcentration => { Writable => 'real' },
    PAC => { Writable => 'real' },
    RelativeAltitude => { Writable => 'real' },
    LightIntensity => { Writable => 'real' },
    UAVPitch => { Writable => 'real' },
    UAVRoll => { Writable => 'real' },
    UAVYaw => { Writable => 'real' },
    GimbalPitch => { Writable => 'real' },
    GimbalRoll => { Writable => 'real' },
    GimbalYaw => { Writable => 'real' },
    CaptureTime => { Writable => 'string' },
);

1; # End of config
```

---

#### [MODIFY] [exiftool_writer.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/exif/exiftool_writer.py)

Update ExifTool command to use the config file:

```python
config_path = resource_path("config/exiftool_config.txt")
cmd = [
    self.exiftool_path,
    f"-config={config_path}",  # Load custom namespace
    "-overwrite_original",
    f"-csv={import_csv}",
    *files,
]
```

---

#### [MODIFY] [build_app.sh](file:///Users/archaerialtesting/Documents/purway_geotagger_app/scripts/macos/build_app.sh)

Add the ExifTool config to the PyInstaller bundle:

```bash
--add-data "config/exiftool_config.txt:config"
```

---

### Verification Gate

```bash
# Run integration test with a sample photo
python -m pytest tests/test_exif_extended.py -v

# Manual verification: Read back XMP tags from a processed photo
exiftool -XMP-ArchAerial:all /path/to/processed_photo.jpg
```

#### Expected Output

```
Methane Concentration       : 1234.5
PAC                         : 49.38
Relative Altitude           : 25.0
UAV Pitch                   : -15.2
...
```

---

## Phase 4: Pipeline Integration

### Objective
Ensure the job runner propagates all new fields through the processing pipeline.

### Files to Modify

#### [MODIFY] [job_runner.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/ops/job_runner.py)

Update task population to copy new fields from `PhotoMatch` to `PhotoTask`:

```python
# In _apply_match() or equivalent:
task.altitude = match.altitude
task.relative_altitude = match.relative_altitude
task.light_intensity = match.light_intensity
task.uav_pitch = match.uav_pitch
# ... etc ...
task.pac = match.pac
```

---

### Verification Gate

```bash
# Run full pipeline test
python -m pytest tests/test_job_runner.py -v

# Functional test: Process a folder and verify manifest.csv contains new columns
```

---

## Phase 5: UI Visibility (Optional)

### Objective
Surface the new fields in the app UI for transparency.

### Files to Modify

#### [MODIFY] [home_page.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/gui/pages/home_page.py)

Update the System Status card or add a "Detected CSV Columns" section that shows which extended fields were found in the input data.

---

#### [MODIFY] [help_page.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/src/purway_geotagger/gui/pages/help_page.py)

Add documentation explaining the new EXIF fields:

```markdown
### Extended Metadata Injection

When processing methane reports, the following fields are automatically 
embedded into your photos:

- **GPS Coordinates**: Standard EXIF GPS tags
- **PAC (Path Average Concentration)**: Calculated as `PPM / Altitude`
- **UAV Orientation**: Pitch, Roll, Yaw of the drone
- **Gimbal Orientation**: Camera orientation
- **And more...**
```

---

### Verification Gate

```bash
# Launch GUI and visually inspect Help page
./scripts/macos/run_gui.sh
```

---

## Phase 6: Testing & Documentation

### Objective
Comprehensive test coverage and user documentation.

### Files to Create

#### [NEW] [tests/test_pac_calculator.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/tests/test_pac_calculator.py)

Unit tests for PAC calculation.

---

#### [NEW] [tests/test_exif_extended.py](file:///Users/archaerialtesting/Documents/purway_geotagger_app/tests/test_exif_extended.py)

Integration tests for extended EXIF writing and reading.

---

#### [MODIFY] [README.md](file:///Users/archaerialtesting/Documents/purway_geotagger_app/README.md)

Document the new extended metadata features.

---

### Verification Gate

```bash
# Full test suite
python -m pytest tests/ -v

# Coverage check
python -m pytest tests/ --cov=purway_geotagger --cov-report=term-missing
```

---

## Performance Considerations

> [!NOTE]
> The following ensures no performance degradation:

1. **CSV Parsing**: Additional column extraction is O(1) per row—negligible overhead.

2. **ExifTool Batch Mode**: All photos are still written in a single ExifTool invocation via CSV import—no change to batch efficiency.

3. **Memory**: Additional fields add ~100 bytes per `PhotoTask`—negligible for typical job sizes (hundreds to low thousands of photos).

4. **PAC Calculation**: Simple arithmetic, computed once per matched photo—O(1).

---

## Summary Checklist

- [x] Phase 1: Extend `PhotoTask` and `PurwayRecord` dataclasses
- [x] Phase 2: Implement PAC calculation utility
- [x] Phase 3: Extend ExifTool writer with custom XMP namespace
- [x] Phase 4: Update job runner to propagate new fields
- [x] Phase 5: Add UI visibility (optional)
- [x] Phase 6: Add tests and documentation

---

## File Summary

| Action | File Path |
|--------|-----------|
| MODIFY | `src/purway_geotagger/core/photo_task.py` |
| MODIFY | `src/purway_geotagger/parsers/purway_csv.py` |
| NEW | `src/purway_geotagger/core/pac_calculator.py` |
| MODIFY | `src/purway_geotagger/exif/exiftool_writer.py` |
| NEW | `config/exiftool_config.txt` |
| MODIFY | `scripts/macos/build_app.sh` |
| MODIFY | `src/purway_geotagger/ops/job_runner.py` |
| MODIFY | `src/purway_geotagger/gui/pages/home_page.py` (optional) |
| MODIFY | `src/purway_geotagger/gui/pages/help_page.py` (optional) |
| NEW | `tests/test_pac_calculator.py` |
| NEW | `tests/test_exif_extended.py` |
| MODIFY | `README.md` |
