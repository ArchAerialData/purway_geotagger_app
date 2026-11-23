# Windows ExifTool dependency

This unmodified official 64-bit ExifTool 13.50 ZIP is vendored so builds do not depend on mutable upstream mirrors. It is the archive previously downloaded and used for the tested local Windows builds. SHA-256 and upstream provenance are recorded in `exiftool.json`.

`stage_exiftool.ps1` checks that hash before extracting, then verifies the staged executable reports exactly 13.50 before replacing a previous stage. The archive retains its README and bundled licenses; `exiftool_files` (including license material) is distributed intact with the app.

For updates, obtain an official archive from https://exiftool.org/, verify provenance and runtime version, replace the archive and manifest together, update workflow/build pins, and run metadata integration tests. Never silently substitute another release after a validation failure.
