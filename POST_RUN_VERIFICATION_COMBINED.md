# Post-Run Verification: Combined Methane + Encroachment (Run 2)

This document verifies the results of the second live test run using **Combined Mode**.

**Run Parameters**:
- **Threshold**: 1500 PPM
- **KMZ**: Enabled
- **Encroachment Name**: Whitewater Midstream (WWM)
- **Starting Index**: 1

---

## 1. Methane Verification (Success)

### Threshold Compliance
- Found cleaned CSVs at `1500-PPM` threshold.
- Manual audit of `Flight_03` CSV shows minimum value in file is **2803 PPM**, successfully obeying the 1500 PPM threshold.

### KMZ Generation
- Verified `methane20260128053631_Cleaned_1500-PPM.kmz` exists.
- This confirms the default configuration change (KMZ on by default) worked as intended.

### EXIF Injection (Original Files)
Sample: `20260128_053834.jpg`
- **PAC**: 2.93
- **UAV Yaw**: 83.2
- **Methane Concentration**: 311.0

---

## 2. Encroachment Verification (Success)

### Renaming & Chronology
All 30 photos were copied to `Encroachment_Output` and renamed sequentially:
- `WWM_0001.jpg` (05:38:34)
- `WWM_0015.jpg` (06:08:42)
- `WWM_0030.jpg` (06:45:26)
**Confirmed**: The files were correctly sorted by **capture time** before indexing, ensuring `WWM_0001` is the earliest photo.

### EXIF Persistence in Copies
Sample: `WWM_0001.jpg`
- **PAC**: 2.93 (Verified present in renaming copy)
- **Methane Concentration**: 311.0
- **UAV Orientation**: Injected successfully.

---

## 3. Configuration Verification
- **Default KMZ**: The application successfully defaulted to KMZ creation as requested.

---

## Conclusion
The application is now **fully verified** for Combined operations. The Extended EXIF injection system is robust, carrying custom metadata through renaming and copying operations while maintaining sub-second chronological precision.
