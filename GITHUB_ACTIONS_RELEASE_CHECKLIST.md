# GitHub Actions Release Checklist (macOS Signed + Notarized)

This checklist is for producing a macOS distribution artifact from GitHub Actions and validating that it is usable on pilot Macs (Gatekeeper-friendly).

Assumptions:
- You are in the repo root: `/Users/archaerialtesting/Documents/purway_geotagger_app`
- You have GitHub CLI (`gh`) installed and access to the `ArchAerialData/purway_geotagger_app` repo
- GitHub repo secrets are already configured (see below)

Notes on cost:
- The `macos-build` workflow runs on a macOS runner (billable). This is why we avoid waiting on Apple notarization inside the build job.
- Notarization is handled asynchronously: the build job will submit the DMG, record a submission id, and upload artifacts. A separate “finalize” step can wait/staple later (or you can do it locally).

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
- `APPLE_KEY_ID`: App Store Connect API key id
- `APPLE_ISSUER_ID`: App Store Connect issuer id (UUID)
- `APPLE_API_KEY_P8`: base64-encoded `.p8` private key

What they’re used for:
- Code signing: `MACOS_CERT_P12` + `MACOS_CERT_PASSWORD`
- Notarization: `APPLE_KEY_ID` + `APPLE_ISSUER_ID` + `APPLE_API_KEY_P8`

## 3) Trigger signed/notarized workflow on `main`

```bash
gh workflow run macos-build -R ArchAerialData/purway_geotagger_app --ref main
```

What it does:
- Starts the workflow `.github/workflows/macos-build.yml` on the `main` branch
- That workflow builds/tests, then (if secrets exist) signs + submits for notarization
- The job does **not** wait for Apple to finish notarization (to control macOS runner cost)

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
- Downloads the artifact produced by Actions (should include `PurwayGeotagger.dmg` plus notarization metadata files)

## 6) Gatekeeper checks (on the downloaded artifact)

```bash
spctl --assess --type open -vv /tmp/purway-release/PurwayGeotagger.dmg

# Mount DMG so we can assess the app bundle itself.
hdiutil attach /tmp/purway-release/PurwayGeotagger.dmg
cp -R /Volumes/PurwayGeotagger/PurwayGeotagger.app /tmp/PurwayGeotagger.app
hdiutil detach /Volumes/PurwayGeotagger

spctl --assess --type execute -vv /tmp/PurwayGeotagger.app
```

What it does:
- `spctl` simulates Gatekeeper assessment
- If the build has been notarized + stapled, this should pass cleanly
- If the build is signed but not notarized/stapled yet, assessment may fail even though it might still be runnable via manual override (not ideal for internal distribution)

## 7) Verify bundled ExifTool exists in the `.app`

```bash
ls -la /tmp/PurwayGeotagger.app/Contents/Resources/bin/exiftool
ls -la /tmp/PurwayGeotagger.app/Contents/Resources/bin/lib
```

What it does:
- Confirms the vendored ExifTool payload is inside the app bundle
- This is critical because pilot Macs must not depend on Homebrew/Terminal PATH

## Optional: Finalize notarization later (without holding a macOS runner open)

If the build workflow submitted notarization but didn’t wait, the artifact should include `notarization_submission_id.txt`.

### Option A: Finalize via GitHub Actions (short “finalize” workflow)

Run the `macos-notarize-finalize` workflow and provide:
- `build_run_id`: the `macos-build` run id that produced the DMG artifact
- `wait_timeout`: how long this finalize run should wait (example: `20m`)

Result:
- A new artifact `PurwayGeotagger-macos-notarized` containing a stapled DMG (if accepted).

### Option B: Finalize locally (no GitHub runner time)

```bash
cd /Users/archaerialtesting/Documents/purway_geotagger_app

# Put the DMG + notarization_submission_id.txt in the same folder (or export NOTARY_SUBMISSION_ID)
export APPLE_KEY_ID="..."
export APPLE_ISSUER_ID="..."
export APPLE_API_KEY_P8="..."   # base64

bash scripts/ci/macos_finalize_notarization.sh /tmp/purway-release/PurwayGeotagger.dmg
```

What it does:
- Polls Apple for the submission id until accepted/rejected (bounded by `NOTARY_WAIT_TIMEOUT`, default `20m`)
- Staples the DMG on acceptance and runs `spctl --assess`

