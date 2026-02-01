# macOS scripts (pilot-first)

Pilots use **macOS**, so distribution should avoid requiring Homebrew, Terminal, or manual virtualenv steps.

## Development (engineers only)

- Setup dev machine: `bash scripts/macos/setup_macos.sh`
- Run GUI from source: `bash scripts/macos/run_gui.sh`
- Run tests: `bash scripts/macos/run_tests.sh`

These scripts use a repo-local virtualenv (`.venv/`) and Homebrew-installed dependencies.

## Pilot distribution (recommended approach)

**Goal:** pilot installs/opens a signed `.app` and it “just works”.

Recommended packaging strategy:
1) Build a self-contained `.app` with PyInstaller (bundles Python + Python deps; no venv needed on pilot machines).
2) Bundle **ExifTool** with the app (or install it via a standard macOS installer), and have the app call it via an explicit path.
   - Do **not** rely on `PATH` inside a Finder-launched GUI app.
3) Code-sign + notarize the app (and any bundled executables) to avoid Gatekeeper prompts.

Build the `.app` (developer machine):
- `bash scripts/macos/build_app.sh`

**Vendored ExifTool (preferred)**
- Place the extracted distribution under `scripts/macos/vendor/Image-ExifTool-<version>/`
  - Must include `exiftool` and `lib/`
- `build_app.sh` will auto-detect this and bundle:
  - `bin/exiftool`
  - `bin/lib/*` (so the script can find its Perl libs)

Notes:
- If ExifTool is not bundled, the app must provide a clear pilot-facing message and a simple “Install/Locate ExifTool” flow.
- Attempting to silently install Homebrew/Python/ExifTool from inside a GUI app is brittle on macOS (admin prompts + security restrictions). Prefer a packaged `.app` or a `.pkg` installer.

## Signing + notarization (pilot distribution)

After building, sign + notarize:
- `CODESIGN_IDENTITY="Developer ID Application: Name (TEAMID)" NOTARY_PROFILE="AC_PROFILE" bash scripts/macos/sign_and_notarize.sh dist/PurwayGeotagger.app`

You must first create the notarytool profile:
```sh
xcrun notarytool store-credentials "AC_PROFILE" --apple-id "you@domain" --team-id "TEAMID" --password "app-specific-password"
```
