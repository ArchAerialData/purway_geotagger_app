from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

from purway_geotagger.util.timeparse import parse_csv_timestamp, parse_photo_timestamp_from_name, format_exif_datetime
from purway_geotagger.util.errors import CorrelationError
from purway_geotagger.core.pac_calculator import calculate_pac
from purway_geotagger.parsers.table_inputs import InputTable, read_tables, finite_number, check_cancel, CancelCheck

from purway_geotagger.parsers.columns import (
    PHOTO_COL_CANDIDATES,
    LAT_COL_CANDIDATES,
    LON_COL_CANDIDATES,
    TIME_COL_CANDIDATES,
    PPM_COL_CANDIDATES,
    ALT_COL_CANDIDATES,
    REL_ALT_COL_CANDIDATES,
    LIGHT_COL_CANDIDATES,
    UAV_PITCH_CANDIDATES,
    UAV_ROLL_CANDIDATES,
    UAV_YAW_CANDIDATES,
    GIMBAL_PITCH_CANDIDATES,
    GIMBAL_ROLL_CANDIDATES,
    GIMBAL_YAW_CANDIDATES,
    FOCAL_LENGTH_CANDIDATES,
    ZOOM_CANDIDATES,
    TARGET_LAT_COL_CANDIDATES,
    TARGET_LON_COL_CANDIDATES,
    DISTANCE_COL_CANDIDATES,
    STATUS_COL_CANDIDATES,
    ERR_CODE_COL_CANDIDATES,
    SNR_COL_CANDIDATES,
    RELIABILITY_COL_CANDIDATES,
    FLIGHT_STATUS_COL_CANDIDATES,
    DIS_CODE_COL_CANDIDATES,
    HOME_DISTANCE_COL_CANDIDATES,
    SPEED_COL_CANDIDATES,
    pick_column as _pick_col,
)

REASON_NO_PHOTO_OR_TIMESTAMP = "no explicit Photo column correlation and no timestamped CSV rows available"
REASON_NO_FILENAME_TIMESTAMP = "no filename timestamp and no explicit Photo column correlation"
REASON_AMBIGUOUS_TIMESTAMP = "ambiguous timestamp join"

@dataclass(frozen=True)
class PurwayRecord:
    csv_path: Path
    lat: float
    lon: float
    ppm: float
    timestamp: object  # datetime or None
    photo_ref: str | None
    # Extended fields
    altitude: float | None = None
    relative_altitude: float | None = None
    light_intensity: float | None = None
    uav_pitch: float | None = None
    uav_roll: float | None = None
    uav_yaw: float | None = None
    gimbal_pitch: float | None = None
    gimbal_roll: float | None = None
    gimbal_yaw: float | None = None
    camera_focal_length: float | None = None
    camera_zoom: float | None = None
    timestamp_raw: str | None = None
    target_lat: float | None = None
    target_lon: float | None = None
    distance: float | None = None
    source_file_name: str | None = None
    payload_model: str | None = None
    csv_status: str | None = None
    err_code: str | None = None
    snr: float | None = None
    reliability: float | None = None
    flight_status: str | None = None
    dis_code: str | None = None
    home_distance: float | None = None
    speed: float | None = None
    source_sheet: str = ""
    source_row: int | None = None

@dataclass(frozen=True)
class PhotoMatch:
    csv_path: str
    source_csv: str
    lat: float
    lon: float
    ppm: float
    datetime_original: str | None
    image_description: str
    join_method: str  # FILENAME|TIMESTAMP
    join_delta_seconds: float | None = None
    # Extended fields
    altitude: float | None = None
    relative_altitude: float | None = None
    light_intensity: float | None = None
    uav_pitch: float | None = None
    uav_roll: float | None = None
    uav_yaw: float | None = None
    gimbal_pitch: float | None = None
    gimbal_roll: float | None = None
    gimbal_yaw: float | None = None
    camera_focal_length: float | None = None
    camera_zoom: float | None = None
    timestamp_raw: str | None = None
    pac: float | None = None  # Derived: ppm / relative_altitude
    target_lat: float | None = None
    target_lon: float | None = None
    distance: float | None = None
    source_file_name: str | None = None
    payload_model: str | None = None
    csv_status: str | None = None
    err_code: str | None = None
    snr: float | None = None
    reliability: float | None = None
    flight_status: str | None = None
    dis_code: str | None = None
    home_distance: float | None = None
    speed: float | None = None
    source_sheet: str = ""
    source_row: int | None = None

class PurwayCSVIndex:
    def __init__(self, records: list[PurwayRecord]) -> None:
        self.records = records
        self.errors: list[str] = []
        self.ambiguous_photos: set[str] = set()

        # Precompute maps for faster joins
        self.by_photo: dict[str, PurwayRecord] = {}
        self.by_time: list[PurwayRecord] = []
        for r in records:
            if r.photo_ref:
                name = Path(r.photo_ref.replace("\\", "/")).name
                previous = self.by_photo.get(name)
                if previous is not None:
                    ignored = {"csv_path", "source_sheet", "source_row"}
                    if any(getattr(previous, f.name) != getattr(r, f.name) for f in fields(r) if f.name not in ignored):
                        self.ambiguous_photos.add(name)
                else:
                    self.by_photo[name] = r
            if r.timestamp:
                self.by_time.append(r)

    @classmethod
    def from_csv_files(cls, csv_files: list[Path], cancel: CancelCheck = None) -> "PurwayCSVIndex":
        """Compatibility entrypoint: accepts CSV and XLSX metadata sources."""
        records: list[PurwayRecord] = []
        errors = []
        for path in csv_files:
            check_cancel(cancel)
            try:
                file_records = []
                for table in read_tables(path, cancel):
                    try:
                        file_records.extend(_parse_table(table, cancel))
                    except ValueError as exc:
                        raise ValueError(f"{table.sheet or 'CSV'}: {exc}") from exc
                records.extend(file_records)
            except (ValueError, OSError) as exc:
                errors.append(f"{path.name}: {exc}")
        index = cls(records)
        index.errors = errors
        return index

    def match_photo(self, photo_path: Path, max_join_delta_seconds: int) -> PhotoMatch:
        # Step A: filename join
        if photo_path.name in self.ambiguous_photos:
            sources = [f"{r.csv_path.name} / {r.source_sheet or 'CSV'} / row {r.source_row}"
                       for r in self.records if r.photo_ref and Path(r.photo_ref.replace('\\', '/')).name == photo_path.name]
            raise CorrelationError(f"Ambiguous filename join for {photo_path.name}: conflicting metadata rows in {'; '.join(sources)}.")
        if self.by_photo:
            r = self.by_photo.get(photo_path.name)
            if r:
                return _to_match(
                    r,
                    join_method="FILENAME",
                    join_delta_seconds=0.0,
                    matched_photo_name=photo_path.name,
                )

        # Step B: timestamp join
        if not self.by_time:
            raise CorrelationError(REASON_NO_PHOTO_OR_TIMESTAMP)

        photo_dt = parse_photo_timestamp_from_name(photo_path.stem)
        if not photo_dt:
            raise CorrelationError(REASON_NO_FILENAME_TIMESTAMP)

        # Find nearest row by time delta
        best = None
        best_delta = None
        ties = 0
        for r in self.by_time:
            dt = r.timestamp
            if not dt:
                continue
            delta = abs((dt - photo_dt).total_seconds())
            if best is None or delta < best_delta:
                best = r
                best_delta = delta
                ties = 1
            elif best_delta is not None and abs(delta - best_delta) < 0.1:
                ties += 1

        if best is None or best_delta is None:
            raise CorrelationError("Unable to find any timestamped CSV row to join.")

        if best_delta > max_join_delta_seconds:
            raise CorrelationError(f"Nearest timestamp delta {best_delta:.2f}s exceeds threshold {max_join_delta_seconds}s.")

        if ties > 1:
            raise CorrelationError(REASON_AMBIGUOUS_TIMESTAMP)

        return _to_match(
            best,
            join_method="TIMESTAMP",
            join_delta_seconds=best_delta,
            matched_photo_name=photo_path.name,
        )

def _to_match(
    r: PurwayRecord,
    join_method: str,
    join_delta_seconds: float | None,
    matched_photo_name: str | None,
) -> PhotoMatch:
    dto = format_exif_datetime(r.timestamp) if r.timestamp else None
    ppm_int = int(round(r.ppm))
    desc = f"ppm={ppm_int}; source_csv={r.csv_path.name}"
    pac = calculate_pac(r.ppm, r.relative_altitude)
    source_file_name = r.source_file_name or r.photo_ref or matched_photo_name
    return PhotoMatch(
        csv_path=str(r.csv_path),
        source_csv=r.csv_path.name,
        source_sheet=r.source_sheet,
        source_row=r.source_row,
        lat=r.lat,
        lon=r.lon,
        ppm=r.ppm,
        datetime_original=dto,
        image_description=desc,
        join_method=join_method,
        join_delta_seconds=join_delta_seconds,
        altitude=r.altitude,
        relative_altitude=r.relative_altitude,
        light_intensity=r.light_intensity,
        uav_pitch=r.uav_pitch,
        uav_roll=r.uav_roll,
        uav_yaw=r.uav_yaw,
        gimbal_pitch=r.gimbal_pitch,
        gimbal_roll=r.gimbal_roll,
        gimbal_yaw=r.gimbal_yaw,
        camera_focal_length=r.camera_focal_length,
        camera_zoom=r.camera_zoom,
        timestamp_raw=r.timestamp_raw,
        pac=pac,
        target_lat=r.target_lat,
        target_lon=r.target_lon,
        distance=r.distance,
        source_file_name=source_file_name,
        payload_model=r.payload_model,
        csv_status=r.csv_status,
        err_code=r.err_code,
        snr=r.snr,
        reliability=r.reliability,
        flight_status=r.flight_status,
        dis_code=r.dis_code,
        home_distance=r.home_distance,
        speed=r.speed,
    )

def _parse_single_csv(path: Path) -> list[PurwayRecord]:
    return [record for table in read_tables(path) for record in _parse_table(table)]


def _parse_table(table: InputTable, cancel: CancelCheck = None) -> list[PurwayRecord]:
    if table.header_index is None:
        return []
    path, cols = table.path, table.columns
    photo_col = _pick_col(cols, PHOTO_COL_CANDIDATES)
    lat_col = _pick_col(cols, LAT_COL_CANDIDATES, exclude_substrings=["dest_lat", "target_lat", "destination_lat"])
    lon_col = _pick_col(cols, LON_COL_CANDIDATES, exclude_substrings=["dest_lon", "target_lon", "destination_lon"])
    time_col = _pick_col(cols, TIME_COL_CANDIDATES)
    ppm_col = _pick_col(cols, PPM_COL_CANDIDATES)
    
    # Extended column lookups
    alt_col = _pick_col(cols, ALT_COL_CANDIDATES, exclude_substrings=REL_ALT_COL_CANDIDATES)
    rel_alt_col = _pick_col(cols, REL_ALT_COL_CANDIDATES)
    light_col = _pick_col(cols, LIGHT_COL_CANDIDATES)
    uav_pitch_col = _pick_col(cols, UAV_PITCH_CANDIDATES)
    uav_roll_col = _pick_col(cols, UAV_ROLL_CANDIDATES)
    uav_yaw_col = _pick_col(cols, UAV_YAW_CANDIDATES)
    gimbal_pitch_col = _pick_col(cols, GIMBAL_PITCH_CANDIDATES)
    gimbal_roll_col = _pick_col(cols, GIMBAL_ROLL_CANDIDATES)
    gimbal_yaw_col = _pick_col(cols, GIMBAL_YAW_CANDIDATES)
    focal_col = _pick_col(cols, FOCAL_LENGTH_CANDIDATES)
    zoom_col = _pick_col(cols, ZOOM_CANDIDATES)
    target_lat_col = _pick_col(cols, TARGET_LAT_COL_CANDIDATES)
    target_lon_col = _pick_col(cols, TARGET_LON_COL_CANDIDATES)
    distance_col = _pick_col(cols, DISTANCE_COL_CANDIDATES)
    status_col = _pick_col(cols, STATUS_COL_CANDIDATES)
    err_code_col = _pick_col(cols, ERR_CODE_COL_CANDIDATES)
    snr_col = _pick_col(cols, SNR_COL_CANDIDATES)
    reliability_col = _pick_col(cols, RELIABILITY_COL_CANDIDATES)
    flight_status_col = _pick_col(cols, FLIGHT_STATUS_COL_CANDIDATES)
    dis_code_col = _pick_col(cols, DIS_CODE_COL_CANDIDATES)
    home_distance_col = _pick_col(cols, HOME_DISTANCE_COL_CANDIDATES)
    speed_col = _pick_col(cols, SPEED_COL_CANDIDATES)
    payload_model = _detect_payload_model(
        reliability_col=reliability_col,
        flight_status_col=flight_status_col,
        dis_code_col=dis_code_col,
        home_distance_col=home_distance_col,
        speed_col=speed_col,
    )

    if not lat_col or not lon_col:
        return []  # ignore CSVs without coordinate columns

    def _safe_float(row: dict, col: str | None) -> float | None:
        return finite_number(row.get(col)) if col else None

    def _safe_str(row: dict, col: str | None) -> str | None:
        if not col or row.get(col) in (None, ""):
            return None
        value = str(row.get(col)).strip()
        return value or None

    out: list[PurwayRecord] = []
    for source_row, r in table.data_rows():
        check_cancel(cancel)
        lat, lon = finite_number(r.get(lat_col)), finite_number(r.get(lon_col))
        if lat is None or lon is None:
            continue
        ppm = finite_number(r.get(ppm_col)) or 0.0

        ts = None
        ts_raw = None
        if time_col and r.get(time_col):
            ts_raw = str(r.get(time_col)).strip()
            try:
                ts = parse_csv_timestamp(ts_raw)
            except Exception:
                ts = None

        photo_ref = str(r.get(photo_col)).strip() if photo_col and r.get(photo_col) else None

        out.append(PurwayRecord(
            csv_path=path,
            source_sheet=table.sheet,
            source_row=source_row.number,
            lat=lat,
            lon=lon,
            ppm=ppm,
            timestamp=ts,
            photo_ref=photo_ref,
            altitude=_safe_float(r, alt_col),
            relative_altitude=_safe_float(r, rel_alt_col),
            light_intensity=_safe_float(r, light_col),
            uav_pitch=_safe_float(r, uav_pitch_col),
            uav_roll=_safe_float(r, uav_roll_col),
            uav_yaw=_safe_float(r, uav_yaw_col),
            gimbal_pitch=_safe_float(r, gimbal_pitch_col),
            gimbal_roll=_safe_float(r, gimbal_roll_col),
            gimbal_yaw=_safe_float(r, gimbal_yaw_col),
            camera_focal_length=_safe_float(r, focal_col),
            camera_zoom=_safe_float(r, zoom_col),
            timestamp_raw=ts_raw,
            target_lat=_safe_float(r, target_lat_col),
            target_lon=_safe_float(r, target_lon_col),
            distance=_safe_float(r, distance_col),
            source_file_name=photo_ref,
            payload_model=payload_model,
            csv_status=_safe_str(r, status_col),
            err_code=_safe_str(r, err_code_col),
            snr=_safe_float(r, snr_col),
            reliability=_safe_float(r, reliability_col),
            flight_status=_safe_str(r, flight_status_col),
            dis_code=_safe_str(r, dis_code_col),
            home_distance=_safe_float(r, home_distance_col),
            speed=_safe_float(r, speed_col),
        ))
    return out


def _detect_payload_model(
    reliability_col: str | None,
    flight_status_col: str | None,
    dis_code_col: str | None,
    home_distance_col: str | None,
    speed_col: str | None,
) -> str | None:
    if reliability_col:
        return "Purway Model II"
    if any((flight_status_col, dis_code_col, home_distance_col, speed_col)):
        return "Purway Model III"
    return None


@dataclass(frozen=True)
class CSVSchema:
    csv_path: Path
    columns: list[str]
    row_count: int
    photo_col: str | None
    lat_col: str | None
    lon_col: str | None
    time_col: str | None
    ppm_col: str | None
    source_sheet: str = ""
    header_row: int | None = None
    error: str = ""


def inspect_csv_schema(path: Path) -> CSVSchema:
    """Legacy single-table interface; workbook callers use inspect_table_schemas."""
    return inspect_table_schemas(path)[0]


def inspect_table_schemas(path: Path) -> list[CSVSchema]:
    try:
        schemas = []
        for table in read_tables(path):
            cols = table.columns
            schemas.append(CSVSchema(
                csv_path=path, columns=cols, row_count=sum(1 for _ in table.data_rows()),
                photo_col=_pick_col(cols, PHOTO_COL_CANDIDATES),
                lat_col=_pick_col(cols, LAT_COL_CANDIDATES, ["dest_lat", "target_lat", "destination_lat"]),
                lon_col=_pick_col(cols, LON_COL_CANDIDATES, ["dest_lon", "target_lon", "destination_lon"]),
                time_col=_pick_col(cols, TIME_COL_CANDIDATES), ppm_col=_pick_col(cols, PPM_COL_CANDIDATES),
                source_sheet=table.sheet,
                header_row=table.rows[table.header_index].number if table.header_index is not None else None,
            ))
        return schemas
    except (ValueError, OSError) as exc:
        return [CSVSchema(path, [], 0, None, None, None, None, None, error=str(exc))]
