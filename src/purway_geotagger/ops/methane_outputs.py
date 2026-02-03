from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import zipfile
import xml.etree.ElementTree as ET
from typing import Iterable

from purway_geotagger.parsers.purway_csv import PPM_COL_CANDIDATES, LAT_COL_CANDIDATES, LON_COL_CANDIDATES


@dataclass
class MethaneCsvResult:
    source_csv: Path
    cleaned_csv: Path | None
    cleaned_status: str  # success|failed|skipped
    cleaned_rows: int = 0
    cleaned_error: str = ""
    kmz: Path | None = None
    kmz_status: str = "skipped"  # success|failed|skipped
    kmz_rows: int = 0
    kmz_error: str = ""


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
            cleaned_rows, cols = _write_cleaned_csv(csv_path, threshold)
            if cols is None:
                result.cleaned_status = "skipped"
                result.cleaned_error = "No PPM column found."
                results.append(result)
                continue

            cleaned_csv = cleaned_csv_path(csv_path, threshold)
            result.cleaned_csv = cleaned_csv
            result.cleaned_rows = cleaned_rows
            result.cleaned_status = "success"

            if generate_kmz:
                lat_col = _pick_col(cols, LAT_COL_CANDIDATES)
                lon_col = _pick_col(cols, LON_COL_CANDIDATES)
                ppm_col = _pick_col(cols, PPM_COL_CANDIDATES)
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


def _write_cleaned_csv(csv_path: Path, threshold: int) -> tuple[int, list[str] | None]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return 0, None
        ppm_col = _pick_col(fieldnames, PPM_COL_CANDIDATES)
        if not ppm_col:
            return 0, None

        cleaned_path = cleaned_csv_path(csv_path, threshold)
        cleaned_path.parent.mkdir(parents=True, exist_ok=True)
        with cleaned_path.open("w", encoding="utf-8", newline="") as out_f:
            writer = csv.DictWriter(out_f, fieldnames=fieldnames)
            writer.writeheader()
            kept = 0
            for row in reader:
                ppm_val = _safe_float(row.get(ppm_col))
                if ppm_val is None or ppm_val < threshold:
                    continue
                writer.writerow(row)
                kept += 1
            return kept, fieldnames


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
