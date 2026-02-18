# Wind Data ZIP Autofill Resource Map

Generated: 2026-02-17  
Repository: `purway_geotagger_app`  
Purpose: inventory the scripts, APIs, and GUI code used to retrieve wind/weather values from ZIP or location input, so this capability can be ported into another application as a standalone module.

## 1) What this module currently does

The current wind autofill flow supports:

- Search location by `ZIP`, `City, State`, or address-like text.
- Restrict suggestions to U.S. locations.
- Convert chosen location + report date + Start/End local times into UTC targets.
- Fetch retrospective observations using provider chain:
  - `NWS -> AviationWeather METAR -> Open-Meteo Archive`
- Backfill missing fields in this order:
  - `NWS missing fields -> METAR -> Open-Meteo Archive`
- Fill only fields with values (does not clear fields when data is missing).
- Persist a verification URL so user can audit source observations.

Target fields per row:

- Wind direction (compass token)
- Wind speed (mph integer)
- Wind gust (mph integer)
- Temperature (F integer)

## 2) External APIs used

No API key is required for any provider in the current implementation.

### 2.1 Open-Meteo Geocoding (location search)

- Base URL: `https://geocoding-api.open-meteo.com/v1/search`
- Used by: `OpenMeteoGeocoder` in `src/purway_geotagger/core/wind_weather_autofill.py`
- Request params:
  - `name`: user query
  - `count`: suggestion count (default `8`, clamped `1..20`)
  - `language`: default `en`
  - `format`: `json`
  - `countryCode`: `US` (hard filter)
- Response fields consumed:
  - `name`, `latitude`, `longitude`, `timezone`, `admin1`, `country_code`, `postcodes` or `postcode`

ZIP behavior:

- ZIP is extracted only when query contains exactly 5 digits after digit-only compaction.
- If API returns `postcodes`, typed ZIP is preferred when present.
- If postcode is missing but query had ZIP, typed ZIP is still shown in display label.

### 2.2 NOAA NWS Observations (primary weather source)

- Base URL: `https://api.weather.gov`
- Used by: `NwsObservationClient`
- Call sequence:
  - `GET /points/{lat},{lon}`
  - Follow `properties.observationStations`
  - `GET /stations/{stationId}/observations?start=...&end=...`
- Response fields consumed:
  - `timestamp`
  - `temperature`
  - `windDirection`
  - `windSpeed`
  - `windGust`

### 2.3 AviationWeather METAR (fallback/backfill)

- Base URL: `https://aviationweather.gov/api/data`
- Endpoint: `https://aviationweather.gov/api/data/metar`
- Used by: `AviationWeatherMetarClient`
- Request params:
  - `format=json`
  - `hours=<calculated retrospective window>`
  - `bbox=minLat,minLon,maxLat,maxLon`
- Search radius steps (default): `25, 80, 160` miles
- Response fields consumed:
  - `obsTime` / `reportTime`, `temp`, `wdir`, `wspd`, `wgst`, `lat`, `lon`, `icaoId`

### 2.4 Open-Meteo Historical Archive (fallback/backfill)

- Base URL: `https://archive-api.open-meteo.com/v1/archive`
- Used by: `OpenMeteoArchiveClient`
- Request params:
  - `latitude`
  - `longitude`
  - `start_date` (selected report date)
  - `end_date` (selected report date)
  - `hourly=temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m`
  - `timezone=<IANA zone>`
- Response fields consumed:
  - `hourly.time`
  - `hourly.temperature_2m`
  - `hourly.wind_speed_10m`
  - `hourly.wind_gusts_10m`
  - `hourly.wind_direction_10m`

## 3) Core backend code inventory (the actual retriever module)

### 3.1 Primary file to port

- `src/purway_geotagger/core/wind_weather_autofill.py`

Main dataclasses:

- `LocationSuggestion`
- `WindAutofillRequest`
- `WindAutofillRow`
- `WindAutofillResult`

Main service and clients:

- `WindWeatherAutofillService`
- `OpenMeteoGeocoder`
- `NwsObservationClient`
- `AviationWeatherMetarClient`
- `OpenMeteoArchiveClient`
- `JsonHttpClient` and `UrlLibJsonHttpClient` abstraction

Important behavior details in this file:

- `ZoneInfo` timezone conversion based on geocoder timezone.
- Start/end local times converted to UTC.
- Search window around requested times: default `+/- 2` hours for NWS station observations.
- Nearest-observation matching for requested timestamps.
- Unit normalization:
  - wind: `m/s`, `km/h`, `kt`, `mph` -> mph integer
  - temp: `degC/degF` -> F integer
  - direction degrees -> 16-point compass token
- Field-level missing warnings and backfill warning synthesis.
- Verification URL generation for provider used.

### 3.2 Optional helper for packaged app HTTPS reliability

- `src/purway_geotagger/core/utils.py`
  - `resource_path(...)` is for packaged resources (not weather API logic).
- `wind_weather_autofill.py` itself handles SSL CA with optional `certifi` fallback for macOS packaged app reliability.

## 4) GUI integration code inventory

These files are the complete GUI path for ZIP search -> suggestion select -> autofill apply.

### 4.1 Worker threading (no network on UI thread)

- `src/purway_geotagger/gui/workers.py`
  - `WindLocationSearchWorker(QThread)` -> calls `service.search_locations(...)`
  - `WindAutofillWorker(QThread)` -> calls `service.build_autofill(...)`

### 4.2 Autofill popup dialog (query + suggestions + date/time selection)

- `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
  - Search query input (`ZIP or City, State`)
  - Debounced search timer (`350ms`)
  - Suggestion list
  - Report date picker
  - Start/End target time controls
  - Emits:
    - `search_requested(str)`
    - `autofill_requested()`

### 4.3 Wind page controller logic

- `src/purway_geotagger/gui/pages/wind_data_page.py`
  - Opens dialog
  - Starts search worker and ignores stale results via generation counter
  - Starts autofill worker
  - Applies result to input grid
  - Stores `_last_autofill_source_url`
  - Enables `Open Autofill Source URL` action
  - Shows provider/backfill/warning status text to user

### 4.4 Wind input grid (where retrieved values are applied)

- `src/purway_geotagger/gui/widgets/wind_entry_grid.py`
  - `apply_autofill_rows(start, end)` only writes non-`None` fields
  - Preserves manual values when provider returns missing fields

### 4.5 App navigation wiring to wind page

- `src/purway_geotagger/gui/main_window.py`
  - Adds `Wind Data` top nav tab and page
- `src/purway_geotagger/gui/pages/home_page.py`
  - Home card route into wind tab (`wind_data_selected`)

### 4.6 Adjacent wind modules (optional for ZIP autofill-only port)

These are not required to fetch weather by ZIP, but they are part of the full Wind Data feature in this repo:

- `src/purway_geotagger/core/wind_docx.py`
  - Wind input validation and placeholder payload building
- `src/purway_geotagger/core/wind_docx_writer.py`
  - DOCX rendering, sidecar debug JSON, embedded metadata XML
- `src/purway_geotagger/core/wind_template_contract.py`
  - Template placeholder contract validation
- `src/purway_geotagger/gui/pages/wind_data_logic.py`
  - Wind template resolution and generate-button readiness logic

## 5) Supporting resources and scripts

### 5.1 Runtime dependencies

- `requirements.txt`
  - `PySide6`
  - `python-dateutil`
  - `appdirs`
  - `certifi` (important for packaged HTTPS on macOS)
  - `pyinstaller`

### 5.2 Run/test scripts

- macOS:
  - `scripts/macos/run_gui.sh`
  - `scripts/macos/run_tests.sh`
  - `scripts/macos/build_app.sh` (includes bundled wind template resources)
- Windows (dev utility scripts):
  - `scripts/windows/run_gui.ps1`
  - `scripts/windows/run_tests.ps1`

### 5.3 Packaging and bundled resources

- `PurwayGeotagger.spec` (bundles `config/wind_templates`)
- `scripts/macos/build_app.sh` (explicitly bundles wind template path)
- `config/wind_templates/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`

Note:

- `src/purway_geotagger/gui/pages/wind_data_logic.py` still contains a legacy dev fallback path candidate:
  - `wind_data_generator/Example of Template Structure/PRODUCTION_WindData_ClientName_YYYY_MM_DD.docx`
- In this current repo snapshot, that fallback file does not exist; the bundled config template path exists and is used.

## 6) Test resources that define expected behavior

Primary weather-autofill behavior tests:

- `tests/test_wind_weather_autofill.py`
  - U.S.-only geocoder filtering
  - ZIP preference logic
  - NWS mapping
  - nearest observation logic
  - METAR fallback and field backfill
  - Open-Meteo archive fallback
  - failure messaging when all providers fail

GUI integration tests:

- `tests/test_wind_autofill_dialog.py`
- `tests/test_wind_page_preview_behavior.py`
- `tests/test_main_window_startup.py`

Related wind page logic tests:

- `tests/test_wind_page_logic.py`

## 7) Planning and implementation context docs

- `README.md` (wind feature map and provider hierarchy)
- `WIND_WEATHER_AUTOFILL_SPIKE_PLAN.md` (provider strategy and UX rules)
- `WIND_DATA_IMPLEMENTATION_PHASES.md` (phase linkage, release gates)
- `WIND_DATA_CHANGESET_NOTES.md` (change history, rollback blocks)

## 8) End-to-end runtime flow (current implementation)

1. User opens Wind page and clicks `Autofill Wind/Temp Data`.
2. User enters query (ZIP/city/address).
3. Dialog emits search event (manual click or debounce).
4. `WindLocationSearchWorker` runs `WindWeatherAutofillService.search_locations`.
5. Geocoder returns U.S. suggestions with timezone metadata.
6. User selects location/date/start/end times in popup.
7. `WindAutofillWorker` runs `WindWeatherAutofillService.build_autofill`.
8. Service fetches NWS rows; if unavailable uses METAR; if unavailable uses Open-Meteo archive.
9. If rows are partial, service backfills missing fields from METAR then Open-Meteo archive.
10. GUI applies non-empty fields to Start/End controls.
11. GUI stores and exposes source verification URL.
12. User can click `Open Autofill Source URL` and manually validate.

## 9) Standalone module extraction guidance for another repo

Minimum copy set for ZIP/weather autofill only:

- `src/purway_geotagger/core/wind_weather_autofill.py`
- plus a thin adapter in target repo UI for:
  - location search
  - request creation
  - result application

If reusing existing UI approach:

- also port:
  - `src/purway_geotagger/gui/workers.py` (or equivalent worker classes)
  - `src/purway_geotagger/gui/widgets/wind_autofill_dialog.py`
  - relevant portions of `src/purway_geotagger/gui/pages/wind_data_page.py`
  - relevant portions of `src/purway_geotagger/gui/widgets/wind_entry_grid.py`

Recommended integration boundary in new app:

- Keep provider logic in one backend module (service + clients + DTOs).
- Keep GUI independent and only call:
  - `search_locations(query)`
  - `build_autofill(request)`

Minimal example call pattern:

```python
from datetime import date
from purway_geotagger.core.wind_weather_autofill import (
    WindWeatherAutofillService,
    WindAutofillRequest,
)

service = WindWeatherAutofillService()
suggestions = service.search_locations("77008", limit=8)

request = WindAutofillRequest(
    location=suggestions[0],
    report_date=date(2026, 2, 6),
    start_time_24h="13:00",
    end_time_24h="17:00",
)

result = service.build_autofill(request)
```

## 10) Known constraints and caveats to preserve if porting

- U.S.-only suggestion policy is hard-coded.
- ZIP extraction only handles 5-digit ZIP, not ZIP+4 parsing.
- No API key support is currently implemented.
- No explicit retry/backoff strategy is implemented.
- METAR fallback history is bounded (`max_history_hours` default `720`).
- Date/time behavior expects same-day Start/End (end must be >= start).
- Network calls must remain off UI thread.

## 11) Quick checklist for another repo agent

1. Port `wind_weather_autofill.py` first and run service-only tests.
2. Wire location search and autofill calls into target GUI worker threads.
3. Preserve warning display and source URL verification action.
4. Preserve non-destructive field application (only overwrite fields with real values).
5. Add or adapt tests equivalent to `tests/test_wind_weather_autofill.py` and GUI smoke tests.
