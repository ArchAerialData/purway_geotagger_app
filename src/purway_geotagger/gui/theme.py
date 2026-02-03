from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from purway_geotagger.gui.style_sheet import get_stylesheet, get_palette


def apply_theme(app: QApplication, theme: str) -> None:
    mode = (theme or "light").strip().lower()
    if mode not in ("light", "dark"):
        mode = "light"

    # We rely on the QSS for almost everything now.
    # However, sometimes we still need to set the general palette 
    # for certain unstyled controls or macOS defaults.
    
    # Force a general palette update to guide OS-level things
    # but the heavy lifting is in setStyleSheet
    app.setPalette(get_palette(mode))
    
    # Load and inject QSS
    qss = get_stylesheet(mode)
    app.setStyleSheet(qss)
    
    # We don't rely on Fusion palette injection as much anymore
    # but setting property can help custom widgets know the mode
    app.setProperty("darkMode", mode == "dark")

