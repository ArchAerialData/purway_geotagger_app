"""Track report values separately from the weather measurements that suggested them."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .wind_docx import WindReportMetadataRaw, WindRowRaw, normalize_report_date
from .wind_weather_autofill import WindAutofillResult


FIELD_ATTRIBUTES = {
    "direction": "wind_direction", "speed_mph": "wind_speed_mph",
    "gust_mph": "gust_mph", "temp_f": "temp_f",
}


def report_timezone(result: WindAutofillResult) -> str | None:
    if result.request is None:
        return None
    request = result.request
    zone = ZoneInfo(request.location.timezone_name)
    labels = []
    for text in (request.start_time_24h, request.end_time_24h):
        local = datetime.combine(request.report_date, datetime.strptime(text, "%H:%M").time(), zone)
        labels.append(local.tzname() or request.location.timezone_name)
    return "/".join(dict.fromkeys(labels))


class WindWeatherEvidence:
    def __init__(self) -> None:
        self._fields: dict[str, dict[str, dict[str, Any]]] = {"start": {}, "end": {}}
        self.last_warnings: tuple[str, ...] = ()
        self.last_missing: dict[str, list[str]] = {"start": [], "end": []}

    def mark_manual(self, row: str, name: str, value: Any) -> None:
        entry = self._fields[row].setdefault(name, {})
        entry.update(status="manual", value=value)

    def apply(self, result: WindAutofillResult) -> None:
        self.last_warnings = result.warnings
        request = result.request
        for label, row in (("start", result.start), ("end", result.end)):
            self.last_missing[label] = []
            for name in FIELD_ATTRIBUTES:
                value = getattr(row, name)
                if value is None:
                    self.last_missing[label].append(name)
                    retained = self._fields[label].setdefault(name, {"status": "missing"})
                    if request is not None and retained.get("status") in {"observed", "estimated"}:
                        old_location = retained["requested"]["location"]
                        if (old_location["latitude"], old_location["longitude"]) != (
                                request.location.latitude, request.location.longitude):
                            retained["status"] = "context_changed"
                    continue  # Preserve previous/manual evidence with the retained value.
                source = row.field_sources.get(name)
                entry: dict[str, Any] = {"value": value, "status": "unverified"}
                if source is not None and request is not None:
                    source_data = asdict(source)
                    source_data["observed_at_utc"] = source.observed_at_utc.isoformat()
                    zone = ZoneInfo(request.location.timezone_name)
                    time_text = request.start_time_24h if label == "start" else request.end_time_24h
                    target = datetime.combine(request.report_date, datetime.strptime(time_text, "%H:%M").time(), zone)
                    source_data["observed_at_local"] = source.observed_at_utc.astimezone(zone).isoformat()
                    source_data["time_delta_minutes"] = (source.observed_at_utc - target).total_seconds() / 60
                    entry.update(
                        status=source.kind, source=source_data,
                        imported_value=value,
                        requested={"date": request.report_date.isoformat(), "time": time_text,
                                   "timezone": report_timezone(result), "timezone_name": zone.key,
                                   "target_utc": target.astimezone(timezone.utc).isoformat(),
                                   "location": asdict(request.location), "policy": asdict(request.policy)},
                        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                    )
                self._fields[label][name] = entry

    def snapshot(self, metadata: WindReportMetadataRaw, start: WindRowRaw, end: WindRowRaw) -> dict[str, Any]:
        rows = {}
        for label, raw in (("start", start), ("end", end)):
            fields = {}
            time_text = raw.time_value.strftime("%H:%M") if hasattr(raw.time_value, "strftime") else str(raw.time_value)
            for name, attribute in FIELD_ATTRIBUTES.items():
                current = getattr(raw, attribute)
                entry = deepcopy(self._fields[label].get(name, {"status": "unverified"}))
                entry["value"] = current
                if entry["status"] in {"observed", "estimated"}:
                    requested = entry["requested"]
                    if str(current) != str(entry["imported_value"]):
                        entry["status"] = "manual"
                    elif (normalize_report_date(metadata.report_date).replace("_", "-") != requested["date"]
                          or time_text != requested["time"]
                          or metadata.timezone.strip().upper() != requested["timezone"]):
                        entry["status"] = "context_changed"
                fields[name] = entry
            rows[label] = fields
        return {"schema_version": 1, "rows": rows,
                "last_lookup_warnings": list(self.last_warnings),
                "last_lookup_missing_fields": deepcopy(self.last_missing)}
