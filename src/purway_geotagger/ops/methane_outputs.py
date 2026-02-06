from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import csv
import zipfile
import xml.etree.ElementTree as ET
from typing import Iterable

from purway_geotagger.parsers.purway_csv import (
    PPM_COL_CANDIDATES,
    LAT_COL_CANDIDATES,
    LON_COL_CANDIDATES,
    PHOTO_COL_CANDIDATES,
)


@dataclass
class MethaneCsvResult:
    source_csv: Path
    cleaned_csv: Path | None
    cleaned_status: str  # success|failed|skipped
    cleaned_rows: int = 0
    cleaned_error: str = ""
    missing_photo_rows: int = 0
    missing_photo_names: list[str] = field(default_factory=list)
    photo_col_missing: bool = False
    kmz: Path | None = None
    kmz_status: str = "skipped"  # success|failed|skipped
    kmz_rows: int = 0
    kmz_error: str = ""


@dataclass
class CleanedCsvInfo:
    kept_rows: int
    fieldnames: list[str] | None
    photo_col: str | None
    missing_photo_rows: int = 0
    missing_photo_names: list[str] = field(default_factory=list)
    used_photo_filter: bool = False


def cleaned_csv_path(path: Path, threshold: int) -> Path:
    return path.with_name(f"{path.stem}_Cleaned_{threshold}-PPM.csv")


def kmz_path_for_cleaned(cleaned_csv: Path) -> Path:
    return cleaned_csv.with_suffix(".kmz")


def generate_methane_outputs(
    csv_paths: Iterable[Path],
    threshold: int,
    generate_kmz: bool,
) -> list[MethaneCsvResult]:
    results: list[MethaneCsvResult] = []

    for csv_path in csv_paths:
        result = MethaneCsvResult(
            source_csv=csv_path,
            cleaned_csv=None,
            cleaned_status="skipped",
            kmz=None,
            kmz_status="skipped",
        )

        try:
            info = _write_cleaned_csv(csv_path, threshold)
            if info.fieldnames is None:
                result.cleaned_status = "skipped"
                result.cleaned_error = "No PPM column found."
                results.append(result)
                continue

            cleaned_csv = cleaned_csv_path(csv_path, threshold)
            result.cleaned_csv = cleaned_csv
            result.cleaned_rows = info.kept_rows
            result.cleaned_status = "success"
            result.missing_photo_rows = info.missing_photo_rows
            result.missing_photo_names = info.missing_photo_names
            result.photo_col_missing = not info.used_photo_filter

            if generate_kmz:
                lat_col = _pick_col(info.fieldnames, LAT_COL_CANDIDATES)
                lon_col = _pick_col(info.fieldnames, LON_COL_CANDIDATES)
                ppm_col = _pick_col(info.fieldnames, PPM_COL_CANDIDATES)
                if not lat_col or not lon_col or not ppm_col:
                    result.kmz_status = "failed"
                    result.kmz_error = "KMZ requires latitude, longitude, and PPM columns."
                else:
                    kmz_path = kmz_path_for_cleaned(cleaned_csv)
                    result.kmz = kmz_path
                    placemark_count = _write_kmz(cleaned_csv, kmz_path, lat_col, lon_col, ppm_col)
                    result.kmz_rows = placemark_count
                    result.kmz_status = "success"
        except UnicodeDecodeError:
            result.cleaned_status = "failed"
            result.cleaned_error = "CSV is not UTF-8 encoded."
        except Exception as exc:  # pragma: no cover - safety net
            result.cleaned_status = "failed"
            result.cleaned_error = str(exc)

        results.append(result)

    return results


def _write_cleaned_csv(csv_path: Path, threshold: int) -> CleanedCsvInfo:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return CleanedCsvInfo(kept_rows=0, fieldnames=None, photo_col=None)
        ppm_col = _pick_col(fieldnames, PPM_COL_CANDIDATES)
        if not ppm_col:
            return CleanedCsvInfo(kept_rows=0, fieldnames=None, photo_col=None)

        photo_col = _pick_col(fieldnames, PHOTO_COL_CANDIDATES)
        use_photo_filter = bool(photo_col)
        jpg_names: set[str] = set()
        jpg_stems: set[str] = set()
        if use_photo_filter:
            jpg_names, jpg_stems = _collect_jpg_names(csv_path.parent)

        cleaned_path = cleaned_csv_path(csv_path, threshold)
        cleaned_path.parent.mkdir(parents=True, exist_ok=True)
        with cleaned_path.open("w", encoding="utf-8", newline="") as out_f:
            out_fieldnames = _reorder_fieldnames(fieldnames, photo_col)
            writer = csv.DictWriter(out_f, fieldnames=out_fieldnames)
            writer.writeheader()
            kept = 0
            missing_rows = 0
            missing_names: list[str] = []
            for row in reader:
                ppm_val = _safe_float(row.get(ppm_col))
                if ppm_val is None or ppm_val < threshold:
                    continue
                if use_photo_filter:
                    if not _row_matches_photo(row.get(photo_col), jpg_names, jpg_stems):
                        missing_rows += 1
                        if len(missing_names) < 20:
                            missing_names.append(str(row.get(photo_col) or "").strip() or "<blank>")
                        continue
                writer.writerow(row)
                kept += 1
            return CleanedCsvInfo(
                kept_rows=kept,
                fieldnames=fieldnames,
                photo_col=photo_col,
                missing_photo_rows=missing_rows,
                missing_photo_names=missing_names,
                used_photo_filter=use_photo_filter,
            )


def _write_kmz(
    cleaned_csv: Path,
    kmz_path: Path,
    lat_col: str,
    lon_col: str,
    ppm_col: str,
) -> int:
    placemarks = []
    with cleaned_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = _safe_float(row.get(lat_col))
            lon = _safe_float(row.get(lon_col))
            if lat is None or lon is None:
                continue
            ppm_val = row.get(ppm_col)
            label = str(ppm_val).strip() if ppm_val is not None else ""
            placemarks.append((lat, lon, label))

    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, "Document")
    name = ET.SubElement(doc, "name")
    name.text = cleaned_csv.stem
    for lat, lon, label in placemarks:
        pm = ET.SubElement(doc, "Placemark")
        pm_name = ET.SubElement(pm, "name")
        pm_name.text = label
        point = ET.SubElement(pm, "Point")
        coords = ET.SubElement(point, "coordinates")
        coords.text = f"{lon},{lat},0"

    kml_bytes = ET.tostring(kml, encoding="utf-8", xml_declaration=True)
    kmz_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)

    return len(placemarks)


def _pick_col(cols: list[str], candidates: list[str]) -> str | None:
    cols_l = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        if cand in cols_l:
            return cols_l[cand]
    for c in cols:
        cl = c.lower()
        if any(cand in cl for cand in candidates):
            return c
    return None


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _collect_jpg_names(folder: Path) -> tuple[set[str], set[str]]:
    names: set[str] = set()
    stems: set[str] = set()
    for child in folder.iterdir():
        if not child.is_file():
            continue
        suffix = child.suffix.lower()
        if suffix not in {".jpg", ".jpeg"}:
            continue
        name = child.name.lower()
        names.add(name)
        stems.add(child.stem.lower())
    return names, stems


def _row_matches_photo(value: object, jpg_names: set[str], jpg_stems: set[str]) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    name = Path(text).name
    name_l = name.lower()
    stem_l = Path(name).stem.lower()
    if name_l in jpg_names:
        return True
    if stem_l in jpg_stems:
        return True
    return False


def _reorder_fieldnames(fieldnames: list[str], photo_col: str | None) -> list[str]:
    if not fieldnames or not photo_col or photo_col not in fieldnames:
        return fieldnames
    if "time" not in (c.lower().strip() for c in fieldnames):
        return fieldnames
    time_col = _pick_col(fieldnames, ["time"])
    if not time_col:
        return fieldnames
    # Move photo_col to immediately after time_col for cleaned CSV output.
    new_fields = [c for c in fieldnames if c not in (photo_col,)]
    try:
        time_idx = new_fields.index(time_col)
    except ValueError:
        return fieldnames
    new_fields.insert(time_idx + 1, photo_col)
    return new_fields
