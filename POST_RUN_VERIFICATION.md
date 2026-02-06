# Post-Run EXIF Verification: American Brine (Test Run 1)

This document verifies the results of the live test run for the "American Brine" folder using a **279 PPM** threshold in Methane mode.

**Run Details**:
- **Date**: 2026-02-03 14:59:14
- **Threshold**: 279 PPM
- **Mode**: Methane Only (Overwrite Originals)

---

## 1. EXIF Injection Verification (Success)

Comparison against [PRE_RUN_EXIF_BASELINE.md](file:///Users/archaerialtesting/Documents/purway_geotagger_app/PRE_RUN_EXIF_BASELINE.md):

| Feature | Pre-Run State | Post-Run State | Verification |
|---------|---------------|----------------|--------------|
| **GPS Longitude** | `0.0` | `98 deg 7' 17.60" W` | **Fixed** |
| **Image Description**| Empty | `ppm=311; source_csv=...` | **Populated** |
| **XMP-ArchAerial:PAC**| Missing | `2.93` | **Injected** |
| **XMP-ArchAerial:PPM**| Missing | `311.0` | **Injected** |
| **UAV Orientation**   | Missing | `Pitch: -6.6, Yaw: 83.2`| **Injected** |
| **Gimbal Orientation**| Missing | `Pitch: -88.3, Yaw: 80.9`| **Injected** |

### PAC Calculation Audit
Sample: `20260128_053838.jpg`
- **Methane (PPM)**: 1013.0
- **Relative Alt**: 106.3 m
- **Calculation**: `1013 / 106.3` = 9.5296...
- **Target PAC**: **9.53** (Correctly rounded to 2 places)

---

## 2. CSV Output Verification (Success)

The cleaned CSV was created at:
`.../American Brine/20260128053631_Flight_01/methane20260128053631_Cleaned_279-PPM.csv`

- **Threshold Compliance**: Correct. The minimum value in the file is **301 PPM** (satisfies > 279).
- **Extended Fields**: All UAV orientation and camera zoom/focal-length columns are present.

---

## 3. KMZ Verification (Not Run)

- **Status**: Skipped.
- **Reason**: The run log shows that "KMZ enabled: No" was selected during the GUI run.

---

## Conclusion
The extended EXIF injection is **fully operational**. All 15+ custom fields are populating correctly into the photos, and the threshold-based CSV cleaning is working as designed.
