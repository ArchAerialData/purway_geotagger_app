"""Compact, persistent weather evidence display with expandable source links."""
from __future__ import annotations

from collections import Counter
from html import escape
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTextBrowser, QToolButton, QVBoxLayout, QWidget


class WindSourceDetails(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.PlainText)
        layout.addWidget(self.summary)
        self.toggle = QToolButton()
        self.toggle.setText("Weather sources and measurement times")
        self.toggle.setCheckable(True)
        layout.addWidget(self.toggle)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        self.details.setMinimumHeight(190)
        self.details.setMaximumHeight(300)
        self.details.hide()
        self.toggle.toggled.connect(self.details.setVisible)
        layout.addWidget(self.details)

    def show_details(self) -> None:
        self.toggle.setChecked(True)

    def set_evidence(self, evidence: dict[str, Any]) -> None:
        summaries = []
        parts = ["<p>Station readings represent nearby conditions. Estimated values are from a model. "
                 "Unverified or changed entries need manual review. Missing gusts are not assumed to be zero.</p>"]
        for label, fields in evidence["rows"].items():
            counts = Counter(entry["status"].replace("_", " ") for entry in fields.values())
            summaries.append(f"{label.title()}: " + ", ".join(f"{count} {status}" for status, count in counts.items()))
            parts.append(f"<h4>{label.title()}</h4>")
            for name, entry in fields.items():
                parts.append(f"<p><b>{escape(name.replace('_', ' '))}: {escape(str(entry['value']))}</b> "
                             f"({escape(entry['status'].replace('_', ' '))})")
                source = entry.get("source")
                if source:
                    requested = entry["requested"]
                    parts.append("<br>Requested: " + escape(f"{requested['date']} {requested['time']} {requested['timezone']}"))
                    parts.append("<br>Source: " + escape(f"{source['provider']} / {source['station_id'] or source['model']}"))
                    parts.append("<br>Measurement: " + escape(source['observed_at_local']))
                    parts.append(f"; difference {source['time_delta_minutes']:+.0f} min")
                    if source.get("distance_miles") is not None:
                        parts.append(f"; station {source['distance_miles']:.1f} miles away")
                    url = source.get("source_url")
                    if url and url.startswith("https://"):
                        parts.append(f'<br><a href="{escape(url, quote=True)}">Open this field’s source</a>')
                parts.append("</p>")
        missing = evidence.get("last_lookup_missing_fields", {})
        if any(missing.values()):
            summaries.append("Last lookup left fields unresolved; existing entries were retained.")
        for warning in evidence.get("last_lookup_warnings", []):
            parts.append(f"<p>{escape(warning)}</p>")
        self.summary.setText("\n".join(summaries))
        self.details.setHtml("".join(parts))
