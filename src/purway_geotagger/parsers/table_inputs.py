"""Read CSVs and value-focused XLSX sheets without changing source files."""
from __future__ import annotations

import csv
import math
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from purway_geotagger.parsers.columns import (
    PPM_COL_CANDIDATES, REL_ALT_COL_CANDIDATES, ALT_COL_CANDIDATES, PHOTO_COL_CANDIDATES,
    TIME_COL_CANDIDATES, LAT_COL_CANDIDATES, LON_COL_CANDIDATES,
    normalize_header, validate_mappings,
)
from purway_geotagger.util.errors import UserCancelledError

CancelCheck = Callable[[], bool] | None


def check_cancel(cancel: CancelCheck) -> None:
    if cancel and cancel():
        raise UserCancelledError()


def finite_number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


@dataclass
class TableRow:
    number: int
    values: list[object]
    formats: list[str] = field(default_factory=list)


@dataclass
class InputTable:
    path: Path
    sheet: str
    rows: list[TableRow]
    header_index: int | None
    columns: list[str]
    sheet_state: str = "visible"

    def data_rows(self) -> Iterator[tuple[TableRow, dict[str, object]]]:
        if self.header_index is None:
            return
        for row in self.rows[self.header_index + 1:]:
            if any(v not in (None, "") for v in row.values):
                yield row, dict(zip(self.columns, row.values))


def _validate_columns(columns: list[str]) -> None:
    named = [normalize_header(c) for c in columns if str(c).strip()]
    if len(named) != len(set(named)):
        raise ValueError("Duplicate column headers are ambiguous.")
    validate_mappings(columns)


def _xlsx_header(rows: list[TableRow]) -> int | None:
    candidates = []
    ppm = {normalize_header(c) for c in PPM_COL_CANDIDATES}
    others = {normalize_header(c) for c in (
        REL_ALT_COL_CANDIDATES + ALT_COL_CANDIDATES + PHOTO_COL_CANDIDATES + TIME_COL_CANDIDATES
        + LAT_COL_CANDIDATES + LON_COL_CANDIDATES
    )}
    for index, row in enumerate(rows):
        names = {normalize_header(v) for v in row.values if isinstance(v, str)}
        if names & ppm and names & others:
            candidates.append(index)
    if len(candidates) > 1:
        raise ValueError(f"Multiple possible table headers at rows {[rows[i].number for i in candidates]}; one table per sheet is supported.")
    return candidates[0] if candidates else None


def _cached_empty_strings(path: Path, worksheet_path: str, cancel: CancelCheck) -> set[str]:
    """Distinguish a cached empty string from a formula with no cached result.

    openpyxl returns None for both. Its pinned reader exposes the worksheet ZIP path;
    inspect only that sheet when this otherwise ambiguous case actually occurs.
    """
    from defusedxml.ElementTree import iterparse
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    cells = set()
    with zipfile.ZipFile(path) as archive, archive.open(worksheet_path) as stream:
        for _, element in iterparse(stream, events=("end",)):
            if element.tag == ns + "c":
                check_cancel(cancel)
                value = element.find(ns + "v")
                if (element.get("t") == "str" and element.find(ns + "f") is not None
                        and value is not None and value.text in (None, "")):
                    cells.add(element.get("r"))
                element.clear()
            elif element.tag == ns + "row":
                element.clear()
    return cells


def read_tables(path: Path, cancel: CancelCheck = None) -> list[InputTable]:
    try:
        return _read_tables(path, cancel)
    except (UserCancelledError, OSError, ValueError):
        raise
    except Exception as exc:
        raise ValueError(f"{path.name}: cannot read metadata table: {exc}") from exc


def _read_tables(path: Path, cancel: CancelCheck = None) -> list[InputTable]:
    check_cancel(cancel)
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            rows = []
            for number, values in enumerate(reader, 1):
                check_cancel(cancel)
                rows.append(TableRow(number, values))
        columns = [str(v) for v in rows[0].values] if rows else []
        _validate_columns(columns)
        if any(len(row.values) > len(columns) for row in rows[1:]):
            raise ValueError(f"{path.name}: a data row has more values than the header.")
        return [InputTable(path, "", rows, 0 if rows else None, columns)]
    if path.suffix.lower() != ".xlsx":
        raise ValueError(f"Unsupported table format: {path.suffix}; use CSV or XLSX.")

    # Import lazily so the existing CSV workflow does not load Excel dependencies.
    from openpyxl import load_workbook
    from openpyxl.xml import DEFUSEDXML
    if not DEFUSEDXML:
        raise RuntimeError("XLSX support requires defusedxml.")

    formulas = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    try:
        cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
        try:
            tables = []
            for sheet in formulas:
                check_cancel(cancel)
                rows = []
                empty_strings = None
                try:
                    for number, (raw_cells, value_cells) in enumerate(zip(sheet.iter_rows(), cached[sheet.title].iter_rows()), 1):
                        check_cancel(cancel)
                        values, formats = [], []
                        for raw, cell in zip(raw_cells, value_cells):
                            value = cell.value
                            if raw.data_type == "f" and cell.value is None:
                                if cell.data_type == "str" and empty_strings is None:
                                    empty_strings = _cached_empty_strings(path, sheet._worksheet_path, cancel)
                                if raw.coordinate not in (empty_strings or set()):
                                    raise ValueError(f"{raw.coordinate}: formula has no saved result. Recalculate and save the workbook in Excel or LibreOffice first.")
                                value = ""
                            values.append(value)
                            formats.append(cell.number_format)
                        rows.append(TableRow(number, values, formats))
                    header = _xlsx_header(rows)
                    columns = [str(v) if v is not None else "" for v in rows[header].values] if header is not None else []
                    if header is not None:
                        _validate_columns(columns)
                        for row in rows[header + 1:]:
                            row.values.extend([None] * max(0, len(columns) - len(row.values)))
                    tables.append(InputTable(path, sheet.title, rows, header, columns, sheet.sheet_state))
                except ValueError as exc:
                    raise ValueError(f"{path.name} / {sheet.title}: {exc}") from exc
            return tables
        finally:
            cached.close()
    finally:
        formulas.close()
