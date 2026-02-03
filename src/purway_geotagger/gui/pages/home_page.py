from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy

from purway_geotagger.core.modes import RunMode


class HomePage(QWidget):
    mode_selected = Signal(RunMode)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode_buttons: list[QPushButton] = []
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("Select a report type")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 4)
        title.setFont(title_font)

        subtitle = QLabel("Choose the workflow that matches the reports you need to deliver.")
        subtitle.setWordWrap(True)

        self._last_mode_label = QLabel("")
        self._last_mode_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._last_mode_label)
        layout.addSpacing(12)

        layout.addWidget(
            self._make_mode_card(
                "Methane Reports Only",
                [
                    "Clean methane CSVs using a PPM threshold (default 1000).",
                    "Inject EXIF metadata in-place (no output folder required).",
                    "Optional KMZ output from the cleaned CSV (when enabled).",
                ],
                RunMode.METHANE,
            )
        , 1)
        layout.addWidget(
            self._make_mode_card(
                "Encroachment Reports Only",
                [
                    "Copy JPGs to a single output folder.",
                    "Optional renaming and indexing ordered by capture time.",
                    "Use templates or manual Client Abbreviation + Start Index (or disable renaming).",
                ],
                RunMode.ENCROACHMENT,
            )
        , 1)
        layout.addWidget(
            self._make_mode_card(
                "Methane + Encroachments",
                [
                    "Single guided flow with a confirmation step.",
                    "Methane stays in-place while encroachments copy to output.",
                    "Separate settings for methane and encroachment outputs.",
                ],
                RunMode.COMBINED,
            )
        , 1)
        self._apply_styles()

    def set_last_mode(self, mode: RunMode | None) -> None:
        if mode is None:
            self._last_mode_label.setText("")
            return
        self._last_mode_label.setText(f"Last used: {_mode_label(mode)}")

    def _make_mode_card(self, title: str, bullets: list[str], mode: RunMode) -> QWidget:
        card = QFrame()
        card.setProperty("modeCardFrame", True)
        card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        btn = QPushButton(title)
        btn.setMinimumHeight(44)
        btn.setProperty("modeCardButton", True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.mode_selected.emit(mode))
        self._mode_buttons.append(btn)

        desc = QLabel(_bullets_html(bullets))
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.RichText)

        card_layout.addWidget(btn)
        card_layout.addWidget(desc)
        return card

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.PaletteChange:
            self._apply_styles()
        super().changeEvent(event)

    def _apply_styles(self) -> None:
        palette = self.palette()
        accent = palette.color(QPalette.Highlight)
        accent_text = palette.color(QPalette.HighlightedText)
        border = palette.color(QPalette.Mid)
        panel = palette.color(QPalette.Base)
        hover = _tint(accent, 1.1)
        pressed = _tint(accent, 0.9)

        btn_style = (
            "QPushButton[modeCardButton=\"true\"] {"
            f"background-color: {accent.name()};"
            f"color: {accent_text.name()};"
            f"border: 1px solid {border.name()};"
            "border-radius: 8px;"
            "padding: 8px 14px;"
            "font-weight: 600;"
            "}"
            "QPushButton[modeCardButton=\"true\"]:hover {"
            f"background-color: {hover.name()};"
            "}"
            "QPushButton[modeCardButton=\"true\"]:pressed {"
            f"background-color: {pressed.name()};"
            "}"
        )
        frame_style = (
            "QFrame[modeCardFrame=\"true\"] {"
            f"background-color: {panel.name()};"
            f"border: 1px solid {border.name()};"
            "border-radius: 10px;"
            "}"
        )
        self.setStyleSheet(f"{btn_style} {frame_style}")


def _tint(color: QColor, factor: float) -> QColor:
    if factor >= 1:
        return color.lighter(int(factor * 100))
    return color.darker(int((1 / factor) * 100))


def _bullets_html(items: list[str]) -> str:
    if not items:
        return ""
    rows = "".join(f"<li>{item}</li>" for item in items)
    return f"<ul style=\"margin: 0; padding-left: 18px;\">{rows}</ul>"


def _mode_label(mode: RunMode) -> str:
    return {
        RunMode.METHANE: "Methane Reports Only",
        RunMode.ENCROACHMENT: "Encroachment Reports Only",
        RunMode.COMBINED: "Methane + Encroachments",
    }.get(mode, mode.value)
