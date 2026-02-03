from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QHBoxLayout
)

class HelpPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area to handle long content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setObjectName("helpContent")
        # Ensure the content widget matches the window background
        # We can rely on inheritance or set it explicitly if needed, but transparent is usually best for scroll container
        content.setStyleSheet("#helpContent { background: transparent; }")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # --- Intro Section ---
        intro_box = QWidget()
        intro_layout = QVBoxLayout(intro_box)
        intro_layout.setContentsMargins(0, 0, 0, 0)
        intro_layout.setSpacing(8)
        
        h1 = QLabel("Purway Geotagger Guide")
        h1.setProperty("cssClass", "h1")
        
        sub = QLabel("Automated post-processing for aerial inspection data.")
        sub.setProperty("cssClass", "subtitle")
        sub.setWordWrap(True)
        
        intro_layout.addWidget(h1)
        intro_layout.addWidget(sub)
        layout.addWidget(intro_box)
        
        # --- Core Features (Cards) ---
        features_lbl = QLabel("Workflows")
        features_lbl.setProperty("cssClass", "h2")
        layout.addWidget(features_lbl)
        
        # Methane Card
        layout.addWidget(self._create_help_card(
            "Methane Reports",
            "Processes raw inspection data to highlight gas detections.",
            [
                "Filters CSV data to find points above your PPM threshold.",
                "Injects simplified metadata (Lat, Lon, PPM) directly into JPG EXIF.",
                "Exports a KMZ file for visualizing the flight path and detections.",
                "<b>Best for:</b> Rapidly generating deliverables for OGI inspections."
            ]
        ))

        # Encroachment Card
        layout.addWidget(self._create_help_card(
            "Encroachment Reports",
            "Organizes and standardizes photo deliverables.",
            [
                "Copies photos from complex folder structures into a single output directory.",
                "Renames files sequentially using customizable patterns (e.g., <i>Project_001.jpg</i>).",
                "Timestamps can be preserved or updated.",
                "<b>Best for:</b> Right-of-Way (ROW) and visual reporting."
            ]
        ))
        
        # --- Tips Section ---
        tips_lbl = QLabel("Tips & Tricks")
        tips_lbl.setProperty("cssClass", "h2")
        tips_lbl.setStyleSheet("margin-top: 16px;")
        layout.addWidget(tips_lbl)
        
        tips_frame = QFrame()
        tips_frame.setProperty("cssClass", "card")
        tips_layout = QVBoxLayout(tips_frame)
        tips_layout.setSpacing(12)
        
        tips = [
            ("Templates", "Save your renaming patterns in the <b>Templates</b> tab to ensure consistency across projects."),
            ("Job History", "Something went wrong? Go to the <b>Jobs</b> tab to view logs, retry failed items, or export manifests."),
            ("ExifTool", "This app relies on ExifTool. If you see a warning, check the <b>Settings</b> to ensure it's installed correctly.")
        ]
        
        for title, text in tips:
            row = QWidget()
            rl = QVBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(2)
            
            t = QLabel(title)
            t.setStyleSheet("font-weight: 600; font-size: 14px; color: palette(text);")
            
            d = QLabel(text)
            d.setWordWrap(True)
            d.setTextFormat(Qt.RichText)
            d.setStyleSheet("color: palette(window-text); opacity: 0.8;")
            
            rl.addWidget(t)
            rl.addWidget(d)
            tips_layout.addWidget(row)
            
        layout.addWidget(tips_frame)
        layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
    def _create_help_card(self, title: str, subtitle: str, bullets: list[str]) -> QFrame:
        card = QFrame()
        card.setProperty("cssClass", "card")
        l = QVBoxLayout(card)
        l.setSpacing(12)
        
        t = QLabel(title)
        t.setProperty("cssClass", "h2")
        t.setStyleSheet("font-size: 16px; margin: 0;")
        
        s = QLabel(subtitle)
        s.setProperty("cssClass", "subtitle")
        s.setWordWrap(True)
        
        html_list = "".join(f"<li style='margin-bottom: 6px;'>{b}</li>" for b in bullets)
        b_lbl = QLabel(f"<ul style='margin: 0; padding-left: 16px;'>{html_list}</ul>")
        b_lbl.setWordWrap(True)
        b_lbl.setTextFormat(Qt.RichText)
        
        l.addWidget(t)
        l.addWidget(s)
        l.addWidget(b_lbl)
        return card
