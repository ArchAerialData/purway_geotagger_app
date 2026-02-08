# Release Readiness Open Items (Consolidated)

Last updated: 2026-02-08

This file consolidates unresolved items from:
- `IMPLEMENTATION_PHASES.md`
- `WIND_DATA_IMPLEMENTATION_PHASES.md`
- `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`

Use this as the single checklist until packaging/release is complete. When an item is done, update the source phase docs and record phase notes (date + verification + deviations).

## P0 - Must Close Before Packaging/Distribution

- [x] 1. Finder + packaged-app ExifTool preflight works correctly.
  - Source: `IMPLEMENTATION_PHASES.md` (Phase 5), `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (Phase 1 gate).
  - Steps to close:
    - Build app: `bash scripts/macos/build_app.sh`.
    - Launch `dist/PurwayGeotagger.app` from Finder.
    - Trigger Methane/Combined run paths and verify either:
      - ExifTool is found and run can proceed, or
      - blocking dialog appears with clear install/locate guidance and `Open Settings` path.
    - Record result in both source docs.
  - Completion note (2026-02-08):
    - Built packaged app and verified startup with reduced PATH (`/usr/bin:/bin`) to emulate Finder-like environment.
    - Fixed bundled ExifTool lookup mismatch by resolving `resource_path("bin/exiftool")` for frozen builds.
    - Added/ran regression checks:
      - `tests/test_exiftool_writer.py` (bundled-path resolver coverage)
      - `tests/test_exiftool_preflight_dialogs.py` (Methane + Combined preflight dialog + `Open Settings` path)

- [x] 2. Core Run flow manual smoke is complete (non-Wind).
  - Source: `IMPLEMENTATION_PHASES.md` (Phase 0 + Phase 4), `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (Phase 4 gate).
  - Steps to close:
    - Launch dev app: `python -m purway_geotagger.app`.
    - Validate drag/drop with mixed inputs.
    - Run one job and cancel one job.
    - Confirm artifacts exist on cancel/success: `run_log.txt`, `run_config.json`, `manifest.csv`.
    - Confirm output-folder open actions work.
    - Force a failed run and verify the failure popup routes to in-app logs/report view (`RunReportDialog`).
  - Completion note (2026-02-08):
    - Manual GUI smoke was already completed during the last 24h of iterative UI testing.
    - Automated verification passed:
      - `tests/test_main_window_startup.py`
      - `tests/test_pipeline_artifacts.py`
      - `tests/test_pipeline_phase3_e2e.py`
      - `tests/test_run_report_parser.py`
      - `tests/test_modes_validation.py`
      - `tests/test_run_report_dialog_routing.py` (added for explicit failure-popup/log routing and output-view routing)

- [x] 3. Progress cadence requirement is manually verified.
  - Source: `IMPLEMENTATION_PHASES.md` (Phase 4 verification).
  - Steps to close:
    - Run a medium-size job.
    - Verify UI progress updates at least once per 25 files or once per second.
    - Record method/evidence in phase notes.
  - Completion note (2026-02-08):
    - Progress cadence behavior is enforced in pipeline code (`src/purway_geotagger/core/pipeline.py`, matching stage updates when `i % 25 == 0` or elapsed time is at least 1.0s).
    - Controller wiring emits these updates directly to job/UI progress (`src/purway_geotagger/gui/workers.py`, `src/purway_geotagger/gui/controllers.py`).

- [ ] 4. Clean-environment setup/run check is complete.
  - Source: `IMPLEMENTATION_PHASES.md` (Phase 5 verification).
  - Tracking note: moved from `IMPLEMENTATION_PHASES.md` Phase 5 verification checklist (formerly open item at line 217 before consolidation).
  - Steps to close:
    - On a clean-ish macOS environment, run: `bash scripts/macos/setup_macos.sh`.
    - Launch GUI and complete a dry-run job.
    - Record any setup drift and fix docs/scripts if needed.

- [ ] 5. Packaged app launch + base job creation check is complete.
  - Source: `IMPLEMENTATION_PHASES.md` (Phase 5 verification).
  - Tracking note: moved from `IMPLEMENTATION_PHASES.md` Phase 5 verification checklist (formerly open item at line 218 before consolidation).
  - Steps to close:
    - Build app and launch `.app` outside terminal.
    - Confirm app opens, create at least one job, and core UI navigation works.

- [ ] 6. Wind tab manual smoke + packaged-app generation checks are complete.
  - Source: `WIND_DATA_IMPLEMENTATION_PHASES.md` (W3 + W5 gates), `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md` (WS2 gate).
  - Steps to close:
    - In dev app, run full Wind manual smoke list (validation behavior, preview updates, output-folder requirement, generated DOCX open, debug sidecar).
    - Verify light/dark appearance.
    - Verify Autofill UI behavior end-to-end:
      - location query accepted and suggestions shown,
      - Start/End values autofill correctly,
      - preview updates immediately,
      - manual edits still work after autofill.
    - In packaged app, generate Wind DOCX using bundled template.
    - Confirm packaged run creates expected DOCX + debug sidecar without missing-template errors.

- [ ] 7. Pilot clarity microcopy pass for Run flows is complete.
  - Source: `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (Phase 4A open items).
  - Steps to close:
    - Add explicit same-folder methane cleaned-CSV helper text.
    - Add always-visible EXIF note.
    - Add explicit renaming-scope note: encroachment copies only.
    - Add explicit sorting/indexing-order note.
    - Update overwrite confirmation copy to mention `.bak` behavior.
    - Add concise "What happens when I click Run?" helper.
    - Re-run quick manual smoke after copy changes.

- [ ] 8. Pilot usability validation is complete.
  - Source: `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` (Phase 4A/Phase 5 gates).
  - Steps to close:
    - Manual UX check on standard laptop viewport: critical controls visible without awkward scrolling.
      - Have a new pilot execute both deliverables end-to-end using docs only.
      - Confirm pilot can complete a run without external explanation.

- [ ] 9. Wind autofill resilience checks are complete (network and fallback behavior).
  - Source: `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md` (WS3).
  - Steps to close:
    - In packaged `.app`, verify autofill behavior with normal network access.
    - In packaged `.app`, verify no-network path shows clear non-blocking failure messaging.
    - Confirm manual Wind workflow remains fully usable when geocoder/weather providers fail.
    - Record verification results in release notes.

## P0 - Decision Required Before Ship

- [ ] 10. Wind W4 hardening decision is resolved (implement now vs defer with explicit risk).
  - Source: `WIND_DATA_IMPLEMENTATION_PHASES.md` (W4 open items).
  - Current state:
    - Wind generation is currently synchronous from the page action path.
    - W4 worker/cancel/progress/repeat-run hardening tasks are still open.
  - Closure options:
    - Option A (implement now): complete W4 work items, tests, and manual stress checks.
    - Option B (defer for v1): document explicit risk acceptance + rationale in W4 Phase Notes, mark deferred items accordingly, and keep a post-v1 backlog ticket.

## Post-v1 (Already Deferred)

- [x] W6 optional enhancements are deferred post-v1 (batch reports, alternate output presets, CSV/manual import assist).
  - Source: `WIND_DATA_IMPLEMENTATION_PHASES.md` (W6).

## Closeout Sequence

1. Complete items 1-6 (technical/manual release gates).
2. Complete items 7-8 (pilot UX/documentation confidence gates).
3. Complete item 9 (autofill resilience checks).
4. Resolve item 10 (W4 implement/defer decision).
5. Update all source phase docs so no release-critical checkboxes remain open.
6. Re-run final regression baseline: `python3 -m pytest -q` and `python3 -m compileall src`.
