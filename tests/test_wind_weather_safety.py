from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from purway_geotagger.core import wind_weather_autofill as w
from purway_geotagger.core.wind_docx import WindReportMetadataRaw, WindRowRaw
from purway_geotagger.core.wind_weather_evidence import WindWeatherEvidence, report_timezone
from test_wind_weather_autofill import FakeJsonHttpClient, _location, _nws_success_responses


TARGET = datetime(2026, 2, 6, 19, tzinfo=timezone.utc)
ZONE = ZoneInfo("America/Chicago")


def observation(*, when=TARGET, distance=5.0, station="KHOU", gust=20):
    return {"timestamp": when, "distance_miles": distance, "station_id": station,
            "latitude": 29.7, "longitude": -95.3,
            "windDirection": {"value": 180, "unitCode": "degree"},
            "windSpeed": {"value": 10, "unitCode": "mph"},
            "windGust": {"value": gust, "unitCode": "mph"},
            "temperature": {"value": 70, "unitCode": "degF"}}


def row(**kwargs):
    obs = observation(**kwargs)
    return w._to_wind_row(obs, obs["station_id"], w.AWC_METAR_URL + "?ids=" + obs["station_id"], ZONE)


@pytest.mark.parametrize("distance,minutes,expected", [(25,60,True),(25.01,0,False),
                                                       (0,60.01,False),(150,720,False)])
def test_station_distance_and_time_are_hard_inclusive_limits(distance, minutes, expected):
    obs = observation(distance=distance, when=TARGET-timedelta(minutes=minutes))
    assert (w._nearest_awc_observation([obs], TARGET) is not None) is expected


def test_zero_distance_is_not_treated_as_unknown():
    local, remote = observation(distance=0), observation(distance=20)
    assert w._nearest_awc_observation([remote, local], TARGET) is local


def test_stale_hourly_and_future_observations_are_ineligible():
    assert w._nearest_observation([observation(when=TARGET-timedelta(hours=24))], TARGET) is None
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    assert w._nearest_observation([observation(when=future)], future) is None


def test_mixed_row_keeps_each_fields_station_and_time():
    primary = row(gust=None)
    fallback = row(station="KOTHER", when=TARGET-timedelta(minutes=30), gust=30)
    merged, fields = w._merge_row_with_fallback(primary=primary, fallback=fallback)
    assert fields == ("gust_mph",)
    assert merged.speed_mph == 10 and merged.gust_mph == 30
    assert merged.field_sources["speed_mph"].station_id == "KHOU"
    assert merged.field_sources["gust_mph"].station_id == "KOTHER"
    assert merged.field_sources["gust_mph"].observed_at_utc == TARGET-timedelta(minutes=30)
    assert merged.station_id is None and merged.observed_at_utc is None and merged.source_url is None


class FixedProvider:
    def __init__(self, rows=None):
        self.rows, self.calls = rows, 0

    def fetch_rows(self, **kwargs):
        self.calls += 1
        if self.rows is None:
            raise w.WindAutofillProviderError("offline")
        return self.rows


def test_partial_metar_after_nws_failure_uses_archive_and_keeps_valid_end():
    partial = row(gust=None)
    full_end = row(when=TARGET+timedelta(hours=4))
    model = row(station="OPEN_METEO_ARCHIVE", gust=22)
    archive = FixedProvider((model, model))
    service = w.WindWeatherAutofillService(weather_client=FixedProvider(),
        metar_client=FixedProvider((partial, full_end)), archive_client=archive)
    result = service.build_autofill(w.WindAutofillRequest(_location(),date(2026,2,6),"13:00","17:00"))
    assert archive.calls == 1
    assert result.start.gust_mph == 22
    assert result.start.field_sources["gust_mph"].kind == "estimated"
    assert result.end == full_end
    assert any("model estimates" in warning for warning in result.warnings)


def test_nws_checks_coordinates_and_continues_after_first_station_failure():
    responses = _nws_success_responses()
    station_url = f"{w.NWS_BASE_URL}/gridpoints/HGX/54,97/stations"
    responses[station_url]["features"].insert(0, {
        "properties": {"stationIdentifier":"FAILED"},
        "geometry": {"coordinates":[-95.3698,29.7604]}})
    responses[f"{w.NWS_BASE_URL}/stations/FAILED/observations"] = w.WindAutofillProviderError("offline")
    client = w.NwsObservationClient(FakeJsonHttpClient(responses))
    args = dict(latitude=29.7604,longitude=-95.3698,start_utc=TARGET-timedelta(hours=1),
        end_utc=TARGET+timedelta(hours=5),targets_utc=(TARGET,TARGET+timedelta(hours=4)),
        verification_start_utc=TARGET,verification_end_utc=TARGET,local_timezone=ZONE)
    start,end = client.fetch_rows(**args)
    assert start.station_id == end.station_id == "KHOU"
    assert 0 < start.field_sources["speed_mph"].distance_miles < 25
    responses[station_url]["features"][1]["geometry"] = {"coordinates":[-97,30]}
    with pytest.raises(w.WindAutofillProviderError,match="no eligible"):
        client.fetch_rows(**args)


def test_metar_query_uses_target_date_and_rejects_distant_bbox_corner():
    payload = [{"icaoId":"CORNER","obsTime":int(TARGET.timestamp()),"lat":30.12,"lon":-94.95,
                "temp":20,"wdir":180,"wspd":10,"wgst":20}]
    http = FakeJsonHttpClient({w.AWC_METAR_URL:payload})
    client = w.AviationWeatherMetarClient(http,max_history_hours=1_000_000)
    with pytest.raises(w.WindAutofillProviderError):
        client.fetch_rows(latitude=29.7604,longitude=-95.3698,targets_utc=(TARGET,TARGET),local_timezone=ZONE)
    assert http.calls[0][1]["hours"] == "2"
    assert http.calls[0][1]["date"] == "2026-02-06T20:00:00Z"


def test_one_target_can_remain_missing_without_reusing_distant_time():
    http = FakeJsonHttpClient({w.AWC_METAR_URL:[{
        "icaoId":"KHOU","obsTime":int(TARGET.timestamp()),"lat":29.7,"lon":-95.3,
        "temp":20,"wdir":180,"wspd":10,"wgst":20}]})
    start,end = w.AviationWeatherMetarClient(http,max_history_hours=1_000_000).fetch_rows(
        latitude=29.7604,longitude=-95.3698,targets_utc=(TARGET,TARGET+timedelta(hours=4)),local_timezone=ZONE)
    assert start.speed_mph is not None and end.speed_mph is None
    assert end.field_sources == {}


@pytest.mark.parametrize("day,time_text", [(date(2026,3,8),"02:30"),(date(2026,11,1),"01:30")])
def test_dst_nonexistent_or_ambiguous_times_fail_explicitly(day,time_text):
    with pytest.raises(w.WindAutofillProviderError,match="daylight-saving"):
        w._combine_local(day,datetime.strptime(time_text,"%H:%M").time(),ZONE)


def test_future_request_is_rejected_before_network():
    provider = FixedProvider()
    service = w.WindWeatherAutofillService(weather_client=provider,metar_client=provider,archive_client=provider)
    with pytest.raises(w.WindAutofillProviderError,match="retrospective"):
        service.build_autofill(w.WindAutofillRequest(_location(), date.today()+timedelta(days=1),"10:00","11:00"))
    assert provider.calls == 0


def test_epoch_archive_times_keep_fall_back_hours_distinct():
    timestamps = [int(datetime(2025,11,2,h,tzinfo=timezone.utc).timestamp()) for h in (6,7)]
    observations = w._open_meteo_hourly_observations(hourly={"time":timestamps},local_timezone=ZONE)
    assert (observations[1]["timestamp"]-observations[0]["timestamp"]).total_seconds() == 3600


def test_invalid_numbers_variable_wind_and_missing_gust_are_not_fabricated():
    obs = observation(gust=None)
    obs["windDirection"]["value"] = "VRB"
    obs["temperature"]["value"] = float("inf")
    result = w._to_wind_row(obs,"KHOU",w.AWC_METAR_URL,ZONE)
    assert result.direction == "VRB" and result.temp_f is None and result.gust_mph is None
    obs["windSpeed"]["value"] = 0
    assert w._to_wind_row(obs,"KHOU",w.AWC_METAR_URL,ZONE).direction == "CALM"
    obs["windSpeed"]["value"] = 0.2
    obs["windDirection"]["value"] = 180
    assert w._to_wind_row(obs,"KHOU",w.AWC_METAR_URL,ZONE).direction == "S"


def test_manual_edit_and_report_context_changes_keep_original_evidence():
    request = w.WindAutofillRequest(_location(),date(2026,7,1),"13:00","17:00")
    result = w.WindAutofillResult(_location(),row(),row(),None,(),request=request)
    assert report_timezone(result) == "CDT"
    evidence = WindWeatherEvidence()
    evidence.apply(result)
    metadata = WindReportMetadataRaw("Client","System",request.report_date,"CDT")
    raw = WindRowRaw("13:00","S",10,20,70)
    assert evidence.snapshot(metadata,raw,raw)["rows"]["start"]["speed_mph"]["status"] == "observed"
    changed = evidence.snapshot(replace(metadata, report_date=date(2026,7,2)),raw,raw)
    assert changed["rows"]["start"]["speed_mph"]["status"] == "context_changed"
    evidence.mark_manual("start","speed_mph",15)
    snapshot = evidence.snapshot(metadata,replace(raw,wind_speed_mph=15),raw)
    assert snapshot["rows"]["start"]["speed_mph"]["status"] == "manual"
    assert snapshot["rows"]["start"]["speed_mph"]["source"]["station_id"] == "KHOU"
    evidence.apply(replace(result,start=w._empty_row(),end=w._empty_row()))
    assert evidence.snapshot(metadata,replace(raw,wind_speed_mph=15),raw)["rows"]["start"]["speed_mph"]["status"] == "manual"


def test_204_empty_response_is_normal_no_data(monkeypatch):
    class Response:
        status = 204
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): raise AssertionError("204 has no JSON body")
    monkeypatch.setattr(w,"urlopen",lambda *args,**kwargs:Response())
    assert w.UrlLibJsonHttpClient().get_json(w.AWC_METAR_URL) == []
