from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import json
from math import isnan
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


NWS_BASE_URL = "https://api.weather.gov"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
US_COUNTRY_CODE = "US"


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


@dataclass(frozen=True)
class WindAutofillRequest:
    location: LocationSuggestion
    report_date: date
    start_time_24h: str
    end_time_24h: str


@dataclass(frozen=True)
class WindAutofillResult:
    location: LocationSuggestion
    start: WindAutofillRow
    end: WindAutofillRow
    verification_url: str | None
    warnings: tuple[str, ...]


class JsonHttpClient:
    """Small interface to keep provider calls mockable and deterministic in tests."""

    def get_json(self, url: str, params: Mapping[str, str] | None = None) -> dict[str, Any]:
        raise NotImplementedError


class UrlLibJsonHttpClient(JsonHttpClient):
    def __init__(self, *, timeout_seconds: float = 10.0, user_agent: str = "purway-geotagger/1.0") -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def get_json(self, url: str, params: Mapping[str, str] | None = None) -> dict[str, Any]:
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
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise WindAutofillProviderError(f"Weather API request failed: {exc}") from exc

        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WindAutofillProviderError("Weather API returned invalid JSON.") from exc
        if not isinstance(parsed, dict):
            raise WindAutofillProviderError("Weather API returned an unexpected response shape.")
        return parsed


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
        self,
        *,
        latitude: float,
        longitude: float,
        start_utc: datetime,
        end_utc: datetime,
        targets_utc: Sequence[datetime],
        verification_start_utc: datetime,
        verification_end_utc: datetime,
        local_timezone: ZoneInfo,
    ) -> tuple[WindAutofillRow, WindAutofillRow]:
        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            raise WindAutofillProviderError("Provider request timestamps must be timezone-aware.")

        stations = self._resolve_station_ids(latitude, longitude)
        if not stations:
            raise WindAutofillProviderError("No nearby weather stations were found for the selected location.")

        observations: list[dict[str, Any]] = []
        station_id_used: str | None = None
        for station_id in stations[: self.station_scan_limit]:
            observations = self._fetch_station_observations(station_id=station_id, start_utc=start_utc, end_utc=end_utc)
            if observations:
                station_id_used = station_id
                break

        if not observations:
            raise WindAutofillProviderError("No weather observations were found for the selected times.")

        start_target, end_target = targets_utc
        start_observation = _nearest_observation(observations, start_target)
        end_observation = _nearest_observation(observations, end_target)
        if start_observation is None or end_observation is None:
            raise WindAutofillProviderError("Could not map observations to both Start and End times.")

        source_url = None
        if station_id_used:
            source_url = _build_observations_url(
                station_id=station_id_used,
                start_utc=verification_start_utc,
                end_utc=verification_end_utc,
            )

        start_row = _to_wind_row(start_observation, station_id_used, source_url, local_timezone)
        end_row = _to_wind_row(end_observation, station_id_used, source_url, local_timezone)
        return start_row, end_row

    def _resolve_station_ids(self, latitude: float, longitude: float) -> list[str]:
        point = self._http.get_json(f"{NWS_BASE_URL}/points/{latitude:.4f},{longitude:.4f}")
        properties = point.get("properties")
        if not isinstance(properties, dict):
            raise WindAutofillProviderError("NWS points response was missing 'properties'.")

        stations_url = properties.get("observationStations")
        if not isinstance(stations_url, str) or not stations_url.strip():
            raise WindAutofillProviderError("NWS points response was missing observation station links.")

        stations_json = self._http.get_json(stations_url)
        features = stations_json.get("features")
        if not isinstance(features, list):
            raise WindAutofillProviderError("NWS stations response was malformed.")

        identifiers: list[str] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties")
            if not isinstance(props, dict):
                continue
            raw = props.get("stationIdentifier")
            if isinstance(raw, str) and raw.strip():
                identifiers.append(raw.strip())
        return identifiers

    def _fetch_station_observations(
        self,
        *,
        station_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[dict[str, Any]]:
        payload = self._http.get_json(
            f"{NWS_BASE_URL}/stations/{station_id}/observations",
            params={
                "start": _to_utc_iso(start_utc),
                "end": _to_utc_iso(end_utc),
            },
        )
        features = payload.get("features")
        if not isinstance(features, list):
            return []

        observations: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                continue
            timestamp_raw = properties.get("timestamp")
            timestamp = _parse_iso_datetime(timestamp_raw)
            if timestamp is None:
                continue
            observations.append(
                {
                    "timestamp": timestamp,
                    "temperature": properties.get("temperature"),
                    "windDirection": properties.get("windDirection"),
                    "windSpeed": properties.get("windSpeed"),
                    "windGust": properties.get("windGust"),
                }
            )
        observations.sort(key=lambda item: item["timestamp"])
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
    ) -> tuple[WindAutofillRow, WindAutofillRow]:
        report_date_text = report_date.isoformat()
        params = {
            "latitude": f"{latitude:.5f}",
            "longitude": f"{longitude:.5f}",
            "start_date": report_date_text,
            "end_date": report_date_text,
            "hourly": "temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m",
            "timezone": local_timezone.key,
        }
        try:
            payload = self._http.get_json(OPEN_METEO_ARCHIVE_URL, params=params)
        except WindAutofillProviderError:
            raise
        except Exception as exc:
            raise WindAutofillProviderError(
                f"Open-Meteo archive request failed: {exc}"
            ) from exc
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise WindAutofillProviderError("Open-Meteo archive response was missing hourly data.")

        observations = _open_meteo_hourly_observations(hourly=hourly, local_timezone=local_timezone)
        if not observations:
            raise WindAutofillProviderError("Open-Meteo archive returned no observations for selected date.")

        start_target, end_target = targets_utc
        start_observation = _nearest_observation(observations, start_target)
        end_observation = _nearest_observation(observations, end_target)
        if start_observation is None or end_observation is None:
            raise WindAutofillProviderError("Could not map Open-Meteo hourly observations to selected times.")

        source_url = _build_open_meteo_archive_url(params=params)
        start_row = _to_wind_row(
            start_observation,
            "OPEN_METEO_ARCHIVE",
            source_url,
            local_timezone,
        )
        end_row = _to_wind_row(
            end_observation,
            "OPEN_METEO_ARCHIVE",
            source_url,
            local_timezone,
        )
        return start_row, end_row


class WindWeatherAutofillService:
    def __init__(
        self,
        *,
        geocoder: OpenMeteoGeocoder | None = None,
        weather_client: NwsObservationClient | None = None,
        archive_client: OpenMeteoArchiveClient | None = None,
        search_window_hours: int = 2,
    ) -> None:
        self.geocoder = geocoder or OpenMeteoGeocoder()
        self.weather_client = weather_client or NwsObservationClient()
        self.archive_client = archive_client or OpenMeteoArchiveClient()
        self.search_window_hours = max(1, search_window_hours)

    def search_locations(self, query: str, *, limit: int = 8) -> list[LocationSuggestion]:
        return self.geocoder.search(query, limit=limit)

    def build_autofill(self, request: WindAutofillRequest) -> WindAutofillResult:
        zone = _resolve_timezone(request.location.timezone_name)
        start_local = _combine_local(request.report_date, _parse_hhmm(request.start_time_24h), zone)
        end_local = _combine_local(request.report_date, _parse_hhmm(request.end_time_24h), zone)
        if end_local < start_local:
            raise WindAutofillProviderError("End time must be the same as or later than Start time for autofill.")

        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        span_start = start_utc - timedelta(hours=self.search_window_hours)
        span_end = end_utc + timedelta(hours=self.search_window_hours)

        provider_warnings: list[str] = []
        try:
            start_row, end_row = self.weather_client.fetch_rows(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                start_utc=span_start,
                end_utc=span_end,
                targets_utc=(start_utc, end_utc),
                verification_start_utc=start_utc,
                verification_end_utc=end_utc,
                local_timezone=zone,
            )
        except WindAutofillProviderError as nws_error:
            try:
                start_row, end_row = self.archive_client.fetch_rows(
                    latitude=request.location.latitude,
                    longitude=request.location.longitude,
                    report_date=request.report_date,
                    targets_utc=(start_utc, end_utc),
                    local_timezone=zone,
                )
                provider_warnings.append(
                    "NWS station observations were unavailable for selected date/times; used Open-Meteo historical hourly data."
                )
            except WindAutofillProviderError as archive_error:
                report_date_text = request.report_date.isoformat()
                raise WindAutofillProviderError(
                    "No weather observations were found for the selected times. "
                    f"NWS observations may only retain recent history for {report_date_text}. "
                    f"NWS error: {nws_error}. Historical fallback error: {archive_error}."
                ) from archive_error

        warnings = tuple(provider_warnings + list(start_row.warnings) + list(end_row.warnings))
        return WindAutofillResult(
            location=request.location,
            start=start_row,
            end=end_row,
            verification_url=start_row.source_url or end_row.source_url,
            warnings=warnings,
        )


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
    return naive.replace(tzinfo=zone)


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


def _nearest_observation(observations: Sequence[dict[str, Any]], target_utc: datetime) -> dict[str, Any] | None:
    if not observations:
        return None
    nearest = min(
        observations,
        key=lambda obs: abs((obs["timestamp"] - target_utc).total_seconds()),
    )
    return nearest


def _to_wind_row(
    observation: dict[str, Any],
    station_id: str | None,
    source_url: str | None,
    local_timezone: ZoneInfo,
) -> WindAutofillRow:
    timestamp_utc = observation["timestamp"]
    warnings: list[str] = []

    direction_degrees = _extract_quant_value(observation.get("windDirection"))
    direction = _degrees_to_compass(direction_degrees)
    if direction is None:
        warnings.append("Wind direction not reported for selected timestamp.")

    speed_mph = _wind_to_mph(observation.get("windSpeed"))
    if speed_mph is None:
        warnings.append("Wind speed not reported for selected timestamp.")

    gust_mph = _wind_to_mph(observation.get("windGust"))
    if gust_mph is None:
        warnings.append("Wind gust not reported for selected timestamp.")

    temp_f = _temp_to_f(observation.get("temperature"))
    if temp_f is None:
        warnings.append("Temperature not reported for selected timestamp.")

    return WindAutofillRow(
        direction=direction,
        speed_mph=speed_mph,
        gust_mph=gust_mph,
        temp_f=temp_f,
        observed_at_utc=timestamp_utc,
        observed_at_local=timestamp_utc.astimezone(local_timezone),
        station_id=station_id,
        source_url=source_url,
        warnings=tuple(warnings),
    )


def _extract_quant_value(raw: Any) -> float | None:
    if not isinstance(raw, dict):
        return None
    value = _as_float(raw.get("value"))
    return value


def _wind_to_mph(raw: Any) -> int | None:
    if not isinstance(raw, dict):
        return None
    value = _as_float(raw.get("value"))
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
    value = _as_float(raw.get("value"))
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
    if value is None:
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
        if isnan(candidate):
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
        if isnan(candidate):
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
        if not isinstance(raw_time, str) or not raw_time.strip():
            continue
        try:
            local_naive = datetime.fromisoformat(raw_time.strip())
        except ValueError:
            continue
        local_aware = local_naive.replace(tzinfo=local_timezone)
        timestamp_utc = local_aware.astimezone(timezone.utc)
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
