# GitHub Actions CI (macOS)

This folder contains CI scripts used by the GitHub Actions workflow. The workflow file itself must live under `.github/workflows/` (GitHub requirement), but all logic is kept here to reduce repo clutter.

## Scripts
- `macos_build.sh` — creates `.venv`, installs deps, runs tests, builds the `.app`.
- `macos_package.sh` — packages the `.app` into a `.dmg`.
- `macos_sign_and_package.sh` — signs the `.app` and creates a signed `.dmg` (no notarization; only runs if secrets are provided).
- `macos_sign_and_notarize.sh` — deprecated wrapper for `macos_sign_and_package.sh` (kept for backwards compatibility).

## Secrets used by CI (optional for code signing)
- `MACOS_CERT_P12` (base64 of Developer ID Application `.p12`)
- `MACOS_CERT_PASSWORD`

## Notes
- CI prefers vendored ExifTool from `scripts/macos/vendor/Image-ExifTool-*/` and exports it for tests/builds.
- Unsigned DMG artifacts are allowed only for non-`main` builds (for ad-hoc debugging).
- Workflow secret handling uses a dedicated readiness step in `.github/workflows/macos-build.yml`:
  - `enabled=true` only when all required signing secrets are present.
  - Signing step runs only when `enabled=true`.
  - On `main`, missing signing secrets fail the job (prevents accidental unsigned release artifacts).
  - Unsigned packaging runs only when `enabled!=true` and branch is not `main`.
- For compatibility, CI sets `MACOSX_DEPLOYMENT_TARGET=13.0` by default (supports Ventura+).
- This repo currently distributes **signed but not notarized** DMGs. Gatekeeper will typically require a manual override on first launch for apps distributed outside the Mac App Store.
