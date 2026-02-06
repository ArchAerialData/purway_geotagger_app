# Pre-Run EXIF Documentation: American Brine (RESET for Run 2)

This document records the initial EXIF/XMP metadata state of photos in the `American Brine` test folder after being reset to their original state.

**Source Path**: `/Users/archaerialtesting/Documents/purway_geotagger_app/raw_data/test_copies/American Brine/20260128053631_Flight_01/`

---

## Baseline Summary (RESET State)

The following metadata was extracted from a sample of 2 photos in the target directory to confirm the reset.

### Sample Photo 1: `20260128_053834.jpg`
| Tag | Current Value | Status |
|-----|---------------|--------|
| **GPS Latitude** | 27 deg 43' 17.87" N | Present |
| **GPS Longitude** | 0 deg 0' 0.00" E | **Placeholder (Zeroed)** |
| **GPS Altitude** | 54.1 m | Present |
| **Image Description** | (None) | Missing |
| **XMP-ArchAerial:PAC** | (None) | Missing |
| **XMP-ArchAerial:MethaneConcentration** | (None) | Missing |
| **XMP-ArchAerial:RelativeAltitude** | (None) | Missing |
| **UAV/Gimbal Orientation** | (None) | Missing |

### Sample Photo 2: `20260128_053838.jpg`
| Tag | Current Value | Status |
|-----|---------------|--------|
| **GPS Latitude** | 27 deg 43' 17.99" N | Present |
| **GPS Longitude** | 0 deg 0' 0.00" E | **Placeholder (Zeroed)** |
| **GPS Altitude** | 54.3 m | Present |
| **Image Description** | (None) | Missing |
| **XMP-ArchAerial:PAC** | (None) | Missing |
| **XMP-ArchAerial:MethaneConcentration** | (None) | Missing |

---

## Conclusion
The photos have been successfully reset. They currently lack any methane-specific metadata and contain placeholder longitude.

**Ready for Test Run 2 (Combined Mode)**:
- **Default KMZ**: Enabled (via config update)
- **Mode**: Combined (Methane + Encroachment)
- **Goal**: Verify Methane EXIF injection, Encroachment copy EXIF injection, and KMZ generation.
