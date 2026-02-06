from __future__ import annotations

from pathlib import Path
import csv
import json

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QGroupBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QPushButton, QHBoxLayout, QWidget, QHeaderView
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


def parse_manifest_outputs(path: Path) -> list[Path]:
    if not path.exists():
        return []
    outputs: list[Path] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("status") or "").upper() != "SUCCESS":
                continue
            out_path = (row.get("output_path") or "").strip()
            if not out_path:
                continue
            outputs.append(Path(out_path))
    return outputs


def collect_output_files(summary: dict | None, run_folder: Path) -> list[dict[str, str]]:
    if not summary:
        return []
    outputs: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(kind: str, path: Path | None) -> None:
        if not path:
            return
        path_str = str(path)
        if path_str in seen:
            return
        seen.add(path_str)
        outputs.append({"type": kind, "path": path_str})

    def _under_base(path: Path, base: Path | None) -> bool:
        if base is None:
            return True
        try:
            path.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

    run_mode = (summary.get("run_mode") or "").lower()
    settings = summary.get("settings", {})

    if run_mode in ("methane", "combined"):
        for out in summary.get("methane_outputs", []):
            cleaned_path = out.get("cleaned_csv")
            if out.get("cleaned_status") == "success" and cleaned_path:
                path = Path(cleaned_path)
                if path.exists():
                    _add("Cleaned CSV", path)
            kmz_path = out.get("kmz")
            if out.get("kmz_status") == "success" and kmz_path:
                path = Path(kmz_path)
                if path.exists():
                    _add("KMZ", path)

    if run_mode in ("encroachment", "combined"):
        enc_base = settings.get("encroachment_output_base") or settings.get("output_photos_root")
        enc_base_path = Path(enc_base) if enc_base else None
        for out_path in parse_manifest_outputs(run_folder / "manifest.csv"):
            if _under_base(out_path, enc_base_path):
                if out_path.exists():
                    _add("Photo", out_path)

    return outputs


class _OpenFilePill(QWidget):
    clicked = Signal()

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("cssClass", "open_file_pill")
        self.setFixedSize(110, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.label = QLabel(text)
        self.label.setProperty("cssClass", "open_file_pill_label")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addStretch(1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.label.setEnabled(enabled)
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)


class RunReportDialog(QDialog):
    def __init__(self, run_folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Report")
        self.resize(980, 720)
        self.setMinimumSize(900, 640)
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
        outputs = collect_output_files(summary, self.run_folder)
        if not outputs:
            outputs_layout.addWidget(QLabel("No outputs recorded."))
        else:
            table = QTableWidget(len(outputs), 3)
            table.setHorizontalHeaderLabels(["Type", "File", "Action"])
            table.setProperty("cssClass", "outputs_table")
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.NoSelection)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.verticalHeader().setVisible(False)
            for row_idx, row in enumerate(outputs):
                path = row.get("path", "")
                table.setItem(row_idx, 0, QTableWidgetItem(row.get("type", "")))
                name_item = QTableWidgetItem(Path(path).name)
                name_item.setToolTip(path)
                table.setItem(row_idx, 1, name_item)
                btn = _OpenFilePill("Open File")
                btn.setToolTip(path)
                target = Path(path)
                if not target.exists():
                    btn.setEnabled(False)
                    btn.setToolTip("File or folder not found.")
                btn.clicked.connect(lambda _checked=False, p=target: self._open_path(p))
                table.setCellWidget(row_idx, 2, btn)
                table.setRowHeight(row_idx, 36)
            table.resizeColumnsToContents()
            header = table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
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
            table.setProperty("cssClass", "outputs_table")
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
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
