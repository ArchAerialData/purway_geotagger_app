# Purway Geotagger — AGENTS Instructions (Repository Root)

This file contains persistent rules for all future sessions. **Always read this file first** before making changes or answering requests in this repo.

---

## 1) macOS‑first (non‑negotiable)
- Pilots use **macOS only**. Avoid any decisions that could break macOS compatibility.
- Assume the app launches from **Finder / a packaged `.app`**, so PATH may not include Homebrew locations.
- Always handle macOS/Dropbox artifacts (`._*`, `.DS_Store`, `__MACOSX/`) without crashes.
- Prefer **argument‑list** subprocess calls (no shell strings).

---

## 2) Organization rules (match existing repo structure)
- Keep code modular under `src/purway_geotagger/`:
  - `core/` (job model, pipeline orchestration, settings, logging, manifest)
  - `parsers/` (CSV parsing + correlation/indexing)
  - `exif/` (ExifTool invocation + verification)
  - `ops/` (copy/backup, rename, sort, flatten)
  - `gui/` (Qt UI, controllers, workers, models, widgets)
  - `util/` (time parsing, path utilities, platform helpers, shared errors)
- Prefer `pathlib` everywhere; avoid stringly‑typed paths.
- No long‑running work on the UI thread (use `QThread` + signals).
- Keep ExifTool calls isolated in `exif/`.
- Keep CSV heuristics isolated in `parsers/`.

---

## 3) Phase discipline (always follow)
All implementation must follow `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` and `IMPLEMENTATION_PHASES.md`.

**Rules:**
- Do **not** start a new phase until **all** items and **Gate** for the current phase are complete.
- At the end of each phase, **update `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`**:
  - mark all checkboxes,
  - add a “Phase Notes” paragraph with date, tests/verification run, and any deviations.
- Keep tests/verification minimal but explicit and recorded.

---

## 4) GUI clarity is critical
- The GUI must be **pilot‑friendly** and minimal by default.
- Use the explicit **Phase 4/4A GUI checklist** in `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md`.
- Modes must be clear: Methane, Encroachment, Combined.
- Encroachment renaming templates apply **only** to encroachment copies.

---

## 5) Outputs / workflows (confirmed decisions)
- **Methane**: in‑place EXIF on all matchable JPGs + cleaned CSV/XLSX files (default ppm ≥1000) written **next to** their original metadata files. The default-on calibration toggle excludes finite methane >0 with finite relative altitude <1 m only from cleaned outputs and their KMZs; never from photo processing. Preserve existing PAC per data sheet, otherwise calculate via the shared PAC calculator. XLSX outputs are saved-value copies; fail uncached formulas rather than erasing them.
- **Encroachment**: copied JPGs to a **single pilot‑selected folder**, with logs for missing/unprocessed JPGs.
- **Combined**: a single run produces both outputs; renaming affects only encroachment copies.

---

## 6) Packaging / scripts organization
- macOS scripts live under `scripts/macos/` (not repo root).
- Windows scripts live under `scripts/windows/`.
- For every Windows build, use `scripts/windows/build_exe.ps1` so the newest successful build replaces the entire `dist/windows/PurwayGeotagger/` folder, including `_internal`. The stable launcher target is `dist/windows/PurwayGeotagger/PurwayGeotagger.exe`; do not leave the newest build only in staging or a versioned folder. Verify the output and `build-info.json` before reporting completion.
- Windows packages must display their app version and unique build ID in the window title. Preserve embedded build metadata and explicit local-change status; use `scripts/windows/package_portable.py` for verified, version-named coworker ZIPs.
- The local Git Bash alias `methane` in `~/.bashrc` targets that stable executable. Keep this path stable for future builds. CI artifacts do not automatically update the local checkout; local builds must be run explicitly (see README).
- Pilot distribution should be a **signed + notarized `.app`**; avoid requiring Homebrew/Terminal/venv on pilot machines.

---

## 7) Always re‑read instructions
If any new instructions appear in future prompts or nested `AGENTS.md` files, follow the **most specific** rules. When in doubt, ask for clarification before proceeding.
