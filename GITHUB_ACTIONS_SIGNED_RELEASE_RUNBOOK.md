# GitHub Actions Signed Release Runbook (macOS)

This runbook is for producing a signed + notarized `PurwayGeotagger.dmg` from GitHub Actions and validating Gatekeeper acceptance before pilot distribution.

Repo:
- `https://github.com/ArchAerialData/purway_geotagger_app`

Workflow:
- `.github/workflows/macos-build.yml`

Related CI scripts:
- `scripts/ci/macos_build.sh`
- `scripts/ci/macos_sign_and_notarize.sh`
- `scripts/ci/macos_package.sh`

## What this runbook verifies

1. The code builds and tests pass on macOS (`macos-14`, Python 3.11).
2. The app is signed with Developer ID and notarized by Apple.
3. The DMG and app pass `spctl` Gatekeeper checks.
4. ExifTool is bundled inside the app so pilots do not need Homebrew.

## Prerequisites

1. You can push to `main` in this repo.
2. GitHub repository secrets are set correctly.
3. `gh` (GitHub CLI) is installed on your Mac.
4. You are on a Mac for local Gatekeeper checks (`spctl`, `hdiutil`).

## Required GitHub Secrets

All five must exist for signed/notarized `main` builds:

- `MACOS_CERT_P12`
- `MACOS_CERT_PASSWORD`
- `APPLE_KEY_ID`
- `APPLE_ISSUER_ID`
- `APPLE_API_KEY_P8`

What they are:
- `MACOS_CERT_P12`: base64-encoded Developer ID Application certificate export (`.p12`).
- `MACOS_CERT_PASSWORD`: password used when exporting that `.p12`.
- `APPLE_KEY_ID`: App Store Connect API key ID.
- `APPLE_ISSUER_ID`: App Store Connect issuer UUID for your Team API key.
- `APPLE_API_KEY_P8`: base64-encoded App Store Connect API key file (`.p8`).

## Step-by-step Commands

Run from your terminal:

```bash
cd /Users/archaerialtesting/Documents/purway_geotagger_app

# 0) Local preflight (should pass cleanly before CI run)
bash scripts/ci/macos_build.sh

# 1) GitHub CLI login (if needed)
gh auth login -h github.com --web

# 2) Confirm required repo secrets exist
gh secret list -R ArchAerialData/purway_geotagger_app

# Required names:
# MACOS_CERT_P12
# MACOS_CERT_PASSWORD
# APPLE_KEY_ID
# APPLE_ISSUER_ID
# APPLE_API_KEY_P8

# 3) Trigger signed/notarized workflow on main
gh workflow run macos-build -R ArchAerialData/purway_geotagger_app --ref main

# 4) Watch latest run
RUN_ID=$(gh run list -R ArchAerialData/purway_geotagger_app --workflow macos-build --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" -R ArchAerialData/purway_geotagger_app
gh run view "$RUN_ID" -R ArchAerialData/purway_geotagger_app --log

# 5) Download artifact after success
gh run download "$RUN_ID" -R ArchAerialData/purway_geotagger_app -n PurwayGeotagger-macos -D /tmp/purway-release

# 6) Gatekeeper checks on downloaded artifact
spctl --assess --type open -vv /tmp/purway-release/PurwayGeotagger.dmg

# Mount DMG and copy app out for execute-assess
hdiutil attach /tmp/purway-release/PurwayGeotagger.dmg
cp -R /Volumes/PurwayGeotagger/PurwayGeotagger.app /tmp/PurwayGeotagger.app
hdiutil detach /Volumes/PurwayGeotagger

spctl --assess --type execute -vv /tmp/PurwayGeotagger.app

# 7) Verify bundled ExifTool exists in app payload
ls -la /tmp/PurwayGeotagger.app/Contents/Resources/bin/exiftool
ls -la /tmp/PurwayGeotagger.app/Contents/Resources/bin/lib
```

## Detailed Meaning of Each Step

### Step 0 - Local preflight
Command:
- `bash scripts/ci/macos_build.sh`

What it does:
- Creates/uses `.venv`.
- Installs app + dev dependencies.
- Runs test suite.
- Builds the app bundle with PyInstaller.
- Verifies packaged resources needed by app startup.

Why it matters:
- Catches obvious breakages before waiting on CI.

Pass signal:
- Script exits `0` and prints build completion.

Fail signal:
- Any non-zero exit, test failures, or missing build dependencies.

### Step 1 - Authenticate GitHub CLI
Command:
- `gh auth login -h github.com --web`

What it does:
- Authenticates `gh` to your GitHub account using browser flow.

Why it matters:
- Needed to query secrets, trigger workflows, watch logs, and download artifacts.

Pass signal:
- `gh auth status -h github.com` shows logged-in account.

### Step 2 - Verify secrets exist in repo
Command:
- `gh secret list -R ArchAerialData/purway_geotagger_app`

What it does:
- Lists secret names configured in repository settings.

Why it matters:
- `main` workflow is configured to fail if signing/notarization secrets are missing.

Pass signal:
- All 5 required secret names are present.

Fail signal:
- Missing any secret name; CI will fail at signing readiness gate.

### Step 3 - Trigger workflow on `main`
Command:
- `gh workflow run macos-build -R ArchAerialData/purway_geotagger_app --ref main`

What it does:
- Starts the macOS build workflow on the `main` branch.

Why it matters:
- Signed/notarized artifacts for pilot distribution should come from `main`.

Pass signal:
- Workflow run appears in Actions list.

### Step 4 - Watch logs and completion
Commands:
- `RUN_ID=$(...)`
- `gh run watch ...`
- `gh run view ... --log`

What it does:
- Captures run ID for latest `main` run.
- Streams live status until completion.
- Prints full logs for post-check.

Why it matters:
- You can confirm notarization + Gatekeeper checks actually happened in CI.

Pass signals to find in logs:
- `Signing + notarization enabled.`
- `Signing app with identity:`
- `Submitting for notarization...`
- `Notarization complete:`
- `spctl --assess --type execute` success
- `spctl --assess --type open` success

### Step 5 - Download artifact
Command:
- `gh run download ... -n PurwayGeotagger-macos -D /tmp/purway-release`

What it does:
- Downloads the CI artifact bundle (contains `PurwayGeotagger.dmg`).

Why it matters:
- Gives you the exact build pilots would receive.

Pass signal:
- `/tmp/purway-release/PurwayGeotagger.dmg` exists.

### Step 6 - Run local Gatekeeper checks
Commands:
- `spctl --assess --type open -vv ...dmg`
- mount/copy/detach via `hdiutil`
- `spctl --assess --type execute -vv ...app`

What it does:
- Validates macOS policy acceptance for opening DMG and launching app.

Why it matters:
- Confirms smooth internal distribution behavior and fewer “unidentified developer” problems.

Pass signal:
- `spctl` exits `0` for both checks.

Fail signal:
- Rejection text indicating signature/notarization/stapling problem.

### Step 7 - Confirm ExifTool is bundled
Commands:
- `ls -la .../bin/exiftool`
- `ls -la .../bin/lib`

What it does:
- Confirms bundled ExifTool executable and Perl lib directory exist inside app payload.

Why it matters:
- Finder-launched app cannot rely on Homebrew PATH on pilot laptops.

Pass signal:
- Both paths exist; `exiftool` is executable.

## Common Failure Cases and Meaning

1. `Signing/notarization secrets are required for main-branch distribution artifacts.`
- At least one required secret is missing.

2. `Developer ID Application identity not found in keychain.`
- Bad or mismatched `.p12`/password secret values.

3. Notary submission auth errors (`401`/`403`).
- Wrong `APPLE_KEY_ID`, `APPLE_ISSUER_ID`, or `.p8` content.

4. `spctl` rejects DMG or app.
- Notarization or stapling did not complete correctly, or signature mismatch.

5. Missing `bin/exiftool` or `bin/lib`.
- Packaging regression; app may fail EXIF workflows on pilot machines.

## Optional Quick Re-check Commands

```bash
# Confirm artifact exists
ls -la /tmp/purway-release/PurwayGeotagger.dmg

# Confirm app exists after copy-out
ls -la /tmp/PurwayGeotagger.app

# Print Gatekeeper detail again
spctl --assess --type open -vv /tmp/purway-release/PurwayGeotagger.dmg
spctl --assess --type execute -vv /tmp/PurwayGeotagger.app
```

## Notes

- Keep this as a repeatable release checklist before each pilot distribution.
- If this runbook passes end-to-end, you have high confidence the build is signed, notarized, Gatekeeper-acceptable, and self-contained for ExifTool.
