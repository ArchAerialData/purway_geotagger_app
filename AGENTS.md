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
- **Methane**: in‑place EXIF on all matchable JPGs + cleaned CSVs (ppm ≥1000) written **next to** original methane CSVs.
- **Encroachment**: copied JPGs to a **single pilot‑selected folder**, with logs for missing/unprocessed JPGs.
- **Combined**: a single run produces both outputs; renaming affects only encroachment copies.

---

## 6) Packaging / scripts organization
- macOS scripts live under `scripts/macos/` (not repo root).
- Windows scripts live under `scripts/windows/`.
- Pilot distribution should be a **signed + notarized `.app`**; avoid requiring Homebrew/Terminal/venv on pilot machines.

---

## 7) Always re‑read instructions
If any new instructions appear in future prompts or nested `AGENTS.md` files, follow the **most specific** rules. When in doubt, ask for clarification before proceeding.
