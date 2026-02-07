# Wind Weather Autofill Spike Plan (Scoped, Planning Only)

Date created: 2026-02-07
Status: planning only. No implementation in this document.

## 1) Spike Goal

Evaluate and prototype a low-to-medium effort "Autofill Wind/Temp Data" flow for the Wind Data tab that:
- accepts pilot location input (`ZIP`, `city`, or full address),
- uses Start/End times (existing Wind row times),
- fetches weather values for those two timestamps only,
- auto-populates Wind Start/End fields:
  - `Direction`
  - `Speed (mph)`
  - `Gust (mph)`
  - `Temp (F)`

## 2) Constraints (Must Hold)

- macOS-first behavior and packaged `.app` compatibility.
- No extra laptop setup or local services.
- HTTP/HTTPS requests only (no browser automation, no shell tools).
- Keep UI responsive (network work off UI thread).
- Keep Wind DOCX generation flow intact if autofill is unavailable/fails.

## 3) Scope Boundaries

### In scope (spike)
- Provider feasibility validation.
- Thin vertical slice from location input to field autofill.
- Error handling for no network/no result.
- Minimal UI affordance in Wind tab.

### Out of scope (spike)
- Full production geocoding autocomplete UX polish.
- Historical climate analytics and bulk interval fills.
- Replacing manual entry workflow.
- Final provider lock for long-term production if contract/legal review is pending.

## 4) Recommended Provider Strategy for Spike

Primary weather authority:
- NWS/NOAA weather endpoints for wind + temperature values.

Location resolution:
- Start with geocoding from ZIP/city/address to lat/lon (no pilot lat/lon entry required).
- Keep geocoder implementation swappable behind one interface.

Fallback behavior:
- If provider data is unavailable for a field (for example gust), keep existing manual value and show a warning.

## 5) Data Contract for Autofill

Request input (from GUI):
- `location_query: str` (ZIP, city/state, or address)
- `report_date: YYYY_MM_DD`
- `start_time: h:mm + AM/PM` (from Start row)
- `end_time: h:mm + AM/PM` (from End row)

Output mapping (to existing controls):
- Start:
  - direction -> Start Direction
  - speed -> Start Speed
  - gust -> Start Gust
  - temp -> Start Temp
- End:
  - direction -> End Direction
  - speed -> End Speed
  - gust -> End Gust
  - temp -> End Temp

## 6) Phased Spike Plan

## Phase WS0 - Contract + Provider Lock (Planning Gate)

### Work items
- [ ] Finalize spike input/output contract and fallback rules.
- [ ] Confirm provider stack for spike run (weather source + geocoder source).
- [ ] Define timeout/retry policy and error message patterns.
- [ ] Define unit conversion policy:
  - wind to mph (integer),
  - temp to F (integer),
  - direction normalized to uppercase compass token.

### Files (planning docs)
- [ ] `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md` (this file)
- [ ] `WIND_DATA_DOCX_FEATURE_PLAN.md` (link/summary update if needed)

### Gate
- [ ] Contract and provider strategy approved for coding.

## Phase WS1 - Core Service Spike (No UI Automation Yet)

### Work items
- [ ] Add core models/client abstraction for:
  - geocode result,
  - weather snapshot result (start/end),
  - provider errors.
- [ ] Implement provider client with deterministic request/response parsing.
- [ ] Implement mapping/normalization to Wind input values.
- [ ] Implement robust fallback when one or more fields are missing.

### Files (new)
- [ ] `src/purway_geotagger/core/wind_weather_autofill.py`
- [ ] `tests/test_wind_weather_autofill.py`

### Files (modify)
- [ ] `src/purway_geotagger/core/wind_docx.py` (only if shared normalizers are reused)

### Tests / verification
- [ ] unit tests with mocked HTTP responses for:
  - successful start/end mapping,
  - missing field fallback behavior,
  - invalid location/no match,
  - timeout/network failure.

### Gate
- [ ] Service returns deterministic Start/End mapped values without UI dependencies.

## Phase WS2 - Wind Tab UI Thin Slice

### Work items
- [ ] Add `Autofill Wind/Temp Data` trigger in Wind Inputs section.
- [ ] Add lightweight prompt flow for:
  - location query,
  - optional confirmation of Start/End times (or reuse current row times directly).
- [ ] Execute lookup on worker thread and update UI on completion.
- [ ] Autofill Start/End controls while preserving manual override.
- [ ] Show source/status line (success, partial fill, failure reason).

### Files (new)
- [ ] `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py` (if dialog is split out)

### Files (modify)
- [ ] `src/purway_geotagger/gui/pages/wind_data_page.py`
- [ ] `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- [ ] `src/purway_geotagger/gui/style_sheet.py`
- [ ] `src/purway_geotagger/gui/workers.py` (or dedicated `workers_wind.py`)

### Tests / verification
- [ ] non-Qt logic tests for mapping/wiring glue.
- [ ] manual macOS smoke:
  - [ ] location query accepted,
  - [ ] start/end values autofill correctly,
  - [ ] preview updates immediately,
  - [ ] manual edits after autofill still work.

### Gate
- [ ] Thin slice works end-to-end without blocking UI thread.

## Phase WS3 - Hardening + Packaged App Readiness

### Work items
- [ ] Ensure feature behaves predictably with no network.
- [ ] Ensure no extra runtime setup/dependencies required.
- [ ] Add Help text for when to trust autofill vs override manually.
- [ ] Add rollback notes for all WS changes.

### Files (modify)
- [ ] `src/purway_geotagger/gui/pages/help_page.py`
- [ ] `README.md`
- [ ] `WIND_DATA_CHANGESET_NOTES.md`

### Tests / verification
- [ ] targeted pytest for WS modules.
- [ ] packaged app smoke (`.app`) with network available and unavailable.

### Gate
- [ ] Safe optional feature: does not degrade existing manual Wind workflow if API/geocoder fails.

## 7) Stop/Go Criteria

Proceed now if:
- WS0 contract/provider strategy is approved quickly and
- estimated effort remains low-to-medium after WS1 prototype.

Defer if:
- provider/legal constraints require substantial review or
- UI complexity starts forcing broad refactors outside Wind tab boundaries.
