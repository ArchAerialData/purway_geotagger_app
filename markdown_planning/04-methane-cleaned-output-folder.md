# Methane Cleaned Output Folder

## Goal

For Methane Only workflows, place cleaned methane deliverables in a `Cleaned Output` subfolder at each source CSV parent folder instead of placing cleaned files directly beside the source CSV.

The `Cleaned Output` folder should contain only cleaned CSV and KMZ deliverables. It should not contain logs or unrelated files.

## Scope

- Methane Only cleaned CSV output location.
- Methane Only optional KMZ output location.
- Batch runs with nested source CSV parent folders.
- Tests for cleaned CSV and KMZ paths.
- Methane UI copy that currently describes cleaned output location.

## Non-Goals

- Do not change threshold filtering logic.
- Do not change KMZ content generation.
- Do not change EXIF behavior.
- Do not move logs into `Cleaned Output`.
- Do not change encroachment output behavior.
- Do not change source CSV or JPG locations.

## Current Behavior / Evidence

- Cleaned CSV path is currently computed with `path.with_name(...)`, which places the cleaned CSV in the same folder as the source CSV. Source: `src/purway_geotagger/ops/methane_outputs.py:44`.
- KMZ path is currently derived from the cleaned CSV path by swapping the suffix to `.kmz`. Source: `src/purway_geotagger/ops/methane_outputs.py:48`.
- The cleaned CSV writer creates the cleaned path parent directory, opens the cleaned CSV there, and writes filtered rows. Source: `src/purway_geotagger/ops/methane_outputs.py:126`.
- The pipeline calls `generate_methane_outputs(...)` for both `RunMode.METHANE` and `RunMode.COMBINED`. Source: `src/purway_geotagger/core/pipeline.py:80`.
- Methane page UI currently tells users cleaned CSVs are saved next to each source methane CSV. Source: `src/purway_geotagger/gui/pages/methane_page.py:340`.
- Combined wizard UI currently uses the same "saved next to each source methane CSV" wording. Source: `src/purway_geotagger/gui/pages/combined_wizard.py:811`.
- Existing tests assert `cleaned_csv_path(src, 1000)` and KMZ path behavior directly. Sources: `tests/test_methane_outputs.py:16` and `tests/test_kmz_writer.py:19`.

## Design

- For Methane Only, cleaned deliverables should be written to:
  - `<source_csv_parent>/Cleaned Output/<source_stem>_Cleaned_<threshold>-PPM.csv`
  - `<source_csv_parent>/Cleaned Output/<source_stem>_Cleaned_<threshold>-PPM.kmz`
- For batch runs with CSVs in multiple parent folders, create one `Cleaned Output` subfolder per source CSV parent folder as needed.
- If multiple CSVs share a parent folder, reuse the same `Cleaned Output` folder.
- Keep log files wherever the current Methane workflow places them. Do not write logs into `Cleaned Output`.
- Keep JPG association logic rooted at the source CSV parent folder, not the new `Cleaned Output` folder.
- Preserve result summaries and run report links by storing the new cleaned CSV and KMZ paths in existing result fields.
- Because `generate_methane_outputs(...)` is shared by Methane and Combined today, implementation must intentionally choose one of these approaches:
  - Add a destination strategy or output subfolder parameter and pass `Cleaned Output` only for `RunMode.METHANE`.
  - Apply the new foldering to both Methane and Combined only if confirmed as acceptable.

## Compatibility Notes

- Must work on macOS and Windows.
- Use `pathlib.Path` for all path construction.
- Folder name should be exactly `Cleaned Output` unless user requests otherwise.
- Avoid shell commands for filesystem work.
- Ensure spaces in folder names work on both platforms.
- Handle existing `Cleaned Output` folders idempotently with `mkdir(parents=True, exist_ok=True)`.
- Preserve macOS/Dropbox artifact tolerance by not scanning the output folder as image input unless the existing scanner already does so safely.

## Implementation Phases

### Phase 1 - Confirm Mode Boundary

- [ ] Confirm whether this change applies only to Methane Only or also to Combined.
- [ ] Decide whether to parameterize `generate_methane_outputs(...)`.
- [ ] Document final mode behavior in this plan before code changes.

Gate: Mode boundary is explicit, because the output generator is currently shared by Methane and Combined.

### Phase 2 - Output Path Logic

- [ ] Update cleaned CSV path construction for the confirmed workflow.
- [ ] Ensure KMZ path remains next to the cleaned CSV inside `Cleaned Output`.
- [ ] Ensure JPG association still scans the source CSV parent folder.
- [ ] Ensure logs and run summaries are not written into `Cleaned Output`.

Gate: Path helper tests prove cleaned CSV and KMZ go to the expected subfolder.

### Phase 3 - Pipeline And UI Copy

- [ ] Wire the new destination behavior through Methane Only pipeline execution.
- [ ] Update Methane page preview copy from "saved next to each source methane CSV" to the new folder wording.
- [ ] Update Combined wizard copy only if Combined behavior changes or if wording needs to clarify Methane Only behavior.
- [ ] Confirm run report links still point to the created cleaned CSV and KMZ files.

Gate: UI copy matches actual output behavior.

### Phase 4 - Verification

- [ ] Update `tests/test_methane_outputs.py`.
- [ ] Update `tests/test_kmz_writer.py`.
- [ ] Add nested parent folder coverage.
- [ ] Run targeted methane output tests.
- [ ] Record verification results in this plan's Phase Notes.

Gate: Tests prove root, nested, and shared-parent cleaned outputs land in `Cleaned Output`.

## Verification Plan

- `pytest tests/test_methane_outputs.py tests/test_kmz_writer.py tests/test_methane_outputs_photo_association.py`
- Add test for multiple CSV parent folders:
  - `parent_a/methane.csv -> parent_a/Cleaned Output/...`
  - `parent_b/nested/methane.csv -> parent_b/nested/Cleaned Output/...`
- Confirm no log files are created in `Cleaned Output`.
- GitHub Actions must continue to pass on macOS and Windows.

## Risks / Open Questions

- User text says "XLSX/KMZ" once and "KMZ and CSV" later. Current code produces CSV/KMZ, so this plan assumes CSV/KMZ unless XLSX is confirmed.
- Because the output generator is shared by Methane and Combined, isolating the change to Methane Only may require a new parameter rather than changing `cleaned_csv_path(...)` globally.
- Existing help text and release docs may still say "saved next to each source methane CSV"; implementation should search and update user-facing wording as needed.

## Phase Notes

- 2026-06-19: Planning file created from user request. No implementation or tests run in this phase.

## Source Of Authority

- User request dated 2026-06-19.
- `markdown_planning/00-Task-Requirements.md`
- Repository root `AGENTS.md`
