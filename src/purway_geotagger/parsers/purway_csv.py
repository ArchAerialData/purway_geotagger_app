from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Optional

from purway_geotagger.util.timeparse import parse_csv_timestamp, parse_photo_timestamp_from_name, format_exif_datetime
from purway_geotagger.util.errors import CorrelationError

PHOTO_COL_CANDIDATES = ["photo", "image", "filename", "file", "sourcefile"]
LAT_COL_CANDIDATES = ["latitude", "lat", "gpslatitude"]
LON_COL_CANDIDATES = ["longitude", "lon", "lng", "gpslongitude"]
TIME_COL_CANDIDATES = ["timestamp", "time", "datetime", "date"]
PPM_COL_CANDIDATES = ["concentration", "ppm", "methane", "ch4"]

REASON_NO_PHOTO_OR_TIMESTAMP = "no explicit Photo column correlation and no timestamped CSV rows available"
REASON_NO_FILENAME_TIMESTAMP = "no filename timestamp and no explicit Photo column correlation"
REASON_AMBIGUOUS_TIMESTAMP = "ambiguous timestamp join"

def _pick_col(cols: list[str], candidates: list[str]) -> Optional[str]:
    cols_l = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        if cand in cols_l:
            return cols_l[cand]
    # substring fallback
    for c in cols:
        cl = c.lower()
        if any(cand in cl for cand in candidates):
            return c
    return None

@dataclass(frozen=True)
class PurwayRecord:
    csv_path: Path
    lat: float
    lon: float
    ppm: float
    timestamp: object  # datetime or None
    photo_ref: str | None

@dataclass(frozen=True)
class PhotoMatch:
    csv_path: str
    lat: float
    lon: float
    ppm: float
    datetime_original: str | None
    image_description: str
    join_method: str  # FILENAME|TIMESTAMP

class PurwayCSVIndex:
    def __init__(self, records: list[PurwayRecord]) -> None:
        self.records = records

        # Precompute maps for faster joins
        self.by_photo: dict[str, PurwayRecord] = {}
        self.by_time: list[PurwayRecord] = []
        for r in records:
            if r.photo_ref:
                self.by_photo[Path(r.photo_ref).name] = r
            if r.timestamp:
                self.by_time.append(r)

    @classmethod
    def from_csv_files(cls, csv_files: list[Path]) -> "PurwayCSVIndex":
        records: list[PurwayRecord] = []
        for p in csv_files:
            recs = _parse_single_csv(p)
            records.extend(recs)
        return cls(records=records)

    def match_photo(self, photo_path: Path, max_join_delta_seconds: int) -> PhotoMatch:
        # Step A: filename join
        if self.by_photo:
            r = self.by_photo.get(photo_path.name)
            if r:
                return _to_match(r, join_method="FILENAME")

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

        return _to_match(best, join_method="TIMESTAMP")

def _to_match(r: PurwayRecord, join_method: str) -> PhotoMatch:
    dto = format_exif_datetime(r.timestamp) if r.timestamp else None
    ppm_int = int(round(r.ppm))
    desc = f"ppm={ppm_int}; source_csv={r.csv_path.name}"
    return PhotoMatch(
        csv_path=str(r.csv_path),
        lat=r.lat,
        lon=r.lon,
        ppm=r.ppm,
        datetime_original=dto,
        image_description=desc,
        join_method=join_method,
    )

def _parse_single_csv(path: Path) -> list[PurwayRecord]:
    # Read with BOM tolerance
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return []
        cols = reader.fieldnames or list(rows[0].keys())

    photo_col = _pick_col(cols, PHOTO_COL_CANDIDATES)
    lat_col = _pick_col(cols, LAT_COL_CANDIDATES)
    lon_col = _pick_col(cols, LON_COL_CANDIDATES)
    time_col = _pick_col(cols, TIME_COL_CANDIDATES)
    ppm_col = _pick_col(cols, PPM_COL_CANDIDATES)

    if not lat_col or not lon_col:
        return []  # ignore CSVs without coordinate columns

    out: list[PurwayRecord] = []
    for r in rows:
        try:
            lat = float(str(r.get(lat_col, "")).strip())
            lon = float(str(r.get(lon_col, "")).strip())
        except ValueError:
            continue

        ppm = 0.0
        if ppm_col and r.get(ppm_col) not in (None, ""):
            try:
                ppm = float(str(r.get(ppm_col)).strip())
            except ValueError:
                ppm = 0.0

        ts = None
        if time_col and r.get(time_col):
            try:
                ts = parse_csv_timestamp(str(r.get(time_col)))
            except Exception:
                ts = None

        photo_ref = str(r.get(photo_col)).strip() if photo_col and r.get(photo_col) else None

        out.append(PurwayRecord(
            csv_path=path,
            lat=lat,
            lon=lon,
            ppm=ppm,
            timestamp=ts,
            photo_ref=photo_ref,
        ))
    return out


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


def inspect_csv_schema(path: Path) -> CSVSchema:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = reader.fieldnames or (list(rows[0].keys()) if rows else [])

    photo_col = _pick_col(cols, PHOTO_COL_CANDIDATES)
    lat_col = _pick_col(cols, LAT_COL_CANDIDATES)
    lon_col = _pick_col(cols, LON_COL_CANDIDATES)
    time_col = _pick_col(cols, TIME_COL_CANDIDATES)
    ppm_col = _pick_col(cols, PPM_COL_CANDIDATES)

    return CSVSchema(
        csv_path=path,
        columns=cols,
        row_count=len(rows),
        photo_col=photo_col,
        lat_col=lat_col,
        lon_col=lon_col,
        time_col=time_col,
        ppm_col=ppm_col,
    )
