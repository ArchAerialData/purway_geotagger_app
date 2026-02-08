# Wind Weather Autofill Spike Plan (Scoped, Planning + WS0 Lock)

Date created: 2026-02-07
Last updated: 2026-02-07
Status: WS0 complete, WS1 complete, WS2 implemented (manual macOS smoke pending gate close), WS2.6 source-chain hardening landed.

## 1) Spike Goal

Evaluate and prototype a low-to-medium effort `Autofill Wind/Temp Data` flow for the Wind Data tab that:
- accepts pilot location input (`ZIP`, `city/state`, or full address),
- reuses Start/End times already in the Wind Inputs rows,
- fetches retrospective weather values for those two timestamps only,
- auto-populates Start/End wind fields:
  - `Direction`
  - `Speed (mph)`
  - `Gust (mph)`
  - `Temp (F)`

## 2) Locked Constraints (Must Hold)

- macOS-first behavior and packaged `.app` compatibility.
- No extra laptop setup or background services.
- HTTPS API calls only.
- Network requests must stay off the UI thread.
- Wind DOCX generation/manual workflow must remain usable when autofill fails.
- Retrospective values only (no forecast dependency for this feature).
- U.S.-only operations:
  - location suggestions and selections are constrained to `country_code=US`.

## 3) Provider Feasibility Summary (Research Locked)

Weather source (authoritative):
- NOAA/NWS API (`api.weather.gov`) station observations for retrospective values.

Geocoding source for type-ahead suggestions:
- Open-Meteo geocoding API for ZIP/city/address search and suggestions.

Why this split:
- NWS observations provide the needed weather fields from an authoritative U.S. weather source.
- NWS does not provide a rich city/ZIP autocomplete UX by itself.
- Open-Meteo geocoding gives low-friction search/suggestion behavior for pilots.

## 4) Data Availability Conclusions

Required fields for Start/End rows:
- Direction: available via NWS observations (`windDirection`), typically as degrees.
- Speed: available via NWS observations (`windSpeed`).
- Gust: available via NWS observations (`windGust`), but can be null/missing.
- Temperature: available via NWS observations (`temperature`).

Granularity findings:
- NWS station observations can be sub-hourly (often around 5-minute cadence at sampled stations).
- Not guaranteed uniform 30-minute cadence everywhere.
- For Wind Data UX, keep pilot time input at current precision and select nearest observation record.

Retrospective window findings:
- Same-day and recent-day retrieval is feasible from station observations.
- Older retention depth can vary by station/API behavior; this feature should target current day + recent days first.

## 5) Locked UX/Behavior Rules for Autofill

Location input:
- Single search field (ZIP/city/state/address) with suggestion list.
- Suggestion row should include city/state and, when available, postal code.
- For ZIP queries, prefer showing the exact ZIP entered by the pilot when available.
- Pilot confirms one selected location before lookup.

Time handling:
- Keep existing Start/End time controls (hour and optional 30-minute increments).
- Convert local report date + row times to UTC using selected location timezone.
- For each target timestamp, map nearest retrospective observation.

Partial fill policy:
- Fill any field that resolves.
- Do not clear an already-entered manual value for fields that cannot be resolved.
- Show per-row/per-field warnings when values are missing or stale.

Manual verification policy:
- Persist a source verification URL from the provider used for returned values:
  - NWS station observations URL when NWS data is complete,
  - AviationWeather METAR URL when METAR was used as primary fallback/backfill,
  - Open-Meteo archive URL when historical fallback/backfill values were used.
- Expose an `Open Autofill Source URL` action in the Wind Data UI after a successful autofill run.

Preview policy:
- Output Preview remains driven by Wind Inputs only (already implemented in current Wind tab).

## 6) Data Contract for Autofill (WS1)

Request input (from GUI):
- `location_query: str` (ZIP/city/state/address)
- `report_date: YYYY_MM_DD`
- `start_time: h:mm + AM/PM`
- `end_time: h:mm + AM/PM`

Intermediate location model:
- selected suggestion with:
  - `display_name`
  - `latitude`
  - `longitude`
  - `timezone` (IANA, ex. `America/Chicago`)

Output mapping (to existing Wind controls):
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

## 7) Phased Spike Plan

## Phase WS0 - Contract + Provider Lock (Planning Gate)

### Work items
- [x] Finalize spike input/output contract and fallback rules.
- [x] Confirm provider stack for spike run (weather source + geocoder source).
- [x] Define timeout/retry policy and error message patterns.
- [x] Define unit conversion policy:
  - wind to mph (integer),
  - temp to F (integer),
  - direction normalized to uppercase compass token.

### Files (planning docs)
- [x] `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md` (this file)
- [x] `WIND_DATA_IMPLEMENTATION_PHASES.md` (W6 linkage already present)

### Gate
- [x] Contract and provider strategy approved for coding.

### Phase Notes

- Date completed: 2026-02-07
- Key decisions:
  - Weather data source: NWS observations (`api.weather.gov`).
  - Location suggestion source: Open-Meteo geocoding.
  - Retrospective focus: same-day + recent days.
  - Missing values: partial-fill with explicit warnings.
  - 30-minute inputs remain allowed; nearest observation mapping handles variable cadence.
- Risks deferred to WS3:
  - API usage/legal review for geocoding provider terms.
  - Long-range retrospective retention expectations.

## Phase WS1 - Core Service Spike (No UI Automation Yet)

### Work items
- [x] Add core models/client abstraction for:
  - geocode result,
  - weather snapshot result (start/end),
  - provider errors.
- [x] Implement provider client with deterministic request/response parsing.
- [x] Implement mapping/normalization to Wind input values.
- [x] Implement robust fallback when one or more fields are missing.

### Files (new)
- [x] `src/purway_geotagger/core/wind_weather_autofill.py`
- [x] `tests/test_wind_weather_autofill.py`

### Files (modify)
- [x] `src/purway_geotagger/core/wind_docx.py` (not required in WS1)

### Tests / verification
- [x] unit tests with mocked HTTP responses for:
  - successful start/end mapping,
  - missing field fallback behavior,
  - invalid location/no match,
  - no-observation provider failure.

### Gate
- [x] Service returns deterministic Start/End mapped values without UI dependencies.

### Phase Notes

- Date completed: 2026-02-07
- Verification run:
  - `python3 -m pytest tests/test_wind_weather_autofill.py` (6 passed)
  - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py` (35 passed)
  - `python3 -m compileall src` (pass)
- Deviations:
  - WS1 uses a swappable `JsonHttpClient` abstraction with stdlib `urllib` default implementation (no new dependencies added).

## Phase WS2 - Wind Tab UI Thin Slice

### Work items
- [x] Add `Autofill Wind/Temp Data` trigger in Wind Inputs section.
- [x] Add lightweight prompt flow for:
  - location query,
  - suggestion pick/confirmation.
- [x] Reuse current Start/End row times by default.
- [x] Execute lookup on worker thread and update UI on completion.
- [x] Autofill Start/End controls while preserving manual override.
- [x] Show source/status line (success, partial fill, failure reason).
  - [x] Include an explicit verification URL action for manual audit checks.

### Files (new)
- [x] `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py` (dialog split out)

### Files (modify)
- [x] `src/purway_geotagger/gui/pages/wind_data_page.py`
- [x] `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
- [x] `src/purway_geotagger/gui/style_sheet.py` (not required in this thin slice)
- [x] `src/purway_geotagger/gui/workers.py` (no dedicated `workers_wind.py` needed)

### Tests / verification
- [x] non-Qt logic tests for mapping/wiring glue.
- [x] (Tracking moved) manual macOS smoke:
  - [x] location query accepted,
  - [x] suggestions show city/state (+ZIP where available),
  - [x] start/end values autofill correctly,
  - [x] preview updates immediately,
  - [x] manual edits after autofill still work.
  - Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6) so this file no longer owns open tasks.

### Gate
- [x] (Tracking moved) Thin slice works end-to-end without blocking UI thread. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 6).

### Phase Notes

- Date implemented: 2026-02-07
- Verification run:
  - `python3 -m pytest tests/test_wind_autofill_dialog.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py` (17 passed)
  - `python3 -m pytest tests/test_wind_autofill_dialog.py tests/test_wind_weather_autofill.py tests/test_wind_page_preview_behavior.py tests/test_wind_page_logic.py` (20 passed)
  - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py` (36 passed)
  - `python3 -m compileall src` (pass)
- Deviations:
  - Thin slice uses a dialog-triggered flow with debounced search and explicit location selection.
  - Style sheet updates were not required for this slice because existing classes already provide acceptable button/status styling.
  - Added WS2.1 lifecycle hardening after crash report: autofill worker cleanup is now instance-specific to prevent stale `finished` signals from deleting the active running worker.
  - Added WS2.3 control consistency hardening: popup target-time controls now use the same custom stepper style as main Wind Inputs and both pages auto-normalize 24h typed hours (`13`-`23`) to 12h + `PM`.
  - Added WS2.4 report-date hardening: popup now includes explicit report-date selection constrained to current-year-through-today and uses that selected date for autofill requests.
  - Added WS2.5 weather-source hardening: when NWS returns partial rows (for example missing gust), service now requests Open-Meteo archive and backfills only missing fields while preserving NWS values that were present.
  - WS2.5 verification:
    - `python3 -m pytest tests/test_wind_weather_autofill.py` (8 passed)
    - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py` (47 passed)
    - `python3 -m compileall src` (pass)
  - Added WS2.6 provider-chain hardening: fallback order is now `NWS -> AviationWeather METAR -> Open-Meteo archive`, and partial rows are backfilled in that order to improve gust/data completion.
  - WS2.6 verification:
    - `python3 -m pytest tests/test_wind_weather_autofill.py` (9 passed)
    - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py` (48 passed)
    - `python3 -m compileall src` (pass)

## Phase WS3 - Hardening + Packaged App Readiness

### Work items
- [x] (Tracking moved) Ensure feature behaves predictably with no network. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 9).
- [x] Ensure no extra runtime setup/dependencies required.
- [x] Add Help text for when to trust autofill vs override manually.
- [x] Add rollback notes for all WS changes.

### Files (modify)
- [x] `src/purway_geotagger/gui/pages/help_page.py` (superseded for v1; guidance is embedded directly in Wind page info-tooltip workflow)
- [x] `README.md`
- [x] `WIND_DATA_CHANGESET_NOTES.md`

### Tests / verification
- [x] targeted pytest for WS modules.
- [x] (Tracking moved) packaged app smoke (`.app`) with network available and unavailable. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 9).

### Gate
- [x] (Tracking moved) Safe optional feature: does not degrade existing manual Wind workflow if API/geocoder fails. Active release tracking moved to `RELEASE_READINESS_OPEN_ITEMS.md` (Item 9).

### Phase Notes

- Date updated: 2026-02-08
- Verification:
  - `python3 -m pytest tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py`
  - `python3 -m pytest tests/test_wind_template_contract.py tests/test_wind_formatting.py tests/test_wind_validation.py tests/test_wind_docx_writer.py tests/test_wind_debug_export.py tests/test_wind_page_logic.py tests/test_wind_page_preview_behavior.py tests/test_wind_weather_autofill.py tests/test_wind_autofill_dialog.py`
- Deviations:
  - Remaining packaged-app network/offline resilience checks are tracked centrally in `RELEASE_READINESS_OPEN_ITEMS.md` (Item 9).

## 8) Stop/Go Criteria

Proceed now if:
- WS1 service prototype passes mocked tests and
- UI thin slice can be added without refactoring unrelated tabs.

Defer if:
- provider legal constraints require substantial review or
- historical data retention requirements expand beyond recent-day use.

## 9) Research Sources

- https://www.weather.gov/documentation/services-web-api
- https://api.weather.gov/openapi.json
- https://open-meteo.com/en/docs/geocoding-api
- https://open-meteo.com/en/pricing
- https://www.ncei.noaa.gov/cdo-web/webservices/v2
