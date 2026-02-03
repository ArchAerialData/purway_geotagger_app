from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy

from purway_geotagger.core.modes import RunMode
from purway_geotagger.exif.exiftool_writer import is_exiftool_available
from purway_geotagger.core.utils import resource_path
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path


class HomePage(QWidget):
    mode_selected = Signal(RunMode)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode_buttons: list[QPushButton] = []
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header Container (Horizontal split)
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(40)

        # Left: Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)
        
        title = QLabel("Select a report type")
        title.setProperty("cssClass", "h1")
        
        subtitle = QLabel("Choose the workflow that matches the reports you need to deliver.")
        subtitle.setProperty("cssClass", "subtitle")
        subtitle.setWordWrap(True)

        self._last_mode_label = QLabel("")
        self._last_mode_label.setProperty("cssClass", "subtitle")
        self._last_mode_label.setStyleSheet("color: #0A84FF; font-weight: 600;")
        self._last_mode_label.setWordWrap(True)

        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        text_layout.addWidget(self._last_mode_label)
        
        # Right: System Status Card
        status_card = QFrame()
        status_card.setProperty("cssClass", "card")
        status_card.setFixedWidth(280)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(16, 16, 16, 16)
        status_layout.setSpacing(10)
        
        st_title = QLabel("System Status")
        st_title.setProperty("cssClass", "h2")
        st_title.setStyleSheet("font-size: 14px; margin-bottom: 4px;")
        
        # ExifTool Check
        et_row = QWidget()
        et_layout = QHBoxLayout(et_row)
        et_layout.setContentsMargins(0, 0, 0, 0)
        et_layout.setSpacing(8)
        
        has_et = is_exiftool_available()
        et_icon = QLabel()
        if has_et:
            # Checkmark
            et_icon.setText("✓")
            et_icon.setStyleSheet("color: #32D74B; font-weight: bold; font-size: 16px;")
        else:
            # X mark
            et_icon.setText("✕")
            et_icon.setStyleSheet("color: #FF453A; font-weight: bold; font-size: 16px;")
            
        et_lbl = QLabel("ExifTool Ready")
        if not has_et:
            et_lbl.setText("ExifTool Missing")
            et_lbl.setStyleSheet("color: #FF453A;")
            
        et_layout.addWidget(et_icon)
        et_layout.addWidget(et_lbl)
        et_layout.addStretch()
        
        status_layout.addWidget(st_title)
        status_layout.addWidget(et_row)
        status_layout.addStretch()

        header_layout.addLayout(text_layout, 1) # Text takes available space
        header_layout.addWidget(status_card)    # Card is fixed width

        layout.addWidget(header_container)

        # Cards Section
        layout.addWidget(
            self._make_mode_card(
                "Methane Reports Only",
                [
                    "Clean methane CSVs using a PPM threshold.",
                    "Inject EXIF metadata in-place.",
                    "Optional KMZ output.",
                ],
                RunMode.METHANE,
            )
        )
        layout.addWidget(
            self._make_mode_card(
                "Encroachment Reports Only",
                [
                    "Copy JPGs to a single output folder.",
                    "Renaming and chronological indexing.",
                    "Use templates or manual client codes.",
                ],
                RunMode.ENCROACHMENT,
            )
        )
        layout.addWidget(
            self._make_mode_card(
                "Methane + Encroachments",
                [
                    "Single guided flow with confirmation.",
                    "Methane stays in-place, encroachments copy out.",
                    "Separate settings for each output type.",
                ],
                RunMode.COMBINED,
            )
        )
        layout.addStretch(1)

    def set_last_mode(self, mode: RunMode | None) -> None:
        if mode is None:
            self._last_mode_label.setText("")
            return
        self._last_mode_label.setText(f"Last used: {_mode_label(mode)}")

    def _make_mode_card(self, title: str, bullets: list[str], mode: RunMode) -> QWidget:
        card = QFrame()
        card.setProperty("cssClass", "card")
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)
        # Card should not expand infinitely vertically, but be tall enough
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Title button area
        btn = QPushButton(title)
        btn.setProperty("cssClass", "primary")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.mode_selected.emit(mode))
        self._mode_buttons.append(btn)

        # Description list
        desc = QLabel(_bullets_html(bullets))
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.RichText)
        desc.setStyleSheet("color: palette(text);") # Ensure follows theme text

        card_layout.addWidget(btn)
        card_layout.addWidget(desc)
        return card


def _bullets_html(items: list[str]) -> str:
    if not items:
        return ""
    rows = "".join(f"<li style='margin-bottom: 4px;'>{item}</li>" for item in items)
    return f"<ul style='margin: 0; padding-left: 18px;'>{rows}</ul>"


def _mode_label(mode: RunMode) -> str:
    return {
        RunMode.METHANE: "Methane Reports Only",
        RunMode.ENCROACHMENT: "Encroachment Reports Only",
        RunMode.COMBINED: "Methane + Encroachments",
    }.get(mode, mode.value)
