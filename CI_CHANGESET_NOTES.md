# CI Change Set Notes (2026-02-06)

This file documents CI/workflow updates as isolated change sets so each can be reverted cleanly.

## Revert strategy

- Before commit:
  - `git restore .github/workflows/macos-build.yml scripts/ci/macos_sign_and_notarize.sh scripts/ci/README.md`
- After commit:
  - `git checkout <commit-before-change> -- .github/workflows/macos-build.yml scripts/ci/macos_sign_and_notarize.sh scripts/ci/README.md`

## CHG-CI-001: Fix invalid workflow secret conditions + improve Gatekeeper verification

### Purpose

- Resolve GitHub Actions workflow parse failure caused by invalid `if:` secret expressions.
- Ensure signing/notarization path explicitly validates Gatekeeper acceptance of both `.app` and `.dmg`.

### Files changed

- `.github/workflows/macos-build.yml`
- `scripts/ci/macos_sign_and_notarize.sh`
- `scripts/ci/README.md`

### What changed

1. Workflow conditional fix (`.github/workflows/macos-build.yml`)
- Added step `Detect signing readiness` with step id `signing_ready`.
- Step checks whether all required secrets are non-empty and writes output:
  - `enabled=true` when all secrets exist
  - `enabled=false` otherwise
- Updated signing step condition:
  - from direct secret expression to `if: ${{ steps.signing_ready.outputs.enabled == 'true' }}`
- Updated unsigned package condition:
  - to `if: ${{ steps.signing_ready.outputs.enabled != 'true' }}`

2. Signing/notarization hardening (`scripts/ci/macos_sign_and_notarize.sh`)
- After notarization submit/wait:
  - staple `.app` bundle
  - staple `.dmg`
- Added Gatekeeper checks in CI:
  - `spctl --assess --type execute -vv <app>`
  - `spctl --assess --type open -vv <dmg>`

3. CI behavior documentation (`scripts/ci/README.md`)
- Clarified that workflow evaluates secret availability via a dedicated readiness step.
- Clarified that all required secrets must be present for signing/notarization.
- Documented that CI now validates Gatekeeper acceptance with `spctl`.

### Expected behavior after this change

- Workflow is valid YAML/expressions and no longer fails schema parsing on `if:`.
- If all 5 signing secrets are present:
  - app is signed, DMG is notarized/stapled, and Gatekeeper checks run.
- If any signing secret is missing:
  - app still builds, unsigned DMG is produced and uploaded.

### Rollback only this change set

- `git restore .github/workflows/macos-build.yml scripts/ci/macos_sign_and_notarize.sh scripts/ci/README.md`

## CHG-CI-002: Disable CI notarization (signed DMG only)

### Purpose

- Avoid long/unpredictable `notarytool` waits in GitHub Actions (macOS runner cost control).
- Produce a **code-signed** DMG artifact only.

### Files changed

- `.github/workflows/macos-build.yml`
- `scripts/ci/macos_sign_and_package.sh`
- `scripts/ci/README.md`
- `GITHUB_ACTIONS_RELEASE_CHECKLIST.md`
- `GITHUB_ACTIONS_SIGNED_RELEASE_RUNBOOK.md`
- `scripts/macos/APPLE_SIGNING_NOTARIZATION_SETUP.md`
- `scripts/macos/README.md`
- Removed: `.github/workflows/macos-notarize-finalize.yml`
- Removed: `scripts/ci/macos_finalize_notarization.sh`

### What changed

1. Workflow behavior (`.github/workflows/macos-build.yml`)
- Readiness check now requires only:
  - `MACOS_CERT_P12`
  - `MACOS_CERT_PASSWORD`
- Main branch enforces code signing secrets (no notarization requirement).
- Artifact upload only includes `dist/PurwayGeotagger.dmg`.

2. CI signing script (`scripts/ci/macos_sign_and_package.sh`)
- Still signs the `.app` with Developer ID and packages a DMG.
- No longer calls:
  - `xcrun notarytool ...`
  - `xcrun stapler ...`
  - `spctl --assess ...`

3. Docs updated to match “signed, not notarized” distribution.

### Expected behavior after this change

- On `main`, CI builds/tests and then produces a **signed** `PurwayGeotagger.dmg`.
- No notarization is attempted; Gatekeeper prompts are expected on pilot Macs.

### Rollback only this change set

- `git restore .github/workflows/macos-build.yml scripts/ci/macos_sign_and_package.sh scripts/ci/macos_sign_and_notarize.sh scripts/ci/README.md GITHUB_ACTIONS_RELEASE_CHECKLIST.md GITHUB_ACTIONS_SIGNED_RELEASE_RUNBOOK.md scripts/macos/APPLE_SIGNING_NOTARIZATION_SETUP.md scripts/macos/README.md`
