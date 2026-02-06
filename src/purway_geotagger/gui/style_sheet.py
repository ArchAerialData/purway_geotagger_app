from __future__ import annotations
from PySide6.QtGui import QColor, QPalette

def get_theme_colors(theme: str) -> dict[str, str]:
    is_dark = (theme or "light").strip().lower() == "dark"
    
    if is_dark:
        return {
            "window_bg": "#1C1C1E",
            "surface_bg": "#2C2C2E",
            "input_bg": "#3A3A3C",
            "input_border": "#48484A",
            "text_primary": "#F5F5F7",
            "text_secondary": "#AEAEB2",
            "text_inverted": "#1C1C1E",
            "primary": "#0A84FF",
            "primary_hover": "#409CFF",
            "primary_pressed": "#0071E3",
            "error": "#FF453A",
            "success": "#32D74B",
            "success_hover": "#4AE168",
            "success_pressed": "#28C840",
            "border": "#38383A",
            "dropzone_bg": "rgba(44, 44, 46, 0.6)",
            "dropzone_border": "#48484A",
            "dropzone_hover": "rgba(10, 132, 255, 0.15)",
            "nav_hover": "rgba(255, 255, 255, 0.1)",
            "nav_checked_bg": "rgba(10, 132, 255, 0.2)",
        }
    else:
        return {
            "window_bg": "#F5F5F7",
            "surface_bg": "#FFFFFF",
            "input_bg": "#FFFFFF",
            "input_border": "#D1D1D6",
            "text_primary": "#1D1D1F",
            "text_secondary": "#86868B",
            "text_inverted": "#FFFFFF",
            "primary": "#007AFF",
            "primary_hover": "#0062CC",
            "primary_pressed": "#0051A8",
            "error": "#FF3B30",
            "success": "#34C759",
            "success_hover": "#2DB84F",
            "success_pressed": "#28A745",
            "border": "#E5E5EA",
            "dropzone_bg": "rgba(255, 255, 255, 0.6)",
            "dropzone_border": "#C7C7CC",
            "dropzone_hover": "rgba(0, 122, 255, 0.05)",
            "nav_hover": "rgba(0, 0, 0, 0.05)",
            "nav_checked_bg": "rgba(0, 122, 255, 0.1)",
        }

def get_palette(theme: str) -> QPalette:
    colors = get_theme_colors(theme)
    p = QPalette()
    
    # Map dictionary colors to QPalette roles
    c_window = QColor(colors["window_bg"])
    c_window_text = QColor(colors["text_primary"])
    c_base = QColor(colors["input_bg"])
    c_alt_base = QColor(colors["surface_bg"])
    c_text = QColor(colors["text_primary"])
    c_button = QColor(colors["surface_bg"])
    c_button_text = QColor(colors["text_primary"])
    c_highlight = QColor(colors["primary"])
    c_highlighted_text = QColor(colors["text_inverted"])
    c_link = QColor(colors["primary"])
    c_link_visited = QColor(colors["primary"])
    
    p.setColor(QPalette.Window, c_window)
    p.setColor(QPalette.WindowText, c_window_text)
    p.setColor(QPalette.Base, c_base)
    p.setColor(QPalette.AlternateBase, c_alt_base)
    p.setColor(QPalette.Text, c_text)
    p.setColor(QPalette.Button, c_button)
    p.setColor(QPalette.ButtonText, c_button_text)
    p.setColor(QPalette.Highlight, c_highlight)
    p.setColor(QPalette.HighlightedText, c_highlighted_text)
    p.setColor(QPalette.Link, c_link)
    p.setColor(QPalette.LinkVisited, c_link_visited)
    
    return p

def get_stylesheet(theme: str) -> str:
    """Returns the QSS stylesheet for the given theme ('light' or 'dark')."""
    c = get_theme_colors(theme)
    
    # Typography (System Font San Francisco equivalent)
    font_family = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

    # The QSS Template
    qss = f"""
    * {{
        font-family: {font_family};
        font-size: 13px;
        color: {c['text_primary']};
        outline: none;
    }}
    
    QMainWindow, QDialog {{
        background-color: {c['window_bg']};
    }}
    
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        background: {c['window_bg']};
        border-radius: 4px;
    }}
    
    QTabBar::tab {{
        background: {c['window_bg']};
        color: {c['text_secondary']};
        padding: 8px 16px;
        border-bottom: 2px solid transparent;
        font-weight: 500;
    }}
    
    QTabBar::tab:selected {{
        color: {c['primary']};
        border-bottom: 2px solid {c['primary']};
    }}
    
    QTabBar::tab:hover {{
        color: {c['text_primary']};
    }}

    /* --- Headings --- */
    QLabel[cssClass="h1"] {{
        font-size: 24px;
        font-weight: 700;
        color: {c['text_primary']};
        margin-bottom: 8px;
    }}
    
    QLabel[cssClass="h2"] {{
        font-size: 18px;
        font-weight: 600;
        color: {c['text_primary']};
        margin-bottom: 6px;
    }}
    
    QLabel[cssClass="subtitle"] {{
        font-size: 14px;
        color: {c['text_secondary']};
    }}

    QLabel[cssClass="error"] {{
        color: {c['error']};
        font-weight: 600;
    }}
    
    /* --- Cards --- */

    QFrame[cssClass="card"] {{
        background-color: {c['surface_bg']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }}
    
    QGroupBox {{
        background-color: {c['surface_bg']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        margin-top: 1.5em; /* space for title */
        font-weight: 600;
        padding-top: 10px;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
        color: {c['text_primary']};
    }}

    /* --- Buttons --- */
    QPushButton {{
        background-color: {c['surface_bg']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 16px;
        color: {c['text_primary']};
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        background-color: {c['window_bg']}; /* Slight darkening/lightening depending on mode context logic, kept simple here */
        border-color: {c['text_secondary']}; 
    }}
    
    QPushButton:pressed {{
        background-color: {c['border']};
    }}
    
    QPushButton:disabled {{
        color: {c['text_secondary']};
        background-color: {c['window_bg']};
        border-color: {c['border']};
    }}

    /* Primary Action Button */
    QPushButton[cssClass="primary"] {{
        background-color: {c['primary']};
        color: {c['text_inverted']};
        border: 1px solid {c['primary']};
        font-weight: 600;
        font-size: 14px;
        padding: 8px 20px;
        border-radius: 8px;
    }}
    
    QPushButton[cssClass="primary"]:hover {{
        background-color: {c['primary_hover']};
        border-color: {c['primary_hover']};
    }}
    
    QPushButton[cssClass="primary"]:pressed {{
        background-color: {c['primary_pressed']};
        border-color: {c['primary_pressed']};
    }}
    
    QPushButton[cssClass="primary"]:disabled {{
        background-color: {c['border']};
        border-color: {c['border']};
        color: {c['text_secondary']};
    }}

    /* Run/Go Button (Green) */
    QPushButton[cssClass="run"] {{
        background-color: {c['success']};
        color: {c['text_inverted']};
        border: 1px solid {c['success']};
        font-weight: 600;
        font-size: 14px;
        padding: 8px 20px;
        border-radius: 8px;
    }}

    QPushButton[cssClass="run"]:hover {{
        background-color: {c['success_hover']};
        border-color: {c['success_hover']};
    }}

    QPushButton[cssClass="run"]:pressed {{
        background-color: {c['success_pressed']};
        border-color: {c['success_pressed']};
    }}

    QPushButton[cssClass="run"]:disabled {{
        background-color: {c['border']};
        border-color: {c['border']};
        color: {c['text_secondary']};
    }}

    /* Ghost/Text Button */
    QPushButton[cssClass="ghost"] {{
        background-color: transparent;
        border: none;
        color: {c['primary']};
    }}
    
    QPushButton[cssClass="ghost"]:hover {{
        color: {c['primary_hover']};
        text-decoration: underline;
    }}

    /* Navigation Button (Header) */
    QPushButton[cssClass="nav_btn"] {{
        background-color: transparent;
        border: none;
        font-weight: 700;
        font-size: 15px;
        color: {c['text_primary']};
        padding: 8px 16px;
        border-radius: 6px;
    }}
    
    QPushButton[cssClass="nav_btn"]:hover {{
        background-color: {c['nav_hover']};
    }}
    
    QPushButton[cssClass="nav_btn"]:checked {{
        background-color: {c['nav_checked_bg']};
        color: {c['primary']};
    }}

    /* Sticky Nav Buttons */
    QToolButton[cssClass="sticky_nav"] {{
        background-color: transparent;
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px 10px;
        color: {c['text_primary']};
    }}

    QToolButton[cssClass="sticky_nav"]:hover {{
        background-color: {c['nav_hover']};
        border-color: {c['text_secondary']};
    }}

    /* --- Inputs --- */
    QLineEdit, QSpinBox, QComboBox {{
        background-color: {c['input_bg']};
        border: 1px solid {c['input_border']};
        border-radius: 6px;
        padding: 6px 8px;
        color: {c['text_primary']};
        selection-background-color: {c['primary']};
        selection-color: {c['text_inverted']};
    }}
    
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {c['primary']};
    }}

    /* --- Checkboxes --- */
    QCheckBox::indicator:unchecked {{
        width: 16px;
        height: 16px;
        border-radius: 3px;
        border: 1px solid {c['input_border']};
        background-color: {c['surface_bg']};
    }}

    QCheckBox::indicator:unchecked:hover {{
        border: 1px solid {c['primary']};
    }}

    QCheckBox::indicator:unchecked:disabled {{
        border: 1px solid {c['border']};
        background-color: {c['window_bg']};
    }}
    
    /* --- Lists --- */
    QListWidget {{
        background-color: {c['input_bg']};
        border: 1px solid {c['input_border']};
        border-radius: 6px;
        padding: 6px 8px;
        color: {c['text_primary']};
        selection-background-color: {c['primary']};
        selection-color: {c['text_inverted']};
    }}
    
    QListWidget::item {{
        padding: 4px;
    }}
    
    QListWidget::item:selected {{
        background: {c['primary']};
        color: {c['text_inverted']};
        border-radius: 4px;
    }}

    /* --- Drop Zone --- */
    QFrame[cssClass="dropzone"] {{
        background-color: {c['dropzone_bg']};
        border: 2px dashed {c['dropzone_border']};
        border-radius: 12px;
    }}
    
    QFrame[cssClass="dropzone"]:hover {{
        background-color: {c['dropzone_hover']};
        border-color: {c['primary']};
    }}

    /* --- Scrollbars (Mac-like slim) --- */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['text_secondary']};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QToolTip {{
        color: {c['text_primary']};
        background-color: {c['surface_bg']};
        border: 1px solid {c['border']};
        padding: 4px;
        border-radius: 4px;
    }}

    /* --- Progress Bar --- */
    QProgressBar {{
        background-color: {c['input_bg']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        text-align: center;
        color: {c['text_primary']};
        font-weight: 700;
        font-size: 13px;
        height: 40px;
    }}

    QProgressBar::chunk {{
        background-color: {c['primary']};
        border-radius: 0px;
    }}

    QProgressBar#globalProgress {{
        height: 40px;
        border: none;
        border-top: 1px solid {c['primary']};
        margin: 0;
    }}

    QProgressBar[status="success"]::chunk {{
        background-color: {c['success']};
    }}

    QProgressBar#globalProgress[status="success"] {{
        border-top: 1px solid {c['success']};
    }}

    QProgressBar[status="error"]::chunk {{
        background-color: {c['error']};
    }}

    QProgressBar#globalProgress[status="error"] {{
        border-top: 1px solid {c['error']};
    }}
    """
    return qss
