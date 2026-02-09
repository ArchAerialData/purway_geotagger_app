# GitHub Actions Release Checklist (macOS Signed DMG, No Notarization)

This checklist is for producing a **code-signed** macOS distribution artifact from GitHub Actions.

Important: This repo currently does **not** notarize the app/DMG. Expect Gatekeeper prompts on first launch for apps distributed outside the Mac App Store.

Assumptions:
- You are in the repo root: `/Users/archaerialtesting/Documents/purway_geotagger_app`
- You have GitHub CLI (`gh`) installed and access to the `ArchAerialData/purway_geotagger_app` repo
- GitHub repo secrets are already configured (see below)

Notes on cost:
- The `macos-build` workflow runs on a macOS runner (billable).
- Removing notarization avoids long, unpredictable waits on Apple during CI.

## 0) Local preflight (recommended before triggering CI)

```bash
cd /Users/archaerialtesting/Documents/purway_geotagger_app

# Builds the app locally and runs the full test suite.
# This reduces the chance of paying for a macOS runner only to fail quickly.
bash scripts/ci/macos_build.sh
```

What it does:
- Creates/uses `.venv`, installs requirements
- Runs `pytest`
- Builds `dist/PurwayGeotagger.app` via PyInstaller (`scripts/macos/build_app.sh`)

## 1) GitHub CLI login (only if needed)

```bash
gh auth login -h github.com --web
gh auth setup-git
```

What it does:
- Authenticates `gh` so you can list secrets, trigger workflows, and download artifacts
- Configures git to use your `gh` credentials for `git push`/fetch (HTTPS)

## 2) Confirm required repo secrets exist

```bash
gh secret list -R ArchAerialData/purway_geotagger_app
```

Required secret names (case-sensitive):
- `MACOS_CERT_P12`: base64-encoded Developer ID Application `.p12`
- `MACOS_CERT_PASSWORD`: password for the `.p12`

What they’re used for:
- Code signing: `MACOS_CERT_P12` + `MACOS_CERT_PASSWORD`

## 3) Trigger signed workflow on `main`

```bash
gh workflow run macos-build -R ArchAerialData/purway_geotagger_app --ref main
```

What it does:
- Starts the workflow `.github/workflows/macos-build.yml` on the `main` branch
- That workflow builds/tests, then (if signing secrets exist) signs and packages a DMG

## 4) Watch the latest run

```bash
REPO="ArchAerialData/purway_geotagger_app"

RUN_ID="$(
  gh run list -R "$REPO" \
    --workflow macos-build \
    --branch main \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId'
)"

gh run watch "$RUN_ID" -R "$REPO"
gh run view "$RUN_ID" -R "$REPO" --log
```

What it does:
- Finds the most recent run id for the `macos-build` workflow
- Streams status/logs until completion

## 5) Download the build artifact (DMG)

```bash
gh run download "$RUN_ID" -R "$REPO" -n PurwayGeotagger-macos -D /tmp/purway-release
ls -la /tmp/purway-release
```

What it does:
- Downloads the artifact produced by Actions (should include `PurwayGeotagger.dmg`)

## 6) Signature checks (on the downloaded artifact)

```bash
hdiutil attach /tmp/purway-release/PurwayGeotagger.dmg
cp -R /Volumes/PurwayGeotagger/PurwayGeotagger.app /tmp/PurwayGeotagger.app
hdiutil detach /Volumes/PurwayGeotagger

codesign --verify --deep --strict --verbose=2 /tmp/PurwayGeotagger.app
codesign -dv --verbose=4 /tmp/PurwayGeotagger.app 2>&1 | sed -n '1,80p'
```

What it does:
- Verifies the app bundle is correctly signed (without involving notarization/Gatekeeper)
- Prints the signing identity and signature metadata

## 7) Verify bundled ExifTool exists in the `.app`

```bash
ls -la /tmp/PurwayGeotagger.app/Contents/Resources/bin/exiftool
ls -la /tmp/PurwayGeotagger.app/Contents/Resources/bin/lib
```

What it does:
- Confirms the vendored ExifTool payload is inside the app bundle
- This is critical because pilot Macs must not depend on Homebrew/Terminal PATH

## Pilot Launch Expectations (No Notarization)

Because the DMG/app is signed but not notarized, pilots will typically need to do a one-time manual override on first launch:
- Copy `PurwayGeotagger.app` into `/Applications`.
- Try opening it.
- If macOS blocks it, use either:
  - Finder: right-click the app, choose **Open**, then confirm.
  - System Settings: Privacy & Security -> **Open Anyway** (after the block).
