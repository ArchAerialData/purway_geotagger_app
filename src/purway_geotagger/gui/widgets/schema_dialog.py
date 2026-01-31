from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
)

from purway_geotagger.parsers.purway_csv import CSVSchema


class SchemaDialog(QDialog):
    def __init__(self, schemas: list[CSVSchema], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CSV Schema Inspector")
        self.resize(900, 300)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"CSVs inspected: {len(schemas)}"))

        table = QTableWidget()
        headers = ["CSV", "Rows", "Photo", "Lat", "Lon", "Time", "PPM", "Columns"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(schemas))

        for i, s in enumerate(schemas):
            table.setItem(i, 0, QTableWidgetItem(str(s.csv_path)))
            table.setItem(i, 1, QTableWidgetItem(str(s.row_count)))
            table.setItem(i, 2, QTableWidgetItem(s.photo_col or ""))
            table.setItem(i, 3, QTableWidgetItem(s.lat_col or ""))
            table.setItem(i, 4, QTableWidgetItem(s.lon_col or ""))
            table.setItem(i, 5, QTableWidgetItem(s.time_col or ""))
            table.setItem(i, 6, QTableWidgetItem(s.ppm_col or ""))
            table.setItem(i, 7, QTableWidgetItem(", ".join(s.columns)))

        table.resizeColumnsToContents()
        layout.addWidget(table)
