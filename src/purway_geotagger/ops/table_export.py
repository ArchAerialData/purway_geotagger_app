"""Atomic, value-only table exports. Source workbooks are never saved in place."""
from __future__ import annotations

import csv
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkstemp
from typing import Iterator

from purway_geotagger.parsers.table_inputs import InputTable, CancelCheck, check_cancel


@contextmanager
def staged_output(destination: Path, cancel: CancelCheck = None) -> Iterator[Path]:
    descriptor, filename = mkstemp(prefix=".purway-", suffix=destination.suffix, dir=destination.parent)
    os.close(descriptor)
    temporary = Path(filename)
    try:
        yield temporary
        check_cancel(cancel)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def write_tables(destination: Path, tables: list[InputTable], cancel: CancelCheck = None) -> None:
    with staged_output(destination, cancel) as temporary:
        if destination.suffix.lower() == ".csv":
            with temporary.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                for row in tables[0].rows:
                    check_cancel(cancel)
                    writer.writerow(row.values)
            return

        from openpyxl import Workbook
        from openpyxl.cell import WriteOnlyCell
        from openpyxl.styles.numbers import is_date_format

        workbook = Workbook(write_only=True)
        try:
            for table in tables:
                sheet = workbook.create_sheet(table.sheet)
                sheet.sheet_state = table.sheet_state
                for row in table.rows:
                    check_cancel(cancel)
                    cells = []
                    for index, value in enumerate(row.values):
                        cell = WriteOnlyCell(sheet, value=value)
                        if isinstance(value, str):
                            cell.data_type = "s"  # Literal =... text must never become a formula.
                        if index < len(row.formats) and is_date_format(row.formats[index]):
                            cell.number_format = row.formats[index]
                        cells.append(cell)
                    sheet.append(cells)
            workbook.save(temporary)
        finally:
            # Close/clean write-only worksheet spools on cancellation or write failure.
            for sheet in workbook.worksheets:
                if not sheet.closed:
                    sheet.close()
                writer = getattr(sheet, "_writer", None)
                if writer is not None and Path(writer.out).exists():
                    writer.cleanup()
            workbook.close()
