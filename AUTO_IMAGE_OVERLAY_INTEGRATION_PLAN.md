# Auto Image Overlay Integration Plan

## Purpose
Integrate the standalone **Auto Image Overlay** tool into Purway Geotagger as a new GUI tab while preserving macOS compatibility, existing UI styling, and repo organization rules. The goal is to generate **KMZ overlays** and/or **GeoTIFFs** from JPG EXIF/XMP metadata directly inside this app, producing **one KMZ and one TIF per JPG** with outputs organized into separate **KMZs** and **TIFs** folders per run.

## Source Context (Current State)
- New folder added: `auto_image_overlay/` (currently at repo root).
- It is a self-contained Python package with a CLI (`python -m auto_image_overlay`).
- Core outputs:
  - **KMZ** overlays: either **superoverlay (tiled)** via GDAL or **quad overlay** (single image).
  - **GeoTIFF** (COG or GTiff) via GDAL.
- Required tags (from ExifTool JSON):
  - `GPSLatitude`, `GPSLongitude`
  - `RelativeAltitude`
  - `GimbalYawDegree`, `GimbalPitchDegree`, `GimbalRollDegree`
  - `ImageWidth`, `ImageHeight`
  - `CalibratedFocalLength`, `CalibratedOpticalCenterX`, `CalibratedOpticalCenterY`
- Dependencies (per README + code):
  - **exiftool** on PATH
  - **GDAL / osgeo** (for superoverlay + GeoTIFF)
  - **pyproj** (camera math + CRS transforms)
  - **Pillow** (quad KMZ image embed)
- The current app’s `PYTHONPATH` only includes `src/`. The new folder is **not importable** yet from the GUI.
- `auto_image_overlay/` currently contains its own `.git` folder (nested repo).
- **Injected JPGs check (current test copies)**: injected photos contain ArchAerial XMP tags (e.g. `XMP-ArchAerial:GimbalYaw/GimbalPitch/GimbalRoll`, `XMP-ArchAerial:RelativeAltitude`) and GPS, but **do not** include DJI calibrated tags (`CalibratedFocalLength`, `CalibratedOpticalCenterX/Y`). This means the overlay tool **cannot run as-is** on injected JPGs without a metadata adapter or camera calibration fallback.
- **Raw backup JPG sample** (un‑injected) shows **no DJI XMP calibration tags** and **no DJI gimbal tags**; only basic EXIF such as `FocalLength` (mm) and GPS. This reinforces the need for camera profiles + CSV/external orientation inputs for overlays.
- **Purway Model III zoom** is listed as **16× Digital Zoom** in product specs (not optical). This means zoom should be treated as a **crop-based effective focal multiplier** rather than a true lens change. citeturn0search0

## macOS Compatibility & Packaging Risks
1. **GDAL/osgeo is native**
   - Requires compiled binaries + PROJ data files.
   - PyInstaller bundling is non-trivial (must include GDAL + PROJ + data).
   - Homebrew GDAL path is not guaranteed in `.app` environment.

2. **pyproj relies on PROJ data**
   - Needs `PROJ_LIB` / data directory set or bundled in app.

3. **ExifTool is currently resolved via PATH in auto_image_overlay**
   - This conflicts with macOS `.app` PATH expectations.
   - The main app already bundles ExifTool via `resource_path`.

4. **Nested .git in auto_image_overlay**
   - Can cause confusion in tooling and packaging; should be removed or converted to a vendored subpackage.

## Integration Strategy (High-Level)
- **Vendor the overlay package under `src/purway_geotagger/`** so it is importable and packaged.
- **Expose a programmatic API** (not just CLI) for GUI use.
- **Reuse existing ExifTool resolver** so the overlay tool uses the app-bundled ExifTool.
- **Add feature gating** to handle missing GDAL gracefully:
  - If GDAL is missing, allow **Quad KMZ only**.
  - If GDAL is present, allow **Superoverlay KMZ** and **GeoTIFF**.
- **Create a dedicated GUI tab** with matching styles, progress reporting, logs, and outputs.
- **Outputs**: Always write one KMZ/TIF per JPG into two sibling folders under the selected output root: `KMZs/` and `TIFs/` (create only the folders for enabled outputs).

## Open Questions (Updated)
1. **Output behavior (answered)**: One KMZ/TIF per JPG, with outputs grouped into `KMZs/` and `TIFs/` folders under the selected output root.
2. **Feature availability (answered)**: **Full GDAL support is required** (Superoverlay + GeoTIFF). Quad KMZ-only is still kept as a fallback mode when GDAL is unavailable, but the target deployment includes GDAL.
3. **Jobs integration (answered)**: Overlay runs **should appear in Jobs** so logs and output folders are easy to access.
4. **Input assumptions (answered, with action needed)**: Inputs will be a **mix** of DJI photos and **injected JPGs** produced by this app. Current injected JPGs **lack DJI calibrated tags**, so we need a metadata adapter or camera calibration fallback to support overlays from injected files.
5. **Default output location (answered)**: Default to a sibling folder like `Overlay_Output` and logs in `Overlay_RunLogs`, but allow user override. GUI should clearly state it will create separate `KMZs/` and `TIFs/` subfolders.
6. **Camera calibration fallback (answered)**: Use **fixed camera profiles** (per model) with **manual override** for focal length / optical center when EXIF calibration is missing. If EXIF calibration is present, use it automatically.
7. **Vendor calibration + CSV clarifications (pending)**: Email sent to Purway requesting camera intrinsics, distortion, sensor size, zoom type confirmation, and CSV/telemetry definitions. Awaiting reply.

## Vendor Reply Status (Pending)
**Request sent to Purway (awaiting response):**
- Camera intrinsics: `fx`, `fy`, `cx`, `cy`
- Lens distortion: `k1`, `k2`, `k3`, `p1`, `p2`
- Sensor size + resolution; camera module / lens model
- Zoom type confirmation (digital vs optical)
- CSV timestamp format + timezone and clock sync confirmation
- `relative_altitude` reference + units
- `altitude` reference (MSL/ellipsoid/geoid)
- Sign conventions for `uav_*` and `gimbal_*` angles
- Definition/units for `camera_focal_length` and `camera_zoom`
- Any edge cases for `file_name` mapping
- Definitions for `status`, `err_code`, `flight_status`, `dis_code`

## Next Actions Upon Vendor Reply
1. Add the provided camera intrinsics + distortion into a **camera profile** JSON under `src/purway_geotagger/overlay/profiles/`.
2. Update the Overlay tab defaults to the new CH‑4 Model III profile.
3. If zoom is confirmed digital, keep the **effective focal multiplier** behavior; if optical, apply zoom as true focal change.
4. Update CSV parsing if Purway confirms different units / sign conventions.
5. Re-run a small overlay test set and document results in the Phase Notes.

## Option Differences (Quality & Accuracy)
### 1) Quad KMZ (no GDAL required)
- **How it works**: Builds a single ground quad using the four image corners computed from camera model. Writes a single KMZ per JPG with the image embedded.
- **Accuracy**: Lowest of the options. Assumes perfectly flat ground and uses a simple planar projection. If the camera is tilted or terrain varies, the overlay can be visibly offset or warped.
- **Image quality**: No tiling; preserves original JPG resolution. Quick to generate and lightweight.
- **Best for**: Quick visualization, when GDAL is unavailable, or when precision is less critical.

### 2) Superoverlay KMZ (GDAL required)
- **How it works**: Orthorectifies the image (using GCP grid + warp) and outputs a tiled KMZ (KMLSUPEROVERLAY). Tiles are generated at multiple zoom levels.
- **Accuracy**: Better than Quad KMZ. Still assumes flat ground but handles camera tilt more robustly by warping the image to a projected plane.
- **Image quality**: Multi-resolution tiles; may resample based on GDAL settings (nearest/bilinear/cubic). Good for large images and smooth zooming in Google Earth.
- **Best for**: Production overlays in Google Earth when GDAL is available.

### 3) GeoTIFF (GDAL required)
- **How it works**: Orthorectifies to a projected CRS and writes a georeferenced raster (COG or GTiff).
- **Accuracy**: Similar or slightly better than superoverlay (same ortho pipeline). Best option for GIS workflows.
- **Image quality**: Configurable compression and resampling; ideal for QGIS/ArcGIS workflows. Produces stable georeferencing.
- **Best for**: GIS analysis or when you want a georeferenced raster file.

## Camera Intrinsics Needed (For Accurate Overlays)
These are the **minimum camera intrinsics** required to compute accurate overlays. The current overlay math expects these values (or derives them from EXIF if present):
1. **Image width/height (pixels)** — must match the JPG dimensions.
2. **Focal length (pixels)** — `f_px`. If only `f_mm` + sensor size are known, compute `f_px`.
3. **Principal point (cx, cy in pixels)** — optical center. Defaults to image center if unknown, but accuracy drops.
4. **Lens distortion (k1, k2, k3, p1, p2)** — **highly recommended** for best accuracy, but the current pipeline **does not correct distortion**. If distortion is significant, overlays will warp.
5. **Skew / pixel aspect ratio** — usually 0 / 1.0; only needed if pixels are not square.

Additionally required **per photo** (extrinsics):
- GPS latitude/longitude
- Relative altitude (AGL) — use `XMP-ArchAerial:RelativeAltitude` from injected JPGs. Treat `0` or missing as **invalid** and require fallback or user confirmation.
- Gimbal yaw/pitch/roll (camera orientation)

## Purway CH‑4 / Model III Camera Data (What We Found)
Public specs for the Purway CH‑4 / Model III list **video resolution** and **camera megapixels**, but **do not publish lens/sensor intrinsics** (focal length, sensor size, principal point). Specifically:
- CH‑4 page lists **FHD 1920×1080 (30p)** video and gimbal stabilization (yaw/pitch/roll). citeturn0search0
- Model II/III pages list **48MP camera**, **4K 30fps**, **16× digital zoom**, and DJI Xport gimbal. citeturn0search1turn0search3turn0search4

**Missing critical data** (not found in public specs): sensor size, focal length, optical center, distortion model. Without these, we cannot compute accurate intrinsics for injected JPGs.

### Action Needed (to finalize camera profiles)
1. **Collect a raw CH‑4 JPG** from the payload (not just injected output).  
2. Run `exiftool` on that file to check for focal length, calibration, or sensor metadata.  
3. If EXIF does **not** include calibration, request the camera module model / calibration sheet from the manufacturer.  
4. Once obtained, store as a **camera profile** in the Overlay tab (with manual override fallback).

---

## Phased Implementation Plan

### Phase 1 — Ingestion & Package Placement
**Goal:** Make the overlay code importable and aligned with repo structure.

**Tasks**
- Move or copy `auto_image_overlay/` into `src/purway_geotagger/overlay/`.
  - Files to place under: `src/purway_geotagger/overlay/`
  - Ensure `__init__.py` is present.
- Remove the nested `.git` folder from the vendored copy.
- Update internal imports if necessary after relocation.
- Create `src/purway_geotagger/overlay/api.py` to expose a clean function entrypoint (no CLI parsing).

**Tests / Verification**
- `python -c "from purway_geotagger.overlay import api"` succeeds.
- `python -m purway_geotagger.app` still launches.

**Phase Notes**
- After completing Phase 1, update this file with: date, tests run, and deviations.

---

### Phase 2 — Dependency Gating & Mac Compatibility
**Goal:** Detect missing dependencies and avoid crashes; keep app usable without GDAL.

**Tasks**
- Add `src/purway_geotagger/overlay/deps.py`:
  - `has_gdal()`, `has_pyproj()`, `has_pillow()` helpers.
  - Return feature flags: `supports_quad`, `supports_superoverlay`, `supports_geotiff`.
- Update `requirements.txt` (and `scripts/macos/setup_macos.sh`) to include:
  - `Pillow`, `pyproj`
  - `gdal` (required for full mode).
- Update `PurwayGeotagger.spec`:
  - Bundle GDAL/PROJ libs and data (required).
  - Add runtime environment setup for `GDAL_DATA` and `PROJ_LIB` pointing to bundled data.

**Tests / Verification**
- Unit test: import `overlay.deps` and verify feature flags in current environment.
- App still launches without GDAL installed; overlay tab should show limited options.

**Phase Notes**
- Record whether GDAL is included or optional.

---

### Phase 3 — Overlay Pipeline API + Logging
**Goal:** Provide a non-CLI pipeline with progress callbacks and run logs.

**Tasks**
- Add `src/purway_geotagger/overlay/pipeline.py`:
  - `run_overlay_job(inputs, output_dir, options, progress_cb, cancel_cb) -> OverlayRunResult`.
  - Validate required EXIF/XMP tags (fail per-file, not entire run).
  - Support quad KMZ, superoverlay KMZ, GeoTIFF based on feature flags.
- Add a metadata adapter in `src/purway_geotagger/overlay/exif_reader.py`:
  - Map **DJI tags** when present.
  - Map **ArchAerial tags** for injected JPGs (GimbalYaw/Pitch/Roll, RelativeAltitude).
  - If calibrated focal length / optical center are missing, use **camera profile** defaults (per model) or **manual override** values and flag missing values in UI before run.
  - Validate `RelativeAltitude` >= **minimum safe AGL**; if below threshold or missing, mark as **ineligible** for overlay output.
- Use the existing app ExifTool resolver instead of PATH:
  - Add `src/purway_geotagger/overlay/exif_reader.py` that uses `resource_path` or `ExifToolWriter` path logic.
- Create run logs:
  - `run_log.txt`, `run_config.json`, and `run_summary.json` in a run folder.
  - Default log folder suggestion: `Overlay_RunLogs` next to output folder.
- Output organization:
  - Write KMZs to `<output_root>/KMZs/`
  - Write TIFs to `<output_root>/TIFs/`
  - Create only the folders for enabled outputs.

**Tests / Verification**
- Unit test for EXIF parsing with mocked JSON.
- Manual run using 1–2 DJI JPGs to verify KMZ output and run logs.

---

### Phase 4 — GUI Tab Integration
**Goal:** Add a new GUI tab that uses the overlay pipeline and theme styles.

**Tasks**
- Add new nav tab in `src/purway_geotagger/gui/main_window.py`:
  - New button: **Overlay** (or **Image Overlay**).
  - New page class: `src/purway_geotagger/gui/pages/overlay_page.py`.
- Build UI with existing styles:
  - Inputs: drag+drop + file/folder buttons (reuse `DropZone`).
  - Output format toggles: KMZ, GeoTIFF.
  - Mode selection: Superoverlay vs Quad (disable if GDAL missing).
  - Output folder selection + default path.
  - Explicit copy text: outputs go into `KMZs/` and `TIFs/` subfolders under the chosen output root.
  - **Camera profile** selector (default: Auto from EXIF, fallback to chosen profile).
  - **Manual override** fields (focal length px, cx/cy) shown only when EXIF is missing and profile is not selected.
  - **Minimum AGL threshold** (default value set by app) with helper text.
  - **Pre‑run eligibility popup**: “X/Y photos qualify for accurate overlays (AGL ≥ threshold + required tags). Proceed?”\n    - Include counts for **ineligible** photos in the run summary and logs.
  - Offset east/north inputs.
  - Progress bar + status text.
  - Run + Cancel buttons.
- Use the global progress bar and update it for overlay runs.
- Reuse `RunReportDialog` to show overlay run summary/logs.

**Tests / Verification**
- GUI opens, tab switches properly, no theme regression.
- Run overlay on a small dataset and confirm output + logs.

---

### Phase 5 — Jobs/Report Integration (Confirmed)
**Goal:** Overlay runs appear in the **Jobs** tab for log and output access.

**Tasks**
- Extend job model to include Overlay runs (new `RunMode.OVERLAY`).
- Update `JobController`, `JobTableModel`, and `run_summary` handling.
- Ensure “View run report” works for overlay jobs.

**Tests / Verification**
- Run overlay job and confirm it appears in Jobs with report view + output folder buttons enabled.
 - Verify run summary includes: total photos scanned, eligible photos processed, ineligible photos skipped (below AGL / missing tags).

---

## Summary of Required File/Folder Paths
**New Modules**
- `src/purway_geotagger/overlay/` (vendored auto_image_overlay package)
- `src/purway_geotagger/overlay/api.py`
- `src/purway_geotagger/overlay/pipeline.py`
- `src/purway_geotagger/overlay/deps.py`
- `src/purway_geotagger/overlay/exif_reader.py`

**GUI**
- `src/purway_geotagger/gui/pages/overlay_page.py`
- `src/purway_geotagger/gui/main_window.py` (add nav button + page)

**Packaging / Setup**
- `requirements.txt`
- `scripts/macos/setup_macos.sh`
- `PurwayGeotagger.spec`

---

## Notes for Phase Discipline
- Do not begin a new phase until all tasks and verification steps in the current phase are completed.
- After each phase, update this markdown file with:
  - date
  - tests run
  - deviations / issues
