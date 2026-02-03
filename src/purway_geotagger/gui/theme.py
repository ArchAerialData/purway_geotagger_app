from __future__ import annotations

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QStyleFactory


def apply_theme(app: QApplication, theme: str) -> None:
    mode = (theme or "light").strip().lower()
    if mode not in ("light", "dark"):
        mode = "light"

    app.setStyle(QStyleFactory.create("Fusion"))
    palette = _build_palette(mode)
    app.setPalette(palette)

    if mode == "dark":
        app.setStyleSheet(
            "QToolTip { color: #f2f2f2; background-color: #2b2b2b; border: 1px solid #3a3a3a; }"
            "QToolButton[themeToggle=\"true\"] {"
            "  border: 1px solid #3a3a3a; border-radius: 6px; padding: 4px 10px;"
            "  background: #2b2b2b; color: #e5e5e5;"
            "}"
            "QToolButton[themeToggle=\"true\"]:checked {"
            "  background: #4c84ff; color: #ffffff; border-color: #4c84ff;"
            "}"
        )
    else:
        app.setStyleSheet(
            "QToolTip { color: #111111; background-color: #ffffe1; border: 1px solid #c7c7c7; }"
            "QToolButton[themeToggle=\"true\"] {"
            "  border: 1px solid #c7c7c7; border-radius: 6px; padding: 4px 10px;"
            "  background: #f2f2f2; color: #111111;"
            "}"
            "QToolButton[themeToggle=\"true\"]:checked {"
            "  background: #2f6fed; color: #ffffff; border-color: #2f6fed;"
            "}"
        )


def _build_palette(mode: str) -> QPalette:
    if mode == "dark":
        window = QColor(18, 18, 18)
        base = QColor(30, 30, 30)
        alt = QColor(45, 45, 45)
        text = QColor(235, 235, 235)
        button = QColor(45, 45, 45)
        highlight = QColor(76, 132, 255)
        link = QColor(120, 170, 255)
    else:
        window = QColor(250, 250, 250)
        base = QColor(255, 255, 255)
        alt = QColor(245, 245, 245)
        text = QColor(20, 20, 20)
        button = QColor(240, 240, 240)
        highlight = QColor(47, 111, 237)
        link = QColor(22, 102, 204)

    highlight_text = _contrast_text(highlight)
    disabled_text = QColor(120, 120, 120) if mode == "light" else QColor(140, 140, 140)

    palette = QPalette()
    palette.setColor(QPalette.Window, window)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.AlternateBase, alt)
    palette.setColor(QPalette.ToolTipBase, window)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, button)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.Highlight, highlight)
    palette.setColor(QPalette.HighlightedText, highlight_text)
    palette.setColor(QPalette.Link, link)
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))

    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, disabled_text)
    return palette


def _contrast_text(color: QColor) -> QColor:
    # Relative luminance to ensure readable highlight text.
    r = color.red() / 255.0
    g = color.green() / 255.0
    b = color.blue() / 255.0
    luminance = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
    return QColor(0, 0, 0) if luminance > 0.6 else QColor(255, 255, 255)
