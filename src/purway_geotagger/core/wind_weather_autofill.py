from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta, timezone
import json
from math import asin
from math import cos
from math import isfinite
from math import radians
from math import sin
from math import sqrt
import ssl
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


NWS_BASE_URL = "https://api.weather.gov"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AWC_BASE_URL = "https://aviationweather.gov/api/data"
AWC_METAR_URL = f"{AWC_BASE_URL}/metar"
US_COUNTRY_CODE = "US"


@dataclass(frozen=True)
class WeatherMatchPolicy:
    """Application defaults, not a guarantee of site-level representativeness."""

    max_distance_miles: float = 25.0
    max_time_delta_minutes: int = 60

    def __post_init__(self) -> None:
        if not isfinite(self.max_distance_miles) or not 1 <= self.max_distance_miles <= 100:
            raise ValueError("Station distance must be between 1 and 100 miles.")
        if not 1 <= self.max_time_delta_minutes <= 120:
            raise ValueError("Time difference must be between 1 and 120 minutes.")


@dataclass(frozen=True)
class WeatherFieldSource:
    provider: str
    kind: str  # observed or estimated
    observed_at_utc: datetime
    station_id: str | None
    source_url: str | None
    distance_miles: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    model: str | None = None


_ROW_MISSING_WARNING_BY_FIELD = {
    "direction": "Wind direction not reported for selected timestamp.",
    "speed_mph": "Wind speed not reported for selected timestamp.",
    "gust_mph": "Wind gust not reported for selected timestamp.",
    "temp_f": "Temperature not reported for selected timestamp.",
}
_ROW_FIELD_LABELS = {
    "direction": "direction",
    "speed_mph": "speed",
    "gust_mph": "gust",
    "temp_f": "temp",
}


class WindAutofillError(RuntimeError):
    """Base exception for wind weather autofill."""


class WindAutofillLocationError(WindAutofillError):
    """Raised when location search/selection cannot resolve."""


class WindAutofillProviderError(WindAutofillError):
    """Raised when a provider call or provider response is invalid."""


@dataclass(frozen=True)
class LocationSuggestion:
    query_text: str
    display_name: str
    latitude: float
    longitude: float
    timezone_name: str
    city: str = ""
    state: str = ""
    postal_code: str = ""


@dataclass(frozen=True)
class WindAutofillRow:
    direction: str | None
    speed_mph: int | None
    gust_mph: int | None
    temp_f: int | None
    observed_at_utc: datetime | None
    observed_at_local: datetime | None
    station_id: str | None
    source_url: str | None
    warnings: tuple[str, ...]
    field_sources: dict[str, WeatherFieldSource] = field(default_factory=dict)


@dataclass(frozen=True)
class WindAutofillRequest:
    location: LocationSuggestion
    report_date: date
    start_time_24h: str
    end_time_24h: str
    policy: WeatherMatchPolicy = field(default_factory=WeatherMatchPolicy)


@dataclass(frozen=True)
class WindAutofillResult:
    location: LocationSuggestion
    start: WindAutofillRow
    end: WindAutofillRow
    verification_url: str | None
    warnings: tuple[str, ...]
    request: WindAutofillRequest | None = None

    @property
    def source_urls(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            source.source_url for row in (self.start, self.end)
            for source in row.field_sources.values() if source.source_url
        ))


class JsonHttpClient:
    """Small interface to keep provider calls mockable and deterministic in tests."""

    def get_json(self, url: str, params: Mapping[str, str] | None = None) -> Any:
        raise NotImplementedError


class UrlLibJsonHttpClient(JsonHttpClient):
    def __init__(self, *, timeout_seconds: float = 10.0, user_agent: str = "purway-geotagger/1.0") -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        # Packaged macOS builds may not have an OpenSSL CA bundle available by default.
        # Prefer certifi's bundled CA store when present so HTTPS calls work on pilot machines.
        self._ssl_context = _build_https_ssl_context()

    def get_json(self, url: str, params: Mapping[str, str] | None = None) -> Any:
        target = url
        if params:
            target = f"{url}?{urlencode(dict(params))}"
        request = Request(
            target,
            headers={
                "Accept": "application/geo+json, application/json",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds, context=self._ssl_context) as response:
                if response.status == 204:
                    return []
                payload = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise WindAutofillProviderError(f"Weather API request failed: {exc}") from exc

        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WindAutofillProviderError("Weather API returned invalid JSON.") from exc
        if not isinstance(parsed, (dict, list)):
            raise WindAutofillProviderError("Weather API returned an unexpected response shape.")
        return parsed


def _build_https_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        # Fall back to OpenSSL defaults (works on developer machines where the CA bundle is configured).
        return ssl.create_default_context()


class OpenMeteoGeocoder:
    def __init__(self, http_client: JsonHttpClient | None = None) -> None:
        self._http = http_client or UrlLibJsonHttpClient()

    def search(self, query: str, *, limit: int = 8, language: str = "en") -> list[LocationSuggestion]:
        text = (query or "").strip()
        if not text:
            raise WindAutofillLocationError("Enter a ZIP, city/state, or address for autofill.")
        zip_query = _extract_us_zip_query(text)

        data = self._http.get_json(
            OPEN_METEO_GEOCODING_URL,
            params={
                "name": text,
                "count": str(max(1, min(limit, 20))),
                "language": language,
                "format": "json",
                "countryCode": US_COUNTRY_CODE,
            },
        )
        if not isinstance(data, dict):
            raise WindAutofillProviderError("Open-Meteo geocoding response was malformed.")
        raw_results = data.get("results")
        if not isinstance(raw_results, list) or not raw_results:
            return []

        suggestions: list[LocationSuggestion] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            latitude = _as_float(item.get("latitude"))
            longitude = _as_float(item.get("longitude"))
            timezone_name = str(item.get("timezone") or "").strip()
            name = str(item.get("name") or "").strip()
            if latitude is None or longitude is None or not timezone_name or not name:
                continue
            state = str(item.get("admin1") or "").strip()
            country = str(item.get("country_code") or "").strip()
            if country.upper() != US_COUNTRY_CODE:
                continue
            postal = ""
            postcodes = item.get("postcodes")
            if isinstance(postcodes, list) and postcodes:
                normalized_postcodes = [str(code).strip() for code in postcodes if str(code).strip()]
                if zip_query and zip_query in normalized_postcodes:
                    postal = zip_query
                elif normalized_postcodes:
                    postal = normalized_postcodes[0]
            elif isinstance(item.get("postcode"), (str, int)):
                postal = str(item.get("postcode")).strip()
            elif zip_query:
                # If geocoder resolves to a US city but omits postcodes, keep the entered ZIP visible for clarity.
                postal = zip_query

            display_parts = [name]
            if state:
                display_parts.append(state)
            if country:
                display_parts.append(country)
            if postal:
                display_parts.append(postal)
            display_name = ", ".join(display_parts)

            suggestions.append(
                LocationSuggestion(
                    query_text=text,
                    display_name=display_name,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_name=timezone_name,
                    city=name,
                    state=state,
                    postal_code=postal,
                )
            )
        return suggestions


class NwsObservationClient:
    def __init__(self, http_client: JsonHttpClient | None = None, *, station_scan_limit: int = 5) -> None:
        self._http = http_client or UrlLibJsonHttpClient()
        self.station_scan_limit = max(1, station_scan_limit)

    def fetch_rows(
        self, *, latitude: float, longitude: float, start_utc: datetime,
        end_utc: datetime, targets_utc: Sequence[datetime],
        verification_start_utc: datetime, verification_end_utc: datetime,
        local_timezone: ZoneInfo, policy: WeatherMatchPolicy = WeatherMatchPolicy(),
    ) -> tuple[WindAutofillRow, WindAutofillRow]:
        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            raise WindAutofillProviderError("Provider request timestamps must be timezone-aware.")
        stations = self._resolve_stations(latitude, longitude)
        observations: list[dict[str, Any]] = []
        for distance, station_id, station_lat, station_lon in stations[:self.station_scan_limit]:
            if distance > policy.max_distance_miles:
                continue
            for target in dict.fromkeys(targets_utc):
                window = timedelta(minutes=policy.max_time_delta_minutes)
                try:
                    records = self._fetch_station_observations(
                        station_id=station_id, start_utc=target - window, end_utc=target + window)
                except WindAutofillProviderError:
                    continue
                for record in records:
                    record.update(station_id=station_id, distance_miles=distance,
                                  latitude=station_lat, longitude=station_lon)
                    observations.append(record)
        rows = []
        for target in targets_utc:
            observation = _nearest_awc_observation(observations, target, policy=policy)
            if observation is None:
                rows.append(_empty_row())
                continue
            station_id = observation["station_id"]
            # Link to the actual selected record, even if outside the flight's time span.
            source_url = _build_observations_url(
                station_id=station_id,
                start_utc=observation["timestamp"] - timedelta(minutes=1),
                end_utc=observation["timestamp"] + timedelta(minutes=1))
            rows.append(_to_wind_row(observation, station_id, source_url, local_timezone))
        return _require_any_data(rows, "NWS")

    def _resolve_stations(self, latitude: float, longitude: float) -> list[tuple[float, str, float, float]]:
        point = self._http.get_json(f"{NWS_BASE_URL}/points/{latitude:.4f},{longitude:.4f}")
        properties = point.get("properties") if isinstance(point, dict) else None
        if not isinstance(properties, dict):
            raise WindAutofillProviderError("NWS points response was missing 'properties'.")
        stations_url = properties.get("observationStations")
        if not isinstance(stations_url, str) or not stations_url.strip():
            raise WindAutofillProviderError("NWS points response was missing observation station links.")
        payload = self._http.get_json(stations_url)
        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list):
            raise WindAutofillProviderError("NWS stations response was malformed.")
        stations = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties")
            geometry = feature.get("geometry")
            if not isinstance(props, dict) or not isinstance(geometry, dict):
                continue
            coords = geometry.get("coordinates")
            station_id = props.get("stationIdentifier")
            if not isinstance(station_id, str) or not station_id.strip():
                continue
            if not isinstance(coords, list) or len(coords) < 2:
                continue  # Unknown distance is not eligible for automatic matching.
            lon, lat = _as_float(coords[0]), _as_float(coords[1])
            if not _valid_coordinates(lat, lon):
                continue
            stations.append((_haversine_miles(latitude, longitude, lat, lon), station_id.strip(), lat, lon))
        return sorted(stations)

    def _fetch_station_observations(self, *, station_id: str, start_utc: datetime,
                                    end_utc: datetime) -> list[dict[str, Any]]:
        payload = self._http.get_json(
            f"{NWS_BASE_URL}/stations/{station_id}/observations",
            params={"start": _to_utc_iso(start_utc), "end": _to_utc_iso(end_utc), "limit": "500"})
        if not isinstance(payload, dict):
            return []
        features = payload.get("features")
        if not isinstance(features, list):
            return []
        if len(features) >= 500:
            raise WindAutofillProviderError("NWS query reached the provider result limit; narrow the time window.")
        observations = []
        for feature in features:
            props = feature.get("properties") if isinstance(feature, dict) else None
            if not isinstance(props, dict):
                continue
            timestamp = _parse_iso_datetime(props.get("timestamp"))
            if timestamp is not None:
                observations.append({"timestamp": timestamp, **{
                    name: props.get(name) for name in ("temperature", "windDirection", "windSpeed", "windGust")
                }})
        return observations


class OpenMeteoArchiveClient:
    def __init__(self, http_client: JsonHttpClient | None = None) -> None:
        self._http = http_client or UrlLibJsonHttpClient()

    def fetch_rows(
        self,
        *,
        latitude: float,
        longitude: float,
        report_date: date,
        targets_utc: Sequence[datetime],
        local_timezone: ZoneInfo,
        policy: WeatherMatchPolicy = WeatherMatchPolicy(),
    ) -> tuple[WindAutofillRow, WindAutofillRow]:
        window = timedelta(minutes=policy.max_time_delta_minutes)
        params = {
            "latitude": f"{latitude:.5f}",
            "longitude": f"{longitude:.5f}",
            "start_date": (min(targets_utc) - window).astimezone(local_timezone).date().isoformat(),
            "end_date": min((max(targets_utc) + window).astimezone(local_timezone).date(),
                            datetime.now(local_timezone).date()).isoformat(),
            "hourly": "temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m",
            "timezone": local_timezone.key,
            "timeformat": "unixtime",
        }
        try:
            payload = self._http.get_json(OPEN_METEO_ARCHIVE_URL, params=params)
        except WindAutofillProviderError:
            raise
        except Exception as exc:
            raise WindAutofillProviderError(
                f"Open-Meteo archive request failed: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise WindAutofillProviderError("Open-Meteo archive response was malformed.")
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise WindAutofillProviderError("Open-Meteo archive response was missing hourly data.")

        observations = _open_meteo_hourly_observations(hourly=hourly, local_timezone=local_timezone)
        if not observations:
            raise WindAutofillProviderError("Open-Meteo archive returned no observations for selected date.")

        start_target, end_target = targets_utc
        source_url = _build_open_meteo_archive_url(params=params)
        rows = []
        for target in (start_target, end_target):
            observation = _nearest_observation(observations, target, policy=policy)
            if observation is None:
                rows.append(_empty_row())
            else:
                observation.update(latitude=payload.get("latitude"), longitude=payload.get("longitude"),
                                   model="Open-Meteo Best Match (model/reanalysis blend)")
                rows.append(_to_wind_row(observation, "OPEN_METEO_ARCHIVE", source_url, local_timezone))
        return _require_any_data(rows, "Open-Meteo")


class AviationWeatherMetarClient:
    def __init__(self, http_client: JsonHttpClient | None = None, *,
                 max_history_hours: int = 720) -> None:
        self._http = http_client or UrlLibJsonHttpClient()
        self.max_history_hours = max(24, int(max_history_hours))

    def fetch_rows(self, *, latitude: float, longitude: float,
                   targets_utc: Sequence[datetime], local_timezone: ZoneInfo,
                   policy: WeatherMatchPolicy = WeatherMatchPolicy(),
                   ) -> tuple[WindAutofillRow, WindAutofillRow]:
        if len(targets_utc) != 2:
            raise WindAutofillProviderError("AviationWeather METAR requires exactly two target timestamps.")
        now_utc = datetime.now(timezone.utc)
        rows = []
        cache: dict[str, list[dict[str, Any]]] = {}
        for target in targets_utc:
            if now_utc - target > timedelta(hours=self.max_history_hours):
                rows.append(_empty_row())
                continue
            window = timedelta(minutes=policy.max_time_delta_minutes)
            # A fixed end date makes the verification URL reproducible, and a small
            # target window avoids losing older reports behind the API result cap.
            params = {
                "format": "json",
                "date": _to_utc_iso(min(target + window, now_utc)),
                "hours": str(max(1, (2 * policy.max_time_delta_minutes + 59) // 60)),
                "bbox": _bbox_for_radius(latitude=latitude, longitude=longitude,
                                         radius_miles=policy.max_distance_miles),
            }
            url = _build_awc_metar_url(params=params)
            try:
                if url not in cache:
                    payload = self._http.get_json(AWC_METAR_URL, params=params)
                    if isinstance(payload, list) and len(payload) >= 400:
                        raise WindAutofillProviderError("METAR query reached the provider result limit; narrow the search.")
                    cache[url] = _awc_observations(payload=payload, latitude=latitude, longitude=longitude)
                observation = _nearest_awc_observation(cache[url], target, policy=policy)
            except WindAutofillProviderError:
                rows.append(_empty_row())
                continue
            rows.append(_to_wind_row(observation, _as_station_id(observation), url, local_timezone)
                        if observation else _empty_row())
        return _require_any_data(rows, "AviationWeather METAR")


class WindWeatherAutofillService:
    def __init__(self, *, geocoder: OpenMeteoGeocoder | None = None,
                 weather_client: NwsObservationClient | None = None,
                 metar_client: AviationWeatherMetarClient | None = None,
                 archive_client: OpenMeteoArchiveClient | None = None,
                 search_window_hours: int = 2) -> None:
        self.geocoder = geocoder or OpenMeteoGeocoder()
        self.weather_client = weather_client or NwsObservationClient()
        self.metar_client = metar_client or AviationWeatherMetarClient()
        self.archive_client = archive_client or OpenMeteoArchiveClient()
        self.search_window_hours = max(1, search_window_hours)

    def search_locations(self, query: str, *, limit: int = 8) -> list[LocationSuggestion]:
        return self.geocoder.search(query, limit=limit)

    def build_autofill(self, request: WindAutofillRequest) -> WindAutofillResult:
        zone = _resolve_timezone(request.location.timezone_name)
        if not _valid_coordinates(request.location.latitude, request.location.longitude):
            raise WindAutofillLocationError("Selected location coordinates are invalid.")
        start_local = _combine_local(request.report_date, _parse_hhmm(request.start_time_24h), zone)
        end_local = _combine_local(request.report_date, _parse_hhmm(request.end_time_24h), zone)
        if end_local < start_local:
            raise WindAutofillProviderError("End time must be the same as or later than Start time for autofill.")
        targets = (start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc))
        if max(targets) > datetime.now(timezone.utc):
            raise WindAutofillProviderError("Autofill is retrospective; select Start and End times in the past.")
        window = timedelta(minutes=request.policy.max_time_delta_minutes)
        common = dict(latitude=request.location.latitude, longitude=request.location.longitude,
                      targets_utc=targets, local_timezone=zone, policy=request.policy)
        providers = (
            ("NWS", self.weather_client, dict(start_utc=targets[0] - window, end_utc=targets[1] + window,
                verification_start_utc=targets[0], verification_end_utc=targets[1])),
            ("AviationWeather METAR", self.metar_client, {}),
            ("Open-Meteo historical hourly data (estimated)", self.archive_client, dict(report_date=request.report_date)),
        )
        rows = (_empty_row(), _empty_row())
        warnings: list[str] = []
        errors: list[str] = []
        verification_url = None
        for label, client, extra in providers:
            if not any(_row_has_missing_fields(row) for row in rows):
                break
            try:
                candidates = client.fetch_rows(**common, **extra)
            except WindAutofillProviderError as exc:
                errors.append(f"{label}: {exc}")
                warnings.append(f"{label} backfill was unavailable within the selected distance/time limits.")
                continue
            merged = [_merge_row_with_fallback(primary=primary, fallback=fallback)
                      for primary, fallback in zip(rows, candidates)]
            if any(fields for _, fields in merged):
                if all(not _row_has_data(row) for row in rows):
                    if label != "NWS":
                        value_label = "estimates" if client is self.archive_client else "observations"
                        warnings.append(f"Station observations were unavailable; used {label} {value_label}.")
                else:
                    warnings.append(_format_backfill_warning(
                        provider_label=label, start_fields=merged[0][1], end_fields=merged[1][1]))
                verification_url = candidates[0].source_url or candidates[1].source_url or verification_url
            rows = (merged[0][0], merged[1][0])
        if not any(_row_has_data(row) for row in rows):
            raise WindAutofillProviderError(
                "No weather observations were found within the selected distance/time limits. "
                "Manual entries were preserved. " + " | ".join(errors))
        for label, row in zip(("Start", "End"), rows):
            warnings.extend(f"{label}: {warning}" for warning in row.warnings)
            if len(set(row.field_sources.values())) > 1:
                warnings.append(f"{label}: mixed sources/times; review the source for each field.")
            if any(source.kind == "estimated" for source in row.field_sources.values()):
                warnings.append(f"{label}: includes model estimates, not on-site measurements.")
        return WindAutofillResult(request.location, rows[0], rows[1], verification_url,
                                  tuple(dict.fromkeys(warnings)), request=request)


def _resolve_timezone(timezone_name: str) -> ZoneInfo:
    tz_text = (timezone_name or "").strip()
    if not tz_text:
        raise WindAutofillProviderError("Selected location is missing timezone metadata.")
    try:
        return ZoneInfo(tz_text)
    except ZoneInfoNotFoundError as exc:
        raise WindAutofillProviderError(f"Unsupported timezone from location provider: {tz_text}") from exc


def _combine_local(report_date: date, t: time, zone: ZoneInfo) -> datetime:
    naive = datetime.combine(report_date, t)
    local = naive.replace(tzinfo=zone)
    if local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != naive:
        raise WindAutofillProviderError("Selected local time does not exist during the daylight-saving transition.")
    if local.utcoffset() != local.replace(fold=1).utcoffset():
        raise WindAutofillProviderError("Selected local time occurs twice during the daylight-saving transition; enter weather manually.")
    return local


def _parse_hhmm(value: str) -> time:
    text = (value or "").strip()
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError as exc:
        raise WindAutofillProviderError(f"Time '{text}' is invalid. Expected HH:MM format.") from exc


def _to_utc_iso(value: datetime) -> str:
    as_utc = value.astimezone(timezone.utc)
    return as_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_datetime(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _nearest_observation(observations: Sequence[dict[str, Any]], target_utc: datetime,
                         *, policy: WeatherMatchPolicy = WeatherMatchPolicy()) -> dict[str, Any] | None:
    eligible = [obs for obs in observations if _time_is_eligible(obs, target_utc, policy)]
    if not eligible:
        return None
    nearest = min(
        eligible,
        key=lambda obs: (abs((obs["timestamp"] - target_utc).total_seconds()), obs["timestamp"]),
    )
    return nearest


def _to_wind_row(
    observation: dict[str, Any],
    station_id: str | None,
    source_url: str | None,
    local_timezone: ZoneInfo,
) -> WindAutofillRow:
    timestamp_utc = observation["timestamp"]

    direction_degrees = _extract_quant_value(observation.get("windDirection"))
    direction = _degrees_to_compass(direction_degrees)

    speed_mph = _wind_to_mph(observation.get("windSpeed"))
    if speed_mph is not None and not 0 <= speed_mph <= 200:
        speed_mph = None
    if speed_mph == 0 and _extract_quant_value(observation.get("windSpeed")) == 0:
        direction = "CALM"
    elif str(_raw_quant_value(observation.get("windDirection"))).upper() == "VRB":
        direction = "VRB"

    gust_mph = _wind_to_mph(observation.get("windGust"))
    if gust_mph is not None and not 0 <= gust_mph <= 250:
        gust_mph = None

    temp_f = _temp_to_f(observation.get("temperature"))
    if temp_f is not None and not -100 <= temp_f <= 150:
        temp_f = None

    source = WeatherFieldSource(
        provider="Open-Meteo" if station_id == "OPEN_METEO_ARCHIVE" else
                 ("AviationWeather METAR" if source_url and AWC_METAR_URL in source_url else "NWS"),
        kind="estimated" if station_id == "OPEN_METEO_ARCHIVE" else "observed",
        observed_at_utc=timestamp_utc,
        station_id=None if station_id == "OPEN_METEO_ARCHIVE" else station_id,
        source_url=source_url,
        distance_miles=_as_float(observation.get("distance_miles")),
        latitude=_as_float(observation.get("latitude")), longitude=_as_float(observation.get("longitude")),
        model=observation.get("model"),
    )
    values = dict(direction=direction, speed_mph=speed_mph, gust_mph=gust_mph, temp_f=temp_f)
    return WindAutofillRow(
        direction=direction,
        speed_mph=speed_mph,
        gust_mph=gust_mph,
        temp_f=temp_f,
        observed_at_utc=timestamp_utc,
        observed_at_local=timestamp_utc.astimezone(local_timezone),
        station_id=station_id,
        source_url=source_url,
        warnings=tuple(_ROW_MISSING_WARNING_BY_FIELD[name] for name, value in values.items() if value is None),
        field_sources={name: source for name, value in values.items() if value is not None},
    )


def _row_has_missing_fields(row: WindAutofillRow) -> bool:
    return row.direction is None or row.speed_mph is None or row.gust_mph is None or row.temp_f is None


def _row_has_data(row: WindAutofillRow) -> bool:
    return any(getattr(row, name) is not None for name in _ROW_FIELD_LABELS)


def _empty_row() -> WindAutofillRow:
    return WindAutofillRow(None, None, None, None, None, None, None, None,
                           tuple(_ROW_MISSING_WARNING_BY_FIELD.values()))


def _require_any_data(rows: Sequence[WindAutofillRow], provider: str) -> tuple[WindAutofillRow, WindAutofillRow]:
    if len(rows) != 2 or not any(_row_has_data(row) for row in rows):
        raise WindAutofillProviderError(f"{provider} returned no eligible observations within the selected limits.")
    return rows[0], rows[1]


def _valid_coordinates(latitude: float | None, longitude: float | None) -> bool:
    return (latitude is not None and longitude is not None and isfinite(latitude) and isfinite(longitude)
            and -90 <= latitude <= 90 and -180 <= longitude <= 180)


def _time_is_eligible(obs: Mapping[str, Any], target: datetime, policy: WeatherMatchPolicy) -> bool:
    timestamp = obs.get("timestamp")
    return (isinstance(timestamp, datetime) and timestamp.tzinfo is not None
            and timestamp <= datetime.now(timezone.utc)
            and abs((timestamp - target).total_seconds()) <= policy.max_time_delta_minutes * 60)


def _merge_row_with_fallback(
    *,
    primary: WindAutofillRow,
    fallback: WindAutofillRow,
) -> tuple[WindAutofillRow, tuple[str, ...]]:
    backfilled_fields: list[str] = []

    direction = primary.direction
    if direction is None and fallback.direction is not None:
        direction = fallback.direction
        backfilled_fields.append("direction")

    speed_mph = primary.speed_mph
    if speed_mph is None and fallback.speed_mph is not None:
        speed_mph = fallback.speed_mph
        backfilled_fields.append("speed_mph")

    gust_mph = primary.gust_mph
    if gust_mph is None and fallback.gust_mph is not None:
        gust_mph = fallback.gust_mph
        backfilled_fields.append("gust_mph")

    temp_f = primary.temp_f
    if temp_f is None and fallback.temp_f is not None:
        temp_f = fallback.temp_f
        backfilled_fields.append("temp_f")

    resolved_warnings = list(primary.warnings)
    if backfilled_fields:
        resolved_missing_warnings = {
            _ROW_MISSING_WARNING_BY_FIELD[field_name] for field_name in backfilled_fields
        }
        resolved_warnings = [
            warning for warning in resolved_warnings if warning not in resolved_missing_warnings
        ]

    sources = dict(primary.field_sources)
    for name in backfilled_fields:
        if name in fallback.field_sources:
            sources[name] = fallback.field_sources[name]
    base = primary if _row_has_data(primary) else fallback
    mixed = bool(backfilled_fields) and _row_has_data(primary) and (
        len(set(sources.values())) > 1 or (primary.station_id, primary.observed_at_utc, primary.source_url)
        != (fallback.station_id, fallback.observed_at_utc, fallback.source_url))
    merged_row = replace(
        base,
        direction=direction,
        speed_mph=speed_mph,
        gust_mph=gust_mph,
        temp_f=temp_f,
        warnings=tuple(resolved_warnings),
        field_sources=sources,
        observed_at_utc=None if mixed else base.observed_at_utc,
        observed_at_local=None if mixed else base.observed_at_local,
        station_id=None if mixed else base.station_id,
        source_url=None if mixed else base.source_url,
    )
    return merged_row, tuple(backfilled_fields)


def _format_backfill_warning(
    *,
    provider_label: str,
    start_fields: Sequence[str],
    end_fields: Sequence[str],
) -> str:
    start_labels = ", ".join(_ROW_FIELD_LABELS[field_name] for field_name in start_fields) or "none"
    end_labels = ", ".join(_ROW_FIELD_LABELS[field_name] for field_name in end_fields) or "none"
    return (
        f"Filled missing values from {provider_label}. "
        f"Start[{start_labels}] End[{end_labels}]."
    )


def _bbox_for_radius(*, latitude: float, longitude: float, radius_miles: float) -> str:
    lat_delta = max(0.05, radius_miles / 69.0)
    lat_radians = radians(latitude)
    lon_factor = max(0.1, abs(cos(lat_radians)))
    lon_delta = max(0.05, radius_miles / (69.0 * lon_factor))
    min_lat = max(-90.0, latitude - lat_delta)
    max_lat = min(90.0, latitude + lat_delta)
    min_lon = max(-180.0, longitude - lon_delta)
    max_lon = min(180.0, longitude + lon_delta)
    return f"{min_lat:.4f},{min_lon:.4f},{max_lat:.4f},{max_lon:.4f}"


def _awc_observations(*, payload: Any, latitude: float, longitude: float) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise WindAutofillProviderError("AviationWeather METAR response was malformed.")

    observations: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        timestamp = _parse_awc_timestamp(item.get("obsTime"), item.get("reportTime"))
        if timestamp is None:
            continue
        station_lat = _as_float(item.get("lat"))
        station_lon = _as_float(item.get("lon"))
        if not _valid_coordinates(station_lat, station_lon):
            continue
        distance_miles = _haversine_miles(latitude, longitude, station_lat, station_lon)
        observations.append(
            {
                "timestamp": timestamp,
                "temperature": {"value": item.get("temp"), "unitCode": "wmoUnit:degC"},
                "windDirection": {"value": item.get("wdir"), "unitCode": "wmoUnit:degree_(angle)"},
                "windSpeed": {"value": item.get("wspd"), "unitCode": "wmoUnit:kt"},
                "windGust": {"value": item.get("wgst"), "unitCode": "wmoUnit:kt"},
                "station_id": str(item.get("icaoId") or "").strip() or None,
                "distance_miles": distance_miles,
                "latitude": station_lat,
                "longitude": station_lon,
            }
        )
    observations.sort(key=lambda item: item["timestamp"])
    return observations


def _parse_awc_timestamp(obs_time_raw: Any, report_time_raw: Any) -> datetime | None:
    if isinstance(obs_time_raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(obs_time_raw), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            pass
    if isinstance(obs_time_raw, str):
        as_float = _as_float(obs_time_raw)
        if as_float is not None:
            try:
                return datetime.fromtimestamp(as_float, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                pass
    return _parse_iso_datetime(report_time_raw)


def _nearest_awc_observation(
    observations: Sequence[dict[str, Any]],
    target_utc: datetime,
    *, policy: WeatherMatchPolicy = WeatherMatchPolicy(),
) -> dict[str, Any] | None:
    eligible = [obs for obs in observations
                if _time_is_eligible(obs, target_utc, policy)
                and _as_float(obs.get("distance_miles")) is not None
                and 0 <= float(obs["distance_miles"]) <= policy.max_distance_miles]
    if not eligible:
        return None
    nearest = min(eligible, key=lambda obs: (_awc_score(obs=obs, target_utc=target_utc),
                                           obs["timestamp"], str(obs.get("station_id", ""))))
    return nearest


def _awc_score(*, obs: dict[str, Any], target_utc: datetime) -> float:
    timestamp = obs.get("timestamp")
    if not isinstance(timestamp, datetime):
        return float("inf")
    time_seconds = abs((timestamp - target_utc).total_seconds())
    distance_miles = _as_float(obs.get("distance_miles"))
    if distance_miles is None:
        return float("inf")
    # 1 mile ~= 60 seconds score weight to balance time and distance.
    return time_seconds + (distance_miles * 60.0)


def _as_station_id(observation: Mapping[str, Any]) -> str | None:
    raw = observation.get("station_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.7613
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_r = radians(lat1)
    lat2_r = radians(lat2)
    a = sin(d_lat / 2.0) ** 2 + cos(lat1_r) * cos(lat2_r) * (sin(d_lon / 2.0) ** 2)
    c = 2.0 * asin(min(1.0, sqrt(max(0.0, a))))
    return radius_miles * c


def _raw_quant_value(raw: Any) -> Any:
    if not isinstance(raw, dict) or raw.get("qualityControl") in {"X", "Z"}:
        return None
    return raw.get("value")


def _extract_quant_value(raw: Any) -> float | None:
    if not isinstance(raw, dict):
        return None
    value = _as_float(_raw_quant_value(raw))
    return value


def _wind_to_mph(raw: Any) -> int | None:
    if not isinstance(raw, dict):
        return None
    value = _as_float(_raw_quant_value(raw))
    if value is None:
        return None
    unit = str(raw.get("unitCode") or "").lower()
    if "m_s" in unit:
        converted = value * 2.2369362920544
    elif "km_h" in unit or "kmh" in unit:
        converted = value * 0.62137119223733
    elif "kt" in unit or "knot" in unit:
        converted = value * 1.1507794480235
    elif "mi_h" in unit or "mph" in unit:
        converted = value
    else:
        # Unknown unit for this field; safer to leave unresolved.
        return None
    return int(round(converted))


def _temp_to_f(raw: Any) -> int | None:
    if not isinstance(raw, dict):
        return None
    value = _as_float(_raw_quant_value(raw))
    if value is None:
        return None
    unit = str(raw.get("unitCode") or "").lower()
    if "degc" in unit:
        converted = (value * 9.0 / 5.0) + 32.0
    elif "degf" in unit:
        converted = value
    else:
        return None
    return int(round(converted))


def _degrees_to_compass(value: float | None) -> str | None:
    if value is None or not 0 <= value <= 360:
        return None
    normalized = value % 360.0
    directions = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )
    index = int((normalized + 11.25) / 22.5) % 16
    return directions[index]


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        candidate = float(value)
        if not isfinite(candidate):
            return None
        return candidate
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            candidate = float(text)
        except ValueError:
            return None
        if not isfinite(candidate):
            return None
        return candidate
    return None


def _extract_us_zip_query(text: str) -> str | None:
    compact = "".join(ch for ch in text if ch.isdigit())
    if len(compact) == 5:
        return compact
    return None


def _build_observations_url(*, station_id: str, start_utc: datetime, end_utc: datetime) -> str:
    params = urlencode(
        {
            "start": _to_utc_iso(start_utc),
            "end": _to_utc_iso(end_utc),
        }
    )
    return f"{NWS_BASE_URL}/stations/{station_id}/observations?{params}"


def _build_awc_metar_url(*, params: Mapping[str, str]) -> str:
    encoded = urlencode(dict(params))
    return f"{AWC_METAR_URL}?{encoded}"


def _open_meteo_hourly_observations(*, hourly: Mapping[str, Any], local_timezone: ZoneInfo) -> list[dict[str, Any]]:
    raw_times = hourly.get("time")
    if not isinstance(raw_times, list):
        return []

    temp_values = _sequence_or_none(hourly.get("temperature_2m"))
    speed_values = _sequence_or_none(hourly.get("wind_speed_10m"))
    gust_values = _sequence_or_none(hourly.get("wind_gusts_10m"))
    direction_values = _sequence_or_none(hourly.get("wind_direction_10m"))

    observations: list[dict[str, Any]] = []
    for idx, raw_time in enumerate(raw_times):
        if isinstance(raw_time, (int, float)) and not isinstance(raw_time, bool):
            try:
                timestamp_utc = datetime.fromtimestamp(raw_time, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
        elif isinstance(raw_time, str) and raw_time.strip():
            try:
                local_naive = datetime.fromisoformat(raw_time.strip())
                local_aware = _combine_local(local_naive.date(), local_naive.time(), local_timezone)
                timestamp_utc = local_aware.astimezone(timezone.utc)
            except (ValueError, WindAutofillProviderError):
                continue
        else:
            continue
        observations.append(
            {
                "timestamp": timestamp_utc,
                "temperature": _open_meteo_quant(temp_values, idx, "wmoUnit:degC"),
                "windDirection": _open_meteo_quant(direction_values, idx, "wmoUnit:degree_(angle)"),
                "windSpeed": _open_meteo_quant(speed_values, idx, "wmoUnit:km_h-1"),
                "windGust": _open_meteo_quant(gust_values, idx, "wmoUnit:km_h-1"),
            }
        )

    observations.sort(key=lambda item: item["timestamp"])
    return observations


def _sequence_or_none(value: Any) -> Sequence[Any] | None:
    if isinstance(value, list):
        return value
    return None


def _open_meteo_quant(values: Sequence[Any] | None, index: int, unit_code: str) -> dict[str, Any]:
    value: Any = None
    if values is not None and 0 <= index < len(values):
        value = values[index]
    return {"value": value, "unitCode": unit_code}


def _build_open_meteo_archive_url(*, params: Mapping[str, str]) -> str:
    encoded = urlencode(dict(params))
    return f"{OPEN_METEO_ARCHIVE_URL}?{encoded}"
