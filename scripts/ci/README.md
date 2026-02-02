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
- `APPLE_ISSUER_ID`
- `APPLE_API_KEY_P8` (base64 of App Store Connect API key `.p8`)

## Notes
- If secrets are missing, CI still builds and packages an **unsigned** `.dmg`.
- For compatibility, CI sets `MACOSX_DEPLOYMENT_TARGET=13.0` by default (supports Ventura+).
