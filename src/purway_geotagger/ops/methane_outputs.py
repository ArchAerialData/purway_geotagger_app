from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from pathlib import Path
from typing import Iterable
import zipfile
import xml.etree.ElementTree as ET

from purway_geotagger.core.pac_calculator import calculate_pac
from purway_geotagger.parsers.columns import (
    PPM_COL_CANDIDATES, REL_ALT_COL_CANDIDATES, PHOTO_COL_CANDIDATES,
    LAT_COL_CANDIDATES, LON_COL_CANDIDATES, pick_column, pac_column,
)
from purway_geotagger.parsers.table_inputs import (
    InputTable, TableRow, read_tables, finite_number, check_cancel, CancelCheck,
)
from purway_geotagger.ops.table_export import write_tables, staged_output
from purway_geotagger.util.errors import UserCancelledError
from purway_geotagger.util.paths import is_macos_artifact


@dataclass
class SheetOutputStats:
    source_sheet: str
    header_row: int | None = None
    input_rows: int = 0
    calibration_excluded: int = 0
    threshold_excluded: int = 0
    invalid_methane_excluded: int = 0
    missing_photo_rows: int = 0
    retained_rows: int = 0
    pac_preserved: int = 0
    pac_calculated: int = 0
    pac_unavailable: int = 0
    altitude_unavailable: int = 0
    photo_col_missing: bool = False
    missing_photo_names: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MethaneCsvResult:
    """Legacy CSV-named fields also carry XLSX paths for summary compatibility."""
    source_csv: Path
    cleaned_csv: Path | None
    cleaned_status: str
    cleaned_rows: int = 0
    cleaned_error: str = ""
    missing_photo_rows: int = 0
    missing_photo_names: list[str] = field(default_factory=list)
    photo_col_missing: bool = False
    kmz: Path | None = None
    kmz_status: str = "skipped"
    kmz_rows: int = 0
    kmz_error: str = ""
    source_format: str = "csv"
    sheets: list[dict] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def cleaned_csv_path(path: Path, threshold: int) -> Path:
    return path.with_name(f"{path.stem}_Cleaned_{threshold}-PPM{path.suffix.lower()}")


def kmz_path_for_cleaned(cleaned_csv: Path) -> Path:
    if cleaned_csv.suffix.lower() == ".xlsx":
        return cleaned_csv.with_name(cleaned_csv.stem + "_XLSX.kmz")
    return cleaned_csv.with_suffix(".kmz")


def generate_methane_outputs(
    csv_paths: Iterable[Path], threshold: int, generate_kmz: bool,
    exclude_calibration: bool = True, cancel_cb: CancelCheck = None,
    completed_results: list[MethaneCsvResult] | None = None,
) -> list[MethaneCsvResult]:
    # Keep already-published files visible in the run summary if a later file is cancelled.
    results = completed_results if completed_results is not None else []
    for path in csv_paths:
        check_cancel(cancel_cb)
        result = MethaneCsvResult(path, None, "skipped", source_format=path.suffix.lower().lstrip("."))
        results.append(result)
        try:
            tables = read_tables(path, cancel_cb)
            cleaned, stats = [], []
            photos = _collect_jpg_names(path.parent)
            for table in tables:
                output, info = _clean_table(table, threshold, exclude_calibration, photos, cancel_cb)
                cleaned.append(output)
                stats.append(info)
            if not any(s.header_row is not None for s in stats):
                result.cleaned_error = "No methane/PPM data table found."
                continue
            destination = cleaned_csv_path(path, threshold)
            write_tables(destination, cleaned, cancel_cb)
            result.cleaned_csv = destination
            result.cleaned_status = "success"
            result.sheets = [asdict(s) for s in stats]
            count_names = ("input_rows", "calibration_excluded", "threshold_excluded", "invalid_methane_excluded",
                           "missing_photo_rows", "retained_rows", "pac_preserved", "pac_calculated",
                           "pac_unavailable", "altitude_unavailable")
            result.counts = {name: sum(getattr(s, name) for s in stats) for name in count_names}
            result.cleaned_rows = result.counts["retained_rows"]
            result.missing_photo_rows = result.counts["missing_photo_rows"]
            result.missing_photo_names = [name for s in stats for name in s.missing_photo_names][:20]
            result.photo_col_missing = any(s.photo_col_missing for s in stats if s.header_row is not None)
            result.warnings = [f"{s.source_sheet or path.name}: {warning}" for s in stats for warning in s.warnings]
            if generate_kmz:
                try:
                    kmz = kmz_path_for_cleaned(destination)
                    result.kmz_rows = _write_tables_kmz(cleaned, kmz, cancel_cb)
                    result.kmz, result.kmz_status = kmz, "success"
                except UserCancelledError:
                    result.kmz_status = "cancelled"
                    raise
                except Exception as exc:
                    result.kmz_status, result.kmz_error = "failed", str(exc)
        except UserCancelledError:
            if result.cleaned_status != "success":
                result.cleaned_status = "cancelled"
            raise
        except Exception as exc:
            result.cleaned_status, result.cleaned_error = "failed", str(exc)
    return results


def _clean_table(table: InputTable, threshold: int, exclude_calibration: bool,
                 photos: tuple[set[str], set[str]], cancel: CancelCheck) -> tuple[InputTable, SheetOutputStats]:
    stats = SheetOutputStats(table.sheet)
    ppm_col = pick_column(table.columns, PPM_COL_CANDIDATES)
    if table.header_index is None or not ppm_col:
        stats.warnings.append("No methane table; sheet copied as saved values without filtering.")
        return table, stats
    stats.header_row = table.rows[table.header_index].number
    altitude_col = pick_column(table.columns, REL_ALT_COL_CANDIDATES)
    photo_col = pick_column(table.columns, PHOTO_COL_CANDIDATES)
    pac_col = pac_column(table.columns)
    stats.photo_col_missing = not bool(photo_col)
    columns = list(table.columns) + ([] if pac_col else ["PAC"])
    # Preserve column order, including an original PAC column's exact position.
    output_rows = list(table.rows[:table.header_index])
    output_rows.append(TableRow(stats.header_row, columns))
    for original, values in table.data_rows():
        check_cancel(cancel)
        stats.input_rows += 1
        ppm = finite_number(values.get(ppm_col))
        altitude = finite_number(values.get(altitude_col)) if altitude_col else None
        if altitude is None:
            stats.altitude_unavailable += 1
        if exclude_calibration and ppm is not None and ppm > 0 and altitude is not None and altitude < 1:
            stats.calibration_excluded += 1
            continue
        if ppm is None:
            stats.invalid_methane_excluded += 1
            continue
        if ppm < threshold:
            stats.threshold_excluded += 1
            continue
        if photo_col and not _row_matches_photo(values.get(photo_col), *photos):
            stats.missing_photo_rows += 1
            if len(stats.missing_photo_names) < 20:
                stats.missing_photo_names.append(str(values.get(photo_col) or "<blank>"))
            continue
        cells = list(original.values) + [None] * (len(table.columns) - len(original.values))
        if pac_col:
            stats.pac_preserved += 1
        else:
            pac = calculate_pac(ppm, altitude)
            cells.append(pac)
            if pac is None:
                stats.pac_unavailable += 1
            else:
                stats.pac_calculated += 1
        output_rows.append(TableRow(original.number, cells, original.formats))
        stats.retained_rows += 1
    if stats.altitude_unavailable:
        stats.warnings.append(f"Relative altitude unavailable on {stats.altitude_unavailable} rows; calibration cannot be determined for those rows.")
    if stats.pac_unavailable:
        stats.warnings.append(f"PAC left blank on {stats.pac_unavailable} retained rows because calculation inputs are unavailable or invalid.")
    return replace(table, rows=output_rows, columns=columns), stats


def _write_tables_kmz(tables: list[InputTable], destination: Path, cancel: CancelCheck) -> int:
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, "Document")
    ET.SubElement(doc, "name").text = destination.stem
    count = 0
    for table in tables:
        ppm_col = pick_column(table.columns, PPM_COL_CANDIDATES)
        if table.header_index is None or not ppm_col:
            continue
        lat_col = pick_column(table.columns, LAT_COL_CANDIDATES, ["dest_lat", "target_lat", "destination_lat"])
        lon_col = pick_column(table.columns, LON_COL_CANDIDATES, ["dest_lon", "target_lon", "destination_lon"])
        if not lat_col or not lon_col:
            raise ValueError(f"{table.sheet or table.path.name}: KMZ requires latitude, longitude, and PPM columns.")
        parent = doc
        if table.sheet:
            parent = ET.SubElement(doc, "Folder")
            ET.SubElement(parent, "name").text = table.sheet
        for _, row in table.data_rows():
            check_cancel(cancel)
            lat, lon = finite_number(row.get(lat_col)), finite_number(row.get(lon_col))
            if lat is None or lon is None:
                continue
            mark = ET.SubElement(parent, "Placemark")
            ET.SubElement(mark, "name").text = str(row.get(ppm_col) or "")
            point = ET.SubElement(mark, "Point")
            ET.SubElement(point, "coordinates").text = f"{lon},{lat},0"
            count += 1
    with staged_output(destination, cancel) as temporary:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("doc.kml", ET.tostring(kml, encoding="utf-8", xml_declaration=True))
    return count


def _collect_jpg_names(folder: Path) -> tuple[set[str], set[str]]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"} and not is_macos_artifact(p)]
    return {p.name.lower() for p in files}, {p.stem.lower() for p in files}


def _row_matches_photo(value: object, jpg_names: set[str], jpg_stems: set[str]) -> bool:
    if value is None or not str(value).strip():
        return False
    name = Path(str(value).strip().replace("\\", "/")).name
    return name.lower() in jpg_names or Path(name).stem.lower() in jpg_stems
