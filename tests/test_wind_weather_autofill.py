from __future__ import annotations

from datetime import date

import pytest

from purway_geotagger.core.wind_weather_autofill import (
    NWS_BASE_URL,
    OPEN_METEO_GEOCODING_URL,
    JsonHttpClient,
    LocationSuggestion,
    NwsObservationClient,
    OpenMeteoGeocoder,
    WindAutofillLocationError,
    WindAutofillProviderError,
    WindAutofillRequest,
    WindWeatherAutofillService,
)


class FakeJsonHttpClient(JsonHttpClient):
    def __init__(self, responses: dict[tuple[str, tuple[tuple[str, str], ...]] | str, object]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get_json(self, url: str, params: dict[str, str] | None = None) -> dict:
        normalized_params = dict(params or {})
        self.calls.append((url, normalized_params))
        keyed = (url, tuple(sorted(normalized_params.items())))
        if keyed in self.responses:
            result = self.responses[keyed]
        elif url in self.responses:
            result = self.responses[url]
        else:
            raise AssertionError(f"No fake response configured for: {url} {normalized_params}")
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, dict)
        return result


def _location() -> LocationSuggestion:
    return LocationSuggestion(
        query_text="77002",
        display_name="Houston, Texas, US, 77002",
        latitude=29.7604,
        longitude=-95.3698,
        timezone_name="America/Chicago",
        city="Houston",
        state="Texas",
        postal_code="77002",
    )


def _nws_success_responses() -> dict[tuple[str, tuple[tuple[str, str], ...]] | str, object]:
    return {
        f"{NWS_BASE_URL}/points/29.7604,-95.3698": {
            "properties": {
                "observationStations": f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations",
            }
        },
        f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations": {
            "features": [
                {"properties": {"stationIdentifier": "KHOU"}},
            ]
        },
        f"{NWS_BASE_URL}/stations/KHOU/observations": {
            "features": [
                {
                    "properties": {
                        "timestamp": "2026-02-06T19:00:00+00:00",
                        "windDirection": {"value": 200.0, "unitCode": "wmoUnit:degree_(angle)"},
                        "windSpeed": {"value": 4.4704, "unitCode": "wmoUnit:m_s-1"},
                        "windGust": {"value": 8.9408, "unitCode": "wmoUnit:m_s-1"},
                        "temperature": {"value": 11.0, "unitCode": "wmoUnit:degC"},
                    }
                },
                {
                    "properties": {
                        "timestamp": "2026-02-06T23:00:00+00:00",
                        "windDirection": {"value": 335.0, "unitCode": "wmoUnit:degree_(angle)"},
                        "windSpeed": {"value": 5.36448, "unitCode": "wmoUnit:m_s-1"},
                        "windGust": {"value": 10.729, "unitCode": "wmoUnit:m_s-1"},
                        "temperature": {"value": 13.0, "unitCode": "wmoUnit:degC"},
                    }
                },
            ]
        },
    }


def test_open_meteo_search_returns_us_only_and_prefers_typed_zip() -> None:
    fake_http = FakeJsonHttpClient(
        {
            OPEN_METEO_GEOCODING_URL: {
                "results": [
                    {
                        "name": "Houston",
                        "latitude": 29.7604,
                        "longitude": -95.3698,
                        "timezone": "America/Chicago",
                        "admin1": "Texas",
                        "country_code": "US",
                        "postcodes": ["77001", "77008", "77003"],
                    },
                    {
                        "name": "Melun",
                        "latitude": 48.5395,
                        "longitude": 2.6609,
                        "timezone": "Europe/Paris",
                        "admin1": "ile-de-France",
                        "country_code": "FR",
                        "postcodes": ["77000"],
                    }
                ]
            }
        }
    )
    geocoder = OpenMeteoGeocoder(http_client=fake_http)
    results = geocoder.search("77008")
    assert len(results) == 1
    assert results[0].display_name == "Houston, Texas, US, 77008"
    assert results[0].postal_code == "77008"
    last_call_url, last_call_params = fake_http.calls[-1]
    assert last_call_url == OPEN_METEO_GEOCODING_URL
    assert last_call_params.get("countryCode") == "US"


def test_open_meteo_search_rejects_blank_query() -> None:
    geocoder = OpenMeteoGeocoder(http_client=FakeJsonHttpClient({}))
    with pytest.raises(WindAutofillLocationError, match="Enter a ZIP"):
        geocoder.search("   ")


def test_build_autofill_maps_required_fields_from_nws_observations() -> None:
    fake_http = FakeJsonHttpClient(_nws_success_responses())
    service = WindWeatherAutofillService(
        weather_client=NwsObservationClient(http_client=fake_http),
    )
    result = service.build_autofill(
        WindAutofillRequest(
            location=_location(),
            report_date=date(2026, 2, 6),
            start_time_24h="13:00",
            end_time_24h="17:00",
        )
    )

    assert result.start.direction == "SSW"
    assert result.start.speed_mph == 10
    assert result.start.gust_mph == 20
    assert result.start.temp_f == 52
    assert result.start.station_id == "KHOU"

    assert result.end.direction == "NNW"
    assert result.end.speed_mph == 12
    assert result.end.gust_mph == 24
    assert result.end.temp_f == 55
    assert result.end.station_id == "KHOU"
    assert result.verification_url is not None
    assert "/stations/KHOU/observations" in result.verification_url
    assert "start=2026-02-06T19%3A00%3A00Z" in result.verification_url
    assert "end=2026-02-06T23%3A00%3A00Z" in result.verification_url
    assert result.warnings == ()


def test_build_autofill_uses_nearest_observation_for_half_hour_inputs() -> None:
    fake_http = FakeJsonHttpClient(
        {
            f"{NWS_BASE_URL}/points/29.7604,-95.3698": {
                "properties": {
                    "observationStations": f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations",
                }
            },
            f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations": {
                "features": [{"properties": {"stationIdentifier": "KHOU"}}]
            },
            f"{NWS_BASE_URL}/stations/KHOU/observations": {
                "features": [
                    {
                        "properties": {
                            "timestamp": "2026-02-06T19:25:00+00:00",
                            "windDirection": {"value": 180.0, "unitCode": "wmoUnit:degree_(angle)"},
                            "windSpeed": {"value": 3.57632, "unitCode": "wmoUnit:m_s-1"},
                            "windGust": {"value": 6.25856, "unitCode": "wmoUnit:m_s-1"},
                            "temperature": {"value": 10.0, "unitCode": "wmoUnit:degC"},
                        }
                    },
                    {
                        "properties": {
                            "timestamp": "2026-02-06T23:40:00+00:00",
                            "windDirection": {"value": 45.0, "unitCode": "wmoUnit:degree_(angle)"},
                            "windSpeed": {"value": 4.02336, "unitCode": "wmoUnit:m_s-1"},
                            "windGust": {"value": 5.8112, "unitCode": "wmoUnit:m_s-1"},
                            "temperature": {"value": 12.0, "unitCode": "wmoUnit:degC"},
                        }
                    },
                ]
            },
        }
    )
    service = WindWeatherAutofillService(weather_client=NwsObservationClient(http_client=fake_http))
    result = service.build_autofill(
        WindAutofillRequest(
            location=_location(),
            report_date=date(2026, 2, 6),
            start_time_24h="13:30",
            end_time_24h="17:30",
        )
    )

    assert result.start.direction == "S"
    assert result.start.speed_mph == 8
    assert result.end.direction == "NE"
    assert result.end.gust_mph == 13


def test_build_autofill_returns_partial_row_and_warning_when_field_missing() -> None:
    fake_http = FakeJsonHttpClient(
        {
            f"{NWS_BASE_URL}/points/29.7604,-95.3698": {
                "properties": {"observationStations": f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations"}
            },
            f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations": {
                "features": [{"properties": {"stationIdentifier": "KHOU"}}]
            },
            f"{NWS_BASE_URL}/stations/KHOU/observations": {
                "features": [
                    {
                        "properties": {
                            "timestamp": "2026-02-06T19:00:00+00:00",
                            "windDirection": {"value": None, "unitCode": "wmoUnit:degree_(angle)"},
                            "windSpeed": {"value": 4.4704, "unitCode": "wmoUnit:m_s-1"},
                            "windGust": {"value": None, "unitCode": "wmoUnit:m_s-1"},
                            "temperature": {"value": 11.0, "unitCode": "wmoUnit:degC"},
                        }
                    },
                    {
                        "properties": {
                            "timestamp": "2026-02-06T23:00:00+00:00",
                            "windDirection": {"value": 300.0, "unitCode": "wmoUnit:degree_(angle)"},
                            "windSpeed": {"value": 5.36448, "unitCode": "wmoUnit:m_s-1"},
                            "windGust": {"value": 10.729, "unitCode": "wmoUnit:m_s-1"},
                            "temperature": {"value": 13.0, "unitCode": "wmoUnit:degC"},
                        }
                    },
                ]
            },
        }
    )
    service = WindWeatherAutofillService(weather_client=NwsObservationClient(http_client=fake_http))
    result = service.build_autofill(
        WindAutofillRequest(
            location=_location(),
            report_date=date(2026, 2, 6),
            start_time_24h="13:00",
            end_time_24h="17:00",
        )
    )

    assert result.start.direction is None
    assert result.start.gust_mph is None
    assert "Wind direction not reported" in " | ".join(result.start.warnings)
    assert "Wind gust not reported" in " | ".join(result.start.warnings)
    assert result.verification_url is not None
    assert len(result.warnings) >= 2


def test_build_autofill_raises_when_provider_returns_no_observations() -> None:
    fake_http = FakeJsonHttpClient(
        {
            f"{NWS_BASE_URL}/points/29.7604,-95.3698": {
                "properties": {"observationStations": f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations"}
            },
            f"{NWS_BASE_URL}/gridpoints/HGX/54,97/stations": {
                "features": [{"properties": {"stationIdentifier": "KHOU"}}]
            },
            f"{NWS_BASE_URL}/stations/KHOU/observations": {"features": []},
        }
    )
    service = WindWeatherAutofillService(weather_client=NwsObservationClient(http_client=fake_http))
    with pytest.raises(WindAutofillProviderError, match="No weather observations"):
        service.build_autofill(
            WindAutofillRequest(
                location=_location(),
                report_date=date(2026, 2, 6),
                start_time_24h="13:00",
                end_time_24h="17:00",
            )
        )
