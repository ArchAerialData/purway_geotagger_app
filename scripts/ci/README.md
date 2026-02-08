# GitHub Actions CI (macOS)

This folder contains CI scripts used by the GitHub Actions workflow. The workflow file itself must live under `.github/workflows/` (GitHub requirement), but all logic is kept here to reduce repo clutter.

## Scripts
- `macos_build.sh` — creates `.venv`, installs deps, runs tests, builds the `.app`.
- `macos_package.sh` — packages the `.app` into a `.dmg`.
- `macos_sign_and_notarize.sh` — signs the `.app`, creates a `.dmg`, notarizes, and staples (only runs if secrets are provided).

## Secrets used by CI (optional for signing/notarization)
- `MACOS_CERT_P12` (base64 of Developer ID Application `.p12`)
- `MACOS_CERT_PASSWORD`
- `APPLE_KEY_ID`
- `APPLE_ISSUER_ID` (required for App Store Connect **Team** API keys; CI assumes a Team key)
- `APPLE_API_KEY_P8` (base64 of App Store Connect API key `.p8`)

## Notes
- CI prefers vendored ExifTool from `scripts/macos/vendor/Image-ExifTool-*/` and exports it for tests/builds.
- Unsigned DMG artifacts are allowed only for non-`main` builds (for ad-hoc debugging).
- Workflow secret handling uses a dedicated readiness step in `.github/workflows/macos-build.yml`:
  - `enabled=true` only when all required signing secrets are present.
  - Signing/notarization step runs only when `enabled=true`.
  - On `main`, missing signing secrets fail the job (prevents accidental non-notarized release artifacts).
  - Unsigned packaging runs only when `enabled!=true` and branch is not `main`.
- For compatibility, CI sets `MACOSX_DEPLOYMENT_TARGET=13.0` by default (supports Ventura+).
- Apple requires Developer ID signing + notarization for smooth Gatekeeper behavior when distributing apps outside the Mac App Store; see `scripts/macos/APPLE_SIGNING_NOTARIZATION_SETUP.md`.
- After notarization, CI staples both `.app` and `.dmg`, then runs:
  - `spctl --assess --type execute -vv <app>`
  - `spctl --assess --type open -vv <dmg>`
  to verify Gatekeeper acceptance before artifact upload.
