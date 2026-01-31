from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
)

from purway_geotagger.core.preview import PreviewResult


class PreviewDialog(QDialog):
    def __init__(self, result: PreviewResult, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Validation Preview")
        self.resize(900, 400)

        layout = QVBoxLayout(self)
        summary = QLabel(f"Scanned photos: {result.scanned_photos}, CSVs: {result.scanned_csvs}. Showing {len(result.rows)} rows.")
        layout.addWidget(summary)

        table = QTableWidget()
        headers = ["Status", "Join", "Photo", "CSV", "Lat", "Lon", "PPM", "DateTime", "Reason"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(result.rows))

        for i, r in enumerate(result.rows):
            table.setItem(i, 0, QTableWidgetItem(r.status))
            table.setItem(i, 1, QTableWidgetItem(r.join_method))
            table.setItem(i, 2, QTableWidgetItem(r.photo_path))
            table.setItem(i, 3, QTableWidgetItem(r.csv_path))
            table.setItem(i, 4, QTableWidgetItem(r.lat))
            table.setItem(i, 5, QTableWidgetItem(r.lon))
            table.setItem(i, 6, QTableWidgetItem(r.ppm))
            table.setItem(i, 7, QTableWidgetItem(r.datetime_original))
            table.setItem(i, 8, QTableWidgetItem(r.reason))

        table.resizeColumnsToContents()
        layout.addWidget(table)
