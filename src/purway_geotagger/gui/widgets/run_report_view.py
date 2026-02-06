from __future__ import annotations

from pathlib import Path
import csv
import json

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QGroupBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QPushButton, QHBoxLayout
)


def parse_manifest_failures(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    failures: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("status") or "").upper() != "FAILED":
                continue
            failures.append({
                "source_path": row.get("source_path", ""),
                "output_path": row.get("output_path", ""),
                "reason": row.get("reason", ""),
                "csv_path": row.get("csv_path", ""),
                "join_method": row.get("join_method", ""),
            })
    return failures


def load_run_summary(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def format_run_summary(summary: dict | None) -> str:
    if not summary:
        return "run_summary.json not available yet."

    mode = summary.get("run_mode") or "unknown"
    exif = summary.get("exif", {})
    exif_line = f"EXIF injected: {exif.get('success', 0)}/{exif.get('total', 0)}"

    settings = summary.get("settings", {})
    threshold = settings.get("methane_threshold")
    kmz_enabled = settings.get("methane_generate_kmz")

    lines = [f"<b>Mode</b>: {mode}", exif_line]
    if threshold is not None:
        kmz_label = "Yes" if kmz_enabled else "No"
        lines.append(f"<b>Methane threshold</b>: {threshold}")
        lines.append(f"<b>KMZ enabled</b>: {kmz_label}")

    outputs = summary.get("methane_outputs", [])
    if outputs:
        lines.append("<b>Methane outputs</b>:")
        for out in outputs:
            name = Path(out.get("source_csv", "")).name
            cleaned_status = out.get("cleaned_status", "unknown")
            cleaned_rows = out.get("cleaned_rows", 0)
            kmz_status = out.get("kmz_status", "unknown")
            extras = []
            if out.get("photo_col_missing"):
                extras.append("photo column missing → PPM-only")
            missing_rows = out.get("missing_photo_rows", 0)
            if missing_rows:
                extras.append(f"missing JPG rows: {missing_rows}")
            extra_txt = f" — {', '.join(extras)}" if extras else ""
            lines.append(
                f"• {name}: Cleaned {cleaned_status} ({cleaned_rows} rows), KMZ {kmz_status}{extra_txt}"
            )

    return "<br/>".join(lines)


def collect_output_files(summary: dict | None) -> list[dict[str, str]]:
    if not summary:
        return []
    outputs: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(kind: str, path: str | None) -> None:
        if not path:
            return
        if path in seen:
            return
        seen.add(path)
        outputs.append({"type": kind, "path": path})

    for out in summary.get("methane_outputs", []):
        _add("Cleaned CSV", out.get("cleaned_csv"))
        _add("KMZ", out.get("kmz"))

    settings = summary.get("settings", {})
    _add("Output folder", settings.get("output_photos_root"))
    _add("Encroachment output folder", settings.get("encroachment_output_base"))
    return outputs


class RunReportDialog(QDialog):
    def __init__(self, run_folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Report")
        self.resize(800, 560)
        self.run_folder = run_folder
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        summary_group = QGroupBox("Run Summary")
        summary_layout = QVBoxLayout(summary_group)
        summary = load_run_summary(self.run_folder / "run_summary.json")
        summary_label = QLabel(format_run_summary(summary))
        summary_label.setWordWrap(True)
        summary_label.setTextFormat(Qt.RichText)
        summary_layout.addWidget(summary_label)
        layout.addWidget(summary_group)

        outputs_group = QGroupBox("Outputs")
        outputs_layout = QVBoxLayout(outputs_group)
        outputs = collect_output_files(summary)
        if not outputs:
            outputs_layout.addWidget(QLabel("No outputs recorded."))
        else:
            table = QTableWidget(len(outputs), 3)
            table.setHorizontalHeaderLabels(["Type", "Path", "Action"])
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            for row_idx, row in enumerate(outputs):
                path = row.get("path", "")
                table.setItem(row_idx, 0, QTableWidgetItem(row.get("type", "")))
                path_item = QTableWidgetItem(path)
                path_item.setToolTip(path)
                table.setItem(row_idx, 1, path_item)
                btn = QPushButton("Open")
                target = Path(path)
                if not target.exists():
                    btn.setEnabled(False)
                    btn.setToolTip("File or folder not found.")
                btn.clicked.connect(lambda _checked=False, p=target: self._open_path(p))
                table.setCellWidget(row_idx, 2, btn)
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)
            outputs_layout.addWidget(table)
        layout.addWidget(outputs_group)

        failure_group = QGroupBox("Failures")
        failure_layout = QVBoxLayout(failure_group)
        failures = parse_manifest_failures(self.run_folder / "manifest.csv")
        if not failures:
            failure_layout.addWidget(QLabel("No failures recorded."))
        else:
            table = QTableWidget(len(failures), 5)
            table.setHorizontalHeaderLabels([
                "Source",
                "Output",
                "Reason",
                "CSV",
                "Join",
            ])
            for row_idx, row in enumerate(failures):
                table.setItem(row_idx, 0, QTableWidgetItem(row.get("source_path", "")))
                table.setItem(row_idx, 1, QTableWidgetItem(row.get("output_path", "")))
                table.setItem(row_idx, 2, QTableWidgetItem(row.get("reason", "")))
                table.setItem(row_idx, 3, QTableWidgetItem(row.get("csv_path", "")))
                table.setItem(row_idx, 4, QTableWidgetItem(row.get("join_method", "")))
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)
            failure_layout.addWidget(table)
        layout.addWidget(failure_group, 1)

        log_group = QGroupBox("Raw Log")
        log_group.setCheckable(True)
        log_group.setChecked(False)
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_text = self._load_log_text()
        self.log_view.setText(log_text)
        self.log_view.setVisible(False)
        log_layout.addWidget(self.log_view)
        log_group.toggled.connect(self._toggle_log)
        layout.addWidget(log_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _load_log_text(self) -> str:
        path = self.run_folder / "run_log.txt"
        if not path.exists():
            return "run_log.txt not available yet."
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return "Unable to read run_log.txt."

    def _toggle_log(self, checked: bool) -> None:
        self.log_view.setVisible(checked)

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
