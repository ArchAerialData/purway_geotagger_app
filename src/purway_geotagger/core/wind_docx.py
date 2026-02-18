from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import re
from typing import Any


DATE_FORMAT_TEMPLATE = "%Y_%m_%d"
DEFAULT_TIMEZONE = "CST"
DEGREE_SYMBOL = "\u00B0"

MIN_WIND_SPEED_MPH = 0
MAX_WIND_SPEED_MPH = 200
MIN_GUST_MPH = 0
MAX_GUST_MPH = 250
MIN_TEMP_F = -100
MAX_TEMP_F = 150

_INT_RE = re.compile(r"^[+-]?\d+$")
_PLACEHOLDER_SAFE_RE = re.compile(r"[{}]")
_DIRECTION_RE = re.compile(r"^[A-Z]{1,8}$")


class WindInputValidationError(ValueError):
    """Raised when wind DOCX user input is invalid."""


@dataclass(frozen=True)
class WindReportMetadataRaw:
    client_name: str
    system_name: str
    report_date: date | datetime | str
    timezone: str = DEFAULT_TIMEZONE
    region_id: str = ""


@dataclass(frozen=True)
class WindRowRaw:
    time_value: time | datetime | str
    wind_direction: str
    wind_speed_mph: int | str
    gust_mph: int | str
    temp_f: int | str


@dataclass(frozen=True)
class WindRowNormalized:
    time_text: str
    wind_direction: str
    wind_speed_mph: int
    gust_mph: int
    temp_f: int
    summary_string: str


@dataclass(frozen=True)
class WindTemplatePayload:
    client_name: str
    system_name: str
    region_id: str
    date: str
    tz: str
    s_time: str
    e_time: str
    s_string: str
    e_string: str

    def as_placeholder_map(self) -> dict[str, str]:
        return {
            "CLIENT_NAME": self.client_name,
            "SYSTEM_NAME": self.system_name,
            "REGION_ID": self.region_id,
            "DATE": self.date,
            "TZ": self.tz,
            "S_TIME": self.s_time,
            "E_TIME": self.e_time,
            "S_STRING": self.s_string,
            "E_STRING": self.e_string,
        }

    def output_filename(self) -> str:
        return build_wind_output_filename(self.client_name, self.date)


@dataclass(frozen=True)
class WindDebugPayload:
    raw_metadata: dict[str, str]
    raw_start: dict[str, str]
    raw_end: dict[str, str]
    normalized_metadata: dict[str, str]
    normalized_start: dict[str, str]
    normalized_end: dict[str, str]
    computed_strings: dict[str, str]
    placeholder_map: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_metadata": dict(self.raw_metadata),
            "raw_start": dict(self.raw_start),
            "raw_end": dict(self.raw_end),
            "normalized_metadata": dict(self.normalized_metadata),
            "normalized_start": dict(self.normalized_start),
            "normalized_end": dict(self.normalized_end),
            "computed_strings": dict(self.computed_strings),
            "placeholder_map": dict(self.placeholder_map),
        }


@dataclass(frozen=True)
class WindReportBuildResult:
    payload: WindTemplatePayload
    debug_payload: WindDebugPayload


def normalize_report_date(value: date | datetime | str) -> str:
    parsed_date: date
    if isinstance(value, datetime):
        parsed_date = value.date()
    elif isinstance(value, date):
        parsed_date = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise WindInputValidationError("Date is required.")
        for fmt in ("%Y_%m_%d", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
            try:
                parsed_date = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
        else:
            raise WindInputValidationError(
                "Date must be a valid calendar date (supported: YYYY_MM_DD, YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY)."
            )
    else:
        raise WindInputValidationError(f"Unsupported date type: {type(value).__name__}")
    return parsed_date.strftime(DATE_FORMAT_TEMPLATE)


def format_wind_time(value: time | datetime | str) -> str:
    t = _coerce_time(value, field_name="time")
    hour_12 = t.hour % 12 or 12
    suffix = "am" if t.hour < 12 else "pm"
    return f"{hour_12}:{t.minute:02d}{suffix}"


def format_wind_summary(
    direction: str,
    speed_mph: int,
    gust_mph: int,
    temp_f: int,
    *,
    degree_symbol: str = DEGREE_SYMBOL,
) -> str:
    return f"{direction} {speed_mph} mph / Gusts {gust_mph} mph / {temp_f}{degree_symbol}F"


def build_wind_output_filename(client_name: str, normalized_date: str) -> str:
    safe_client_name = _normalize_text(client_name, field_name="Client Name")
    if "/" in safe_client_name or "\\" in safe_client_name:
        raise WindInputValidationError("Client Name cannot include path separators.")
    filename_client_name = re.sub(r"\s+", "", safe_client_name)
    if not filename_client_name:
        raise WindInputValidationError("Client Name must include at least one non-whitespace character.")
    if not re.fullmatch(r"\d{4}_\d{2}_\d{2}", normalized_date):
        raise WindInputValidationError("DATE must be normalized to YYYY_MM_DD before filename generation.")
    return f"WindData_{filename_client_name}_{normalized_date}.docx"


def build_wind_template_payload(
    metadata_raw: WindReportMetadataRaw,
    start_raw: WindRowRaw,
    end_raw: WindRowRaw,
) -> WindReportBuildResult:
    client_name = _normalize_text(metadata_raw.client_name, field_name="Client Name")
    system_name = _normalize_text(metadata_raw.system_name, field_name="System Name")
    region_id = _normalize_optional_text(metadata_raw.region_id, field_name="Region")
    tz = _normalize_timezone(metadata_raw.timezone)
    normalized_date = normalize_report_date(metadata_raw.report_date)

    start_time_value = _coerce_time(start_raw.time_value, field_name="Start time")
    end_time_value = _coerce_time(end_raw.time_value, field_name="End time")
    if _minutes_since_midnight(end_time_value) < _minutes_since_midnight(start_time_value):
        raise WindInputValidationError(
            "End time must be the same as or later than start time for single-day Wind Data reports."
        )

    start = _normalize_row(start_raw, row_label="Start")
    end = _normalize_row(end_raw, row_label="End")

    payload = WindTemplatePayload(
        client_name=client_name,
        system_name=system_name,
        region_id=region_id,
        date=normalized_date,
        tz=tz,
        s_time=start.time_text,
        e_time=end.time_text,
        s_string=start.summary_string,
        e_string=end.summary_string,
    )
    placeholder_map = payload.as_placeholder_map()

    debug_payload = WindDebugPayload(
        raw_metadata={
            "client_name": _stringify_raw(metadata_raw.client_name),
            "system_name": _stringify_raw(metadata_raw.system_name),
            "region_id": _stringify_raw(metadata_raw.region_id),
            "report_date": _stringify_raw(metadata_raw.report_date),
            "timezone": _stringify_raw(metadata_raw.timezone),
        },
        raw_start={
            "time_value": _stringify_raw(start_raw.time_value),
            "wind_direction": _stringify_raw(start_raw.wind_direction),
            "wind_speed_mph": _stringify_raw(start_raw.wind_speed_mph),
            "gust_mph": _stringify_raw(start_raw.gust_mph),
            "temp_f": _stringify_raw(start_raw.temp_f),
        },
        raw_end={
            "time_value": _stringify_raw(end_raw.time_value),
            "wind_direction": _stringify_raw(end_raw.wind_direction),
            "wind_speed_mph": _stringify_raw(end_raw.wind_speed_mph),
            "gust_mph": _stringify_raw(end_raw.gust_mph),
            "temp_f": _stringify_raw(end_raw.temp_f),
        },
        normalized_metadata={
            "client_name": client_name,
            "system_name": system_name,
            "region_id": region_id,
            "date": normalized_date,
            "timezone": tz,
        },
        normalized_start={
            "time": start.time_text,
            "wind_direction": start.wind_direction,
            "wind_speed_mph": str(start.wind_speed_mph),
            "gust_mph": str(start.gust_mph),
            "temp_f": str(start.temp_f),
        },
        normalized_end={
            "time": end.time_text,
            "wind_direction": end.wind_direction,
            "wind_speed_mph": str(end.wind_speed_mph),
            "gust_mph": str(end.gust_mph),
            "temp_f": str(end.temp_f),
        },
        computed_strings={
            "S_STRING": start.summary_string,
            "E_STRING": end.summary_string,
            "output_filename": payload.output_filename(),
        },
        placeholder_map=placeholder_map,
    )
    return WindReportBuildResult(payload=payload, debug_payload=debug_payload)


def _normalize_row(row_raw: WindRowRaw, *, row_label: str) -> WindRowNormalized:
    direction = _normalize_direction(row_raw.wind_direction, field_name=f"{row_label} wind direction")
    speed = _parse_integer_field(
        row_raw.wind_speed_mph,
        field_name=f"{row_label} wind speed",
        min_value=MIN_WIND_SPEED_MPH,
        max_value=MAX_WIND_SPEED_MPH,
    )
    gust = _parse_integer_field(
        row_raw.gust_mph,
        field_name=f"{row_label} gust",
        min_value=MIN_GUST_MPH,
        max_value=MAX_GUST_MPH,
    )
    temp_f = _parse_integer_field(
        row_raw.temp_f,
        field_name=f"{row_label} temperature",
        min_value=MIN_TEMP_F,
        max_value=MAX_TEMP_F,
    )
    time_text = format_wind_time(row_raw.time_value)
    summary_string = format_wind_summary(direction, speed, gust, temp_f)
    return WindRowNormalized(
        time_text=time_text,
        wind_direction=direction,
        wind_speed_mph=speed,
        gust_mph=gust,
        temp_f=temp_f,
        summary_string=summary_string,
    )


def _normalize_text(value: str, *, field_name: str, max_len: int = 120) -> str:
    if not isinstance(value, str):
        raise WindInputValidationError(f"{field_name} is required.")
    text = value.strip()
    if not text:
        raise WindInputValidationError(f"{field_name} is required.")
    if _PLACEHOLDER_SAFE_RE.search(text):
        raise WindInputValidationError(f"{field_name} cannot contain template braces.")
    if len(text) > max_len:
        raise WindInputValidationError(f"{field_name} must be at most {max_len} characters.")
    return text


def _normalize_timezone(value: str) -> str:
    timezone_text = _normalize_text(value, field_name="Time Zone", max_len=24)
    return timezone_text.upper()


def _normalize_optional_text(value: str | None, *, field_name: str, max_len: int = 120) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise WindInputValidationError(f"{field_name} must be text.")
    text = value.strip()
    if not text:
        return ""
    if _PLACEHOLDER_SAFE_RE.search(text):
        raise WindInputValidationError(f"{field_name} cannot contain template braces.")
    if len(text) > max_len:
        raise WindInputValidationError(f"{field_name} must be at most {max_len} characters.")
    return text


def _normalize_direction(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise WindInputValidationError(f"{field_name} is required.")
    compact = re.sub(r"\s+", "", value).upper()
    if not compact:
        raise WindInputValidationError(f"{field_name} is required.")
    if not _DIRECTION_RE.fullmatch(compact):
        raise WindInputValidationError(
            f"{field_name} must be letters only (examples: SW, SSW, NNE)."
        )
    return compact


def _parse_integer_field(
    value: int | str,
    *,
    field_name: str,
    min_value: int,
    max_value: int,
) -> int:
    if isinstance(value, bool):
        raise WindInputValidationError(f"{field_name} must be an integer.")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise WindInputValidationError(f"{field_name} is required.")
        if not _INT_RE.fullmatch(text):
            raise WindInputValidationError(
                f"{field_name} must be integer-only (do not include units such as mph)."
            )
        parsed = int(text)
    else:
        raise WindInputValidationError(f"{field_name} must be an integer.")

    if parsed < min_value or parsed > max_value:
        raise WindInputValidationError(
            f"{field_name} must be between {min_value} and {max_value}."
        )
    return parsed


def _coerce_time(value: time | datetime | str, *, field_name: str) -> time:
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if not isinstance(value, str):
        raise WindInputValidationError(f"{field_name} is required.")

    text = value.strip()
    if not text:
        raise WindInputValidationError(f"{field_name} is required.")
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M%p", "%I:%M %p", "%I:%M:%S%p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(text, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue
    raise WindInputValidationError(
        f"{field_name} must be a valid time (examples: 10:00, 1:00pm)."
    )


def _minutes_since_midnight(t: time) -> int:
    return t.hour * 60 + t.minute


def _stringify_raw(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat(timespec="minutes")
    return str(value)
