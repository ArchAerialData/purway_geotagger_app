# Purway Geotagger — Phased Implementation Plan (Hard Gates)

This repo already contains a working **skeleton**. This document breaks the remaining work (to fully meet `README.md`) into **ordered phases**.

**Rule:** Each phase is a **hard gate**. Do **not** start the next phase until **all** objectives, tests, verification steps, and housekeeping in the current phase are complete.

---

## Global organization rules (apply in every phase)

- Keep code modular and grouped by responsibility under `src/purway_geotagger/`:
  - `core/` (job model, pipeline orchestration, settings, logging, manifest)
  - `parsers/` (CSV parsing + correlation/indexing)
  - `exif/` (ExifTool invocation + verification)
  - `ops/` (copy/backup, rename, sort, flatten)
  - `gui/` (Qt UI, controllers, workers, models, widgets)
  - `util/` (time parsing, path utilities, platform helpers, shared errors)
- Keep tests in `tests/` only, named `test_*.py`, and prefer **unit tests** (mock ExifTool/subprocess).
- Keep configuration defaults in `config/` (read-only defaults) and persist user settings under the OS config dir.
- Prefer `pathlib` everywhere; avoid stringly-typed paths.
- No long-running work on the UI thread (use `QThread` + signals).
- Avoid “misc” modules; if a folder grows, create a subpackage with a clear name.
- Any run (success, cancel, or failure) must still emit `run_log.txt`, `run_config.json`, and `manifest.csv` in the run folder.

---

## Phase 0 — Baseline repo hygiene + repeatable dev workflow

**Goal:** Make the repo easy to run, test, and modify without regressions.

### Objectives
- Standardize how to run tests locally (and on a pilot laptop).
- Ensure all dependencies needed for **tests** are defined.
- Confirm the skeleton runs end-to-end in “dry run” mode without ExifTool writes.

### Work items
- [x] Decide and document how tests are installed/run (e.g., add `pytest` as a dev dependency in `requirements-dev.txt` and define a single canonical command like `python -m pytest`).
- [x] Add a minimal test runner script (optional) under `scripts/` if it improves repeatability.
- [x] Confirm `scripts/macos/setup_macos.sh` + `scripts/macos/run_gui.sh` still match the documented workflow in `README.md`.
- [x] Confirm run folder naming matches `<output_root>/PurwayGeotagger_<YYYYMMDD_HHMMSS>/`.
- [x] Confirm `run_log.txt`, `run_config.json`, and `manifest.csv` are always created even on cancel/failure.

### Tests / verification (must be done before moving on)
- [x] `python -m compileall src` succeeds.
- [x] Tests run successfully (once a test runner exists, use it consistently).
- [x] GUI starts via `python -m purway_geotagger.app` and can create at least one job (even if it fails due to missing inputs). **(Manual check completed during iterative GUI smoke sessions)**
- [x] Verify a cancelled job still emits `run_log.txt`, `run_config.json`, and `manifest.csv`.

### Housekeeping / organization
- [x] Remove dead code and keep responsibilities in the correct package folder.
- [x] Keep docs accurate (if you change run/test commands, update `README.md` and/or scripts).

**Gate:** Phase 0 is complete only when all checkboxes above are complete.

---

## Phase 1 — Scanner + CSV parsing + correlation correctness

**Goal:** Guarantee the app finds JPG/CSV inputs and matches photos to CSV rows exactly as specified in `README.md` (including failure reasons).

### Objectives
- Fully support all input layouts (mixed folder drops; recursive scanning).
- Match algorithm implements:
  - filename join when a photo reference column exists
  - timestamp join fallback with tie-handling + max delta threshold
  - clear failure reasons when correlation can’t be done

### Work items
- [x] Verify and, if needed, refine column-detection heuristics in `src/purway_geotagger/parsers/purway_csv.py`.
- [x] Expand timestamp parsing in `src/purway_geotagger/util/timeparse.py` only as needed (avoid over-guessing).
- [x] Ensure unmatched photos are recorded as `FAILED` (not silently skipped) with the exact-style reasons required by the README.

### Tests / verification (must be done before moving on)
- [x] Add/expand unit tests for:
  - scanning recursion + deduplication (`src/purway_geotagger/core/scanner.py`)
  - CSV parsing with BOM and column variants (`src/purway_geotagger/parsers/purway_csv.py`)
  - join behaviors: filename join, timestamp join, threshold failure, ambiguous tie failure
- [x] Run the full test suite and confirm all new tests pass.

### Housekeeping / organization
- [x] Keep parsing/matching logic in `parsers/` (do not leak CSV heuristics into GUI or ops).
- [x] Keep time parsing isolated in `util/timeparse.py` and add tests alongside existing ones in `tests/`.

**Gate:** Phase 1 is complete only when all checkboxes above are complete.

---

## Phase 2 — ExifTool write contract + per-file verification

**Goal:** Write the required EXIF/XMP tags via ExifTool using the “import CSV” contract from `README.md`, and produce reliable per-file success/failure results.

### Objectives
- Import CSV columns and ExifTool invocation match the README contract.
- Implement a verification pass (or equivalent reliable method) so each photo’s `exif_written` can be trusted.
- Dry run mode must behave deterministically (no subprocess calls).

### Work items
- [x] Ensure required GPS tags are written: `GPSLatitude`, `GPSLongitude`, **and** `GPSLatitudeRef` / `GPSLongitudeRef`.
- [x] Ensure optional XMP fields are handled via settings: `XMP:GPSLatitude`, `XMP:GPSLongitude`, and `XMP:Description`.
- [x] Ensure `ImageDescription` (and `XMP:Description` when enabled) includes `ppm=<value>`, `source_csv=<csv name>`, and `purway_payload=<user string>` when provided.
- [x] Implement per-file verification in `src/purway_geotagger/exif/exiftool_writer.py` (e.g., re-read tags and validate lat/lon were applied).
- [x] Ensure ExifTool failures surface cleanly as `FAILED` with actionable error messages.

### Tests / verification (must be done before moving on)
- [x] Unit tests for import CSV generation (no filesystem surprises; correct headers; absolute `SourceFile` paths).
- [x] Unit tests for GPS ref computation (N/S/E/W) and that refs are written for all records.
- [x] Unit tests that `ImageDescription` and `XMP:Description` contain required key/value pairs, including `purway_payload` when set.
- [x] Unit tests for subprocess invocation (mock `subprocess.run`) covering:
  - non-zero return code
  - stderr handling
  - cancel behavior
  - dry-run behavior (no subprocess)
- [x] If you add an optional integration test, it must be skipped automatically when `exiftool` is not available. (No integration test added in this phase.)

### Housekeeping / organization
- [x] Keep ExifTool-specific behavior contained to `exif/` (don’t spread subprocess calls elsewhere).
- [x] Keep error types in `src/purway_geotagger/util/errors.py` and reuse them consistently.

**Gate:** Phase 2 is complete only when all checkboxes above are complete.

---

## Phase 3 — Output behaviors: copy/overwrite, backup, rename, sort, flatten

**Goal:** Implement all output behaviors from `README.md` and ensure they compose correctly in the pipeline order.

### Objectives
- Overwrite vs copy behavior is safe and predictable.
- Optional flatten, rename, and sort-by-PPM work correctly on the post-write output paths.
- Cleanup behavior is explicitly enabled and **scoped**:
  - Copy mode: may remove empty directories only under the run folder.
  - Overwrite mode: may remove empty source directories **only** under user-selected input roots and only when the user explicitly opts in.

### Work items
- [x] Copy/overwrite correctness and safety:
  - [x] honor `create_backup_on_overwrite`
  - [x] ensure warnings/guardrails exist in GUI for overwrite mode (including a confirmation if cleanup of source dirs is enabled)
- [x] Rename templates:
  - [x] token rendering matches README (`{client}`, `{date}`, `{time}`, `{index}`, `{ppm}`, `{lat}`, `{lon}`, `{orig}`, and python format spec support)
  - [x] collision behavior appends `_dupN`
- [x] Sorting-by-PPM bins:
  - [x] bin naming and edge logic matches README defaults and settings
  - [x] sorting uses the output path after rename (if renaming enabled)
- [x] Flatten + optional cleanup of empty dirs:
  - [x] implement cleanup scoped per objective rules above (never delete outside run folder or user-selected input roots)
  - [x] ensure flatten updates task output paths and doesn’t break manifest

### Tests / verification (must be done before moving on)
- [x] Unit tests for:
  - collision-safe rename and copy naming
  - bin selection edge cases (exact boundaries)
  - flatten move behavior and path updates
  - cleanup empty dirs scope (must not traverse outside run folder)
- [x] End-to-end “dry run” pipeline test that exercises COPY → MATCH → (DRY)WRITE → RENAME → SORT → FLATTEN and validates manifest output fields.
- [x] Verify run folder naming conforms to `<output_root>/PurwayGeotagger_<YYYYMMDD_HHMMSS>/` in tests or integration checks.

### Housekeeping / organization
- [x] Keep file operations in `ops/`; avoid mixing them into `core/pipeline.py` beyond orchestration.
- [x] Keep any helper utilities private to their modules unless reused elsewhere.

**Gate:** Phase 3 is complete only when all checkboxes above are complete.

---

## Phase 4 — GUI completion: settings, templates, job UX

**Goal:** The GUI exposes all required configuration and job controls listed in `README.md`, while keeping long-running work off the UI thread.

### Objectives
- Users can configure: output root, overwrite/copy, flatten + cleanup, sort bins, join delta, XMP toggle, dry run, backup-on-overwrite.
- Renaming can be enabled with template selection and start index control.
- Multi-job session is supported (queued behavior should match README intent; do not silently run all jobs concurrently unless explicitly chosen).
- Progress updates must occur at least once per 25 files or once per second (whichever is more frequent).
- Users can enter optional `purway_payload` string for metadata injection.

### Work items
- [x] Implement rename template selection UI and wire to `JobOptions` (`src/purway_geotagger/gui/controllers.py` currently hardcodes renaming off).
- [x] Implement template editor dialog (start from `src/purway_geotagger/gui/widgets/template_editor.py` placeholder):
  - [x] create/edit/delete templates
  - [x] validate patterns and show a preview render
- [x] Add a Settings dialog/panel for bin edges, join delta, XMP default, backup-on-overwrite, etc.
- [x] Add an input field for `purway_payload` and wire it into job options and metadata composition.
- [x] Ensure job table and selected-job actions match README: cancel, open output folder, export/open manifest.

### Tests / verification (must be done before moving on)
- [x] Manual smoke test on macOS (or a supported dev OS):
  - [x] drag/drop works for mixed inputs
  - [x] job progress updates
  - [x] cancel works and leaves a manifest/log/config
  - [x] output folder open actions work
- [x] Verify progress update frequency (>= once per 25 files or once per second) during a medium-sized job.
- [x] Unit tests for non-Qt logic added to controllers/template manager (Qt UI layout tests are optional).

### Housekeeping / organization
- [x] Keep business logic out of widgets; prefer controller/service functions that can be unit tested.
- [x] Keep Qt threading boundaries explicit (signals carry plain data, not open file handles).

**Gate:** Phase 4 is complete only when all checkboxes above are complete.

---

## Phase 5 — Packaging + field readiness (macOS)

**Goal:** Deliver a reliable pilot-laptop setup and a build artifact strategy that works with Qt + ExifTool.

### Objectives
- Setup script is robust and verifiable.
- Build script produces a working macOS `.app` (or a clearly documented alternative) with the necessary Qt plugins and bundled resources.

### Work items
- [x] Validate and refine `scripts/macos/setup_macos.sh` to be idempotent and fail with clear guidance.
- [x] Update `scripts/macos/build_app.sh` to reliably bundle PySide6/Qt dependencies (PyInstaller flags/spec as needed).
- [x] Ensure non-code resources are included where needed (e.g., default templates JSON).
- [x] Document build output expectations (e.g., `dist/PurwayGeotagger.app`).

### Tests / verification (must be done before moving on)
- [x] (Tracking moved) On a clean-ish environment: run setup, run GUI, perform a dry run job. **Superseded in this file; tracked as an active final-release task in `RELEASE_READINESS_OPEN_ITEMS.md` (Item 4).**
- [x] (Tracking moved) Build the `.app` and launch it; confirm it can open, create a job, and show UI (ExifTool presence can be treated as an external dependency unless bundled). **Superseded in this file; tracked as an active final-release task in `RELEASE_READINESS_OPEN_ITEMS.md` (Item 5).**

### Housekeeping / organization
- [x] Keep scripts in `scripts/` and avoid embedding OS-specific logic in core modules.
- [x] Keep documentation aligned with the actual build/run steps.

**Gate:** Phase 5 is complete only when all checkboxes above are complete.

---

## Phase 6 — Optional enhancements (only after Phase 5 is complete)

These are explicitly “if time allows” per `README.md`. Implement only after all required phases are done.

### Candidates
- [x] Validation preview before running (sample of matched rows).
- [x] CSV schema inspector tab (detected columns and selections).
- [x] “Re-run failed only” workflow.
- [x] Auto-detect client profile rules.

**Gate:** Phase 6 is complete only when the chosen optional items are complete (with tests/verification and housekeeping at the same standard as prior phases).
