# GitHub Actions Signed Release Runbook (macOS, No Notarization)

This runbook is for producing a **code-signed** `PurwayGeotagger.dmg` from GitHub Actions and validating the signature before pilot distribution.

Important: This repo currently does **not** notarize the app/DMG. Expect Gatekeeper prompts on first launch for apps distributed outside the Mac App Store.

Repo:
- `https://github.com/ArchAerialData/purway_geotagger_app`

Workflow:
- `.github/workflows/macos-build.yml`

Related CI scripts:
- `scripts/ci/macos_build.sh`
- `scripts/ci/macos_sign_and_package.sh`
- `scripts/ci/macos_package.sh`

## What this runbook verifies

1. The code builds and tests pass on macOS (`macos-14`, Python 3.11).
2. The app is signed with Developer ID (valid `codesign` verification).
3. ExifTool is bundled inside the app so pilots do not need Homebrew.

## Prerequisites

1. You can push to `main` in this repo.
2. GitHub repository secrets are set correctly.
3. `gh` (GitHub CLI) is installed on your Mac.
4. You are on a Mac for local Gatekeeper checks (`spctl`, `hdiutil`).

## Required GitHub Secrets

Both must exist for signed `main` builds:

- `MACOS_CERT_P12` (base64-encoded Developer ID Application certificate export, `.p12`)
- `MACOS_CERT_PASSWORD` (password used when exporting that `.p12`)

What they are:
- `MACOS_CERT_P12`: base64-encoded Developer ID Application certificate export (`.p12`).
- `MACOS_CERT_PASSWORD`: password used when exporting that `.p12`.

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

# 3) Trigger signed workflow on main
gh workflow run macos-build -R ArchAerialData/purway_geotagger_app --ref main

# 4) Watch latest run
RUN_ID=$(gh run list -R ArchAerialData/purway_geotagger_app --workflow macos-build --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" -R ArchAerialData/purway_geotagger_app
gh run view "$RUN_ID" -R ArchAerialData/purway_geotagger_app --log

# 5) Download artifact after success
gh run download "$RUN_ID" -R ArchAerialData/purway_geotagger_app -n PurwayGeotagger-macos -D /tmp/purway-release

# 6) Signature checks on downloaded artifact
# Mount DMG and copy app out for codesign verification
hdiutil attach /tmp/purway-release/PurwayGeotagger.dmg
cp -R /Volumes/PurwayGeotagger/PurwayGeotagger.app /tmp/PurwayGeotagger.app
hdiutil detach /Volumes/PurwayGeotagger

codesign --verify --deep --strict --verbose=2 /tmp/PurwayGeotagger.app

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
- `main` workflow is configured to fail if signing secrets are missing.

Pass signal:
 - Both required secret names are present.

Fail signal:
- Missing any secret name; CI will fail at signing readiness gate.

### Step 3 - Trigger workflow on `main`
Command:
- `gh workflow run macos-build -R ArchAerialData/purway_geotagger_app --ref main`

What it does:
- Starts the macOS build workflow on the `main` branch.

Why it matters:
- Signed artifacts for pilot distribution should come from `main`.

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
- You can confirm signing + DMG packaging happened in CI.

Pass signals to find in logs:
- `Code signing enabled.`
- `Signing app with identity:`

### Step 5 - Download artifact
Command:
- `gh run download ... -n PurwayGeotagger-macos -D /tmp/purway-release`

What it does:
- Downloads the CI artifact bundle (contains `PurwayGeotagger.dmg`).

Why it matters:
- Gives you the exact build pilots would receive.

Pass signal:
- `/tmp/purway-release/PurwayGeotagger.dmg` exists.

### Step 6 - Run local signature checks
Commands:
- `spctl --assess --type open -vv ...dmg`
- mount/copy/detach via `hdiutil`
- `spctl --assess --type execute -vv ...app`

What it does:
 - Validates the app signature without involving notarization/Gatekeeper.

Why it matters:
 - Confirms the DMG contains a correctly signed app bundle.

Pass signal:
 - `codesign --verify` exits `0`.

Fail signal:
 - `codesign` errors indicating signature problems or missing signing identity.

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

1. `Code signing secrets are required for main-branch distribution artifacts.`
- Signing secrets are missing or incorrectly configured.

2. `Developer ID Application identity not found in keychain.`
- Bad or mismatched `.p12`/password secret values.
3. Missing `bin/exiftool` or `bin/lib`.
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
- If this runbook passes end-to-end, you have high confidence the build is signed, packaged, and self-contained for ExifTool. (Gatekeeper prompts are still expected without notarization.)
