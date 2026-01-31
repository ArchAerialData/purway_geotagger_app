from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from purway_geotagger.core.scanner import scan_inputs, ScanResult
from purway_geotagger.parsers.purway_csv import PurwayCSVIndex, inspect_csv_schema, CSVSchema
from purway_geotagger.util.errors import CorrelationError


@dataclass
class PreviewRow:
    photo_path: str
    status: str  # MATCHED|FAILED
    join_method: str
    csv_path: str
    lat: str
    lon: str
    ppm: str
    datetime_original: str
    reason: str


@dataclass
class PreviewResult:
    scanned_photos: int
    scanned_csvs: int
    rows: list[PreviewRow]
    schemas: list[CSVSchema]


def build_preview(
    inputs: list[Path],
    max_rows: int,
    max_join_delta_seconds: int,
) -> PreviewResult:
    scan: ScanResult = scan_inputs(inputs)
    schemas = [inspect_csv_schema(p) for p in scan.csvs]
    index = PurwayCSVIndex.from_csv_files(scan.csvs)

    rows: list[PreviewRow] = []
    for p in scan.photos[:max_rows]:
        try:
            match = index.match_photo(photo_path=p, max_join_delta_seconds=max_join_delta_seconds)
            rows.append(
                PreviewRow(
                    photo_path=str(p),
                    status="MATCHED",
                    join_method=match.join_method,
                    csv_path=match.csv_path,
                    lat=str(match.lat),
                    lon=str(match.lon),
                    ppm=str(match.ppm),
                    datetime_original=match.datetime_original or "",
                    reason="",
                )
            )
        except CorrelationError as e:
            rows.append(
                PreviewRow(
                    photo_path=str(p),
                    status="FAILED",
                    join_method="NONE",
                    csv_path="",
                    lat="",
                    lon="",
                    ppm="",
                    datetime_original="",
                    reason=str(e),
                )
            )

    return PreviewResult(
        scanned_photos=len(scan.photos),
        scanned_csvs=len(scan.csvs),
        rows=rows,
        schemas=schemas,
    )
