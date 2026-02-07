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

