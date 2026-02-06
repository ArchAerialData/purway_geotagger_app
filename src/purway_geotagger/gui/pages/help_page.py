from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QBoxLayout, QLabel, QScrollArea, QFrame
)


class HelpPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        h1 = QLabel("Purway Geotagger Guide")
        h1.setProperty("cssClass", "h1")
        sub = QLabel("Use this page as a quick reference for modes, outputs, and troubleshooting.")
        sub.setProperty("cssClass", "subtitle")
        sub.setWordWrap(True)

        layout.addWidget(h1)
        layout.addWidget(sub)

        layout.addWidget(
            self._create_help_card(
                "Quick Start (2-3 minutes)",
                "Follow these steps for most runs.",
                [
                    "<b>1)</b> Open the <b>Run</b> tab and choose a mode.",
                    "<b>2)</b> Drop your <b>Raw Data folder(s)</b> or add folders/files manually.",
                    "<b>3)</b> Configure only required options (for Encroachment/Combined, set output folder).",
                    "<b>4)</b> Click Run, then use <b>View log</b> / <b>Run Report</b> if needed.",
                ],
            )
        )

        modes_title = QLabel("Choose The Right Mode")
        modes_title.setProperty("cssClass", "h2")
        layout.addWidget(modes_title)

        self._mode_cards_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self._mode_cards_layout.setSpacing(14)
        self._mode_cards_layout.addWidget(
            self._create_help_card(
                "Methane Reports",
                "Best when you need methane deliverables only.",
                [
                    "Writes EXIF in-place for matched JPGs.",
                    "Creates cleaned CSV files beside source methane CSV files.",
                    "Optional KMZ output from cleaned data.",
                ],
            )
        )
        self._mode_cards_layout.addWidget(
            self._create_help_card(
                "Encroachment Reports",
                "Best when you need one unified photo deliverable folder.",
                [
                    "Copies JPGs into a single output folder.",
                    "Optional renaming using templates and start index.",
                    "Run logs include missing/unprocessed photo reasons.",
                ],
            )
        )
        self._mode_cards_layout.addWidget(
            self._create_help_card(
                "Combined",
                "Best when you need methane + encroachment outputs in one pass.",
                [
                    "Produces methane outputs and encroachment copies together.",
                    "Encroachment renaming affects copied files only.",
                    "Useful for minimizing repeat setup steps.",
                ],
            )
        )
        layout.addLayout(self._mode_cards_layout)

        layout.addWidget(
            self._create_reference_card(
                "Feature Reference",
                [
                    (
                        "Run Tab",
                        "Primary workflow: choose mode, add inputs, set required options, then run.",
                    ),
                    (
                        "Templates Tab",
                        "Create and preview renaming templates used for encroachment copies.",
                    ),
                    (
                        "Jobs Tab",
                        "Review status, open outputs, re-run failed photos, and view run reports.",
                    ),
                    (
                        "Settings",
                        "Set ExifTool path and defaults such as join delta and cleanup behavior.",
                    ),
                ],
            )
        )

        layout.addWidget(
            self._create_reference_card(
                "Troubleshooting",
                [
                    (
                        "ExifTool missing warning",
                        "Open Settings and set the ExifTool path, then run again.",
                    ),
                    (
                        "No outputs created",
                        "Check mode requirements (especially output folder in Encroachment/Combined).",
                    ),
                    (
                        "Some photos failed",
                        "Open Run Report and review the Failures table for exact reasons.",
                    ),
                    (
                        "Unexpected files in Raw Data",
                        "The app skips macOS artifact files and continues scanning valid inputs.",
                    ),
                ],
            )
        )

        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        self._apply_responsive_layout(self.width())

    def _create_help_card(self, title: str, subtitle: str, bullets: list[str]) -> QFrame:
        card = QFrame()
        card.setProperty("cssClass", "card")
        l = QVBoxLayout(card)
        l.setSpacing(12)

        t = QLabel(title)
        t.setProperty("cssClass", "label_strong")

        s = QLabel(subtitle)
        s.setProperty("cssClass", "subtitle")
        s.setWordWrap(True)

        html_list = "".join(f"<li style='margin-bottom: 6px;'>{b}</li>" for b in bullets)
        b_lbl = QLabel(f"<ul style='margin: 0; padding-left: 16px;'>{html_list}</ul>")
        b_lbl.setWordWrap(True)
        b_lbl.setTextFormat(Qt.RichText)
        b_lbl.setProperty("cssClass", "subtitle")

        l.addWidget(t)
        l.addWidget(s)
        l.addWidget(b_lbl)
        return card

    def _create_reference_card(self, title: str, rows: list[tuple[str, str]]) -> QFrame:
        card = QFrame()
        card.setProperty("cssClass", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        heading = QLabel(title)
        heading.setProperty("cssClass", "label_strong")
        layout.addWidget(heading)

        for item_title, text in rows:
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)

            t = QLabel(item_title)
            t.setProperty("cssClass", "label_strong")

            d = QLabel(text)
            d.setWordWrap(True)
            d.setProperty("cssClass", "muted")

            row_layout.addWidget(t)
            row_layout.addWidget(d)
            layout.addWidget(row)

        return card

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout(event.size().width())

    def _apply_responsive_layout(self, width: int) -> None:
        if width < 1300:
            self._mode_cards_layout.setDirection(QBoxLayout.TopToBottom)
        else:
            self._mode_cards_layout.setDirection(QBoxLayout.LeftToRight)
