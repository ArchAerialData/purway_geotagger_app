from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
import json
from math import asin
from math import cos
from math import isnan
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
        if not isinstance(payload, dict):
            return []
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
        if not isinstance(payload, dict):
            raise WindAutofillProviderError("Open-Meteo archive response was malformed.")
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


class AviationWeatherMetarClient:
    def __init__(
        self,
        http_client: JsonHttpClient | None = None,
        *,
        radius_miles_steps: Sequence[float] = (25.0, 80.0, 160.0),
        max_history_hours: int = 720,
        minimum_hours: int = 6,
    ) -> None:
        self._http = http_client or UrlLibJsonHttpClient()
        steps = [float(step) for step in radius_miles_steps if float(step) > 0.0]
        self.radius_miles_steps = tuple(steps) if steps else (80.0,)
        self.max_history_hours = max(24, int(max_history_hours))
        self.minimum_hours = max(1, int(minimum_hours))

    def fetch_rows(
        self,
        *,
        latitude: float,
        longitude: float,
        targets_utc: Sequence[datetime],
        local_timezone: ZoneInfo,
    ) -> tuple[WindAutofillRow, WindAutofillRow]:
        if len(targets_utc) != 2:
            raise WindAutofillProviderError("AviationWeather METAR requires exactly two target timestamps.")
        start_target, end_target = targets_utc
        required_hours = _required_history_hours(
            now_utc=datetime.now(timezone.utc),
            oldest_target_utc=min(start_target, end_target),
            minimum_hours=self.minimum_hours,
        )
        if required_hours > self.max_history_hours:
            raise WindAutofillProviderError(
                "AviationWeather METAR history is limited to recent days; selected timestamps are too old."
            )
        hours_text = str(min(required_hours, self.max_history_hours))

        last_error: WindAutofillProviderError | None = None
        for radius_miles in self.radius_miles_steps:
            params = {
                "format": "json",
                "hours": hours_text,
                "bbox": _bbox_for_radius(latitude=latitude, longitude=longitude, radius_miles=radius_miles),
            }
            try:
                payload = self._http.get_json(AWC_METAR_URL, params=params)
            except WindAutofillProviderError as exc:
                last_error = exc
                continue
            except Exception as exc:
                last_error = WindAutofillProviderError(f"AviationWeather METAR request failed: {exc}")
                continue

            observations = _awc_observations(payload=payload, latitude=latitude, longitude=longitude)
            if not observations:
                continue

            start_observation = _nearest_awc_observation(observations, start_target)
            end_observation = _nearest_awc_observation(observations, end_target)
            if start_observation is None or end_observation is None:
                continue

            source_url = _build_awc_metar_url(params=params)
            start_row = _to_wind_row(
                start_observation,
                _as_station_id(start_observation),
                source_url,
                local_timezone,
            )
            end_row = _to_wind_row(
                end_observation,
                _as_station_id(end_observation),
                source_url,
                local_timezone,
            )
            return start_row, end_row

        if last_error is not None:
            raise WindAutofillProviderError(
                "AviationWeather METAR observations were unavailable for selected location/times."
            ) from last_error
        raise WindAutofillProviderError("AviationWeather METAR returned no observations for selected location/times.")


class WindWeatherAutofillService:
    def __init__(
        self,
        *,
        geocoder: OpenMeteoGeocoder | None = None,
        weather_client: NwsObservationClient | None = None,
        metar_client: AviationWeatherMetarClient | None = None,
        archive_client: OpenMeteoArchiveClient | None = None,
        search_window_hours: int = 2,
    ) -> None:
        self.geocoder = geocoder or OpenMeteoGeocoder()
        self.weather_client = weather_client or NwsObservationClient()
        self.metar_client = metar_client or AviationWeatherMetarClient()
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
        verification_url: str | None = None
        primary_provider = ""
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
            verification_url = start_row.source_url or end_row.source_url
            primary_provider = "NWS"
        except WindAutofillProviderError as nws_error:
            try:
                start_row, end_row = self.metar_client.fetch_rows(
                    latitude=request.location.latitude,
                    longitude=request.location.longitude,
                    targets_utc=(start_utc, end_utc),
                    local_timezone=zone,
                )
                provider_warnings.append(
                    "NWS station observations were unavailable for selected date/times; used AviationWeather METAR observations."
                )
                verification_url = start_row.source_url or end_row.source_url
                primary_provider = "AWC"
            except WindAutofillProviderError as metar_error:
                try:
                    start_row, end_row = self.archive_client.fetch_rows(
                        latitude=request.location.latitude,
                        longitude=request.location.longitude,
                        report_date=request.report_date,
                        targets_utc=(start_utc, end_utc),
                        local_timezone=zone,
                    )
                    provider_warnings.append(
                        "NWS and AviationWeather METAR observations were unavailable; used Open-Meteo historical hourly data."
                    )
                    verification_url = start_row.source_url or end_row.source_url
                    primary_provider = "OPEN_METEO_ARCHIVE"
                except WindAutofillProviderError as archive_error:
                    report_date_text = request.report_date.isoformat()
                    raise WindAutofillProviderError(
                        "No weather observations were found for the selected times. "
                        f"NWS observations may only retain recent history for {report_date_text}. "
                        f"NWS error: {nws_error}. METAR fallback error: {metar_error}. Historical fallback error: {archive_error}."
                    ) from archive_error
        else:
            if _row_has_missing_fields(start_row) or _row_has_missing_fields(end_row):
                metar_warning_added = False
                if primary_provider != "AWC":
                    try:
                        metar_start_row, metar_end_row = self.metar_client.fetch_rows(
                            latitude=request.location.latitude,
                            longitude=request.location.longitude,
                            targets_utc=(start_utc, end_utc),
                            local_timezone=zone,
                        )
                    except WindAutofillProviderError:
                        provider_warnings.append(
                            "NWS observations were partial and AviationWeather METAR backfill was unavailable."
                        )
                        metar_warning_added = True
                    else:
                        start_row, start_backfilled = _merge_row_with_fallback(
                            primary=start_row,
                            fallback=metar_start_row,
                        )
                        end_row, end_backfilled = _merge_row_with_fallback(
                            primary=end_row,
                            fallback=metar_end_row,
                        )
                        if start_backfilled or end_backfilled:
                            provider_warnings.append(
                                _format_backfill_warning(
                                    provider_label="AviationWeather METAR",
                                    start_fields=start_backfilled,
                                    end_fields=end_backfilled,
                                )
                            )
                            verification_url = (
                                metar_start_row.source_url or metar_end_row.source_url or verification_url
                            )

                if _row_has_missing_fields(start_row) or _row_has_missing_fields(end_row):
                    if primary_provider == "AWC" and not metar_warning_added:
                        provider_warnings.append(
                            "AviationWeather METAR observations were partial; trying Open-Meteo backfill."
                        )
                    try:
                        archive_start_row, archive_end_row = self.archive_client.fetch_rows(
                            latitude=request.location.latitude,
                            longitude=request.location.longitude,
                            report_date=request.report_date,
                            targets_utc=(start_utc, end_utc),
                            local_timezone=zone,
                        )
                    except WindAutofillProviderError:
                        provider_warnings.append(
                            "Observations were partial and Open-Meteo backfill was unavailable; "
                            "some fields may remain missing."
                        )
                    else:
                        start_row, start_backfilled = _merge_row_with_fallback(
                            primary=start_row,
                            fallback=archive_start_row,
                        )
                        end_row, end_backfilled = _merge_row_with_fallback(
                            primary=end_row,
                            fallback=archive_end_row,
                        )
                        if start_backfilled or end_backfilled:
                            provider_warnings.append(
                                _format_backfill_warning(
                                    provider_label="Open-Meteo historical hourly data",
                                    start_fields=start_backfilled,
                                    end_fields=end_backfilled,
                                )
                            )
                            verification_url = (
                                archive_start_row.source_url or archive_end_row.source_url or verification_url
                            )

        warnings = tuple(provider_warnings + list(start_row.warnings) + list(end_row.warnings))
        return WindAutofillResult(
            location=request.location,
            start=start_row,
            end=end_row,
            verification_url=verification_url or start_row.source_url or end_row.source_url,
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


def _row_has_missing_fields(row: WindAutofillRow) -> bool:
    return row.direction is None or row.speed_mph is None or row.gust_mph is None or row.temp_f is None


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

    merged_row = replace(
        primary,
        direction=direction,
        speed_mph=speed_mph,
        gust_mph=gust_mph,
        temp_f=temp_f,
        warnings=tuple(resolved_warnings),
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


def _required_history_hours(*, now_utc: datetime, oldest_target_utc: datetime, minimum_hours: int) -> int:
    delta = now_utc - oldest_target_utc
    total_seconds = max(0.0, delta.total_seconds())
    raw_hours = int(total_seconds // 3600) + 3
    return max(minimum_hours, raw_hours)


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
        if station_lat is None or station_lon is None:
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
) -> dict[str, Any] | None:
    if not observations:
        return None
    nearest = min(observations, key=lambda obs: _awc_score(obs=obs, target_utc=target_utc))
    return nearest


def _awc_score(*, obs: dict[str, Any], target_utc: datetime) -> float:
    timestamp = obs.get("timestamp")
    if not isinstance(timestamp, datetime):
        return float("inf")
    time_seconds = abs((timestamp - target_utc).total_seconds())
    distance_miles = _as_float(obs.get("distance_miles")) or 9999.0
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
