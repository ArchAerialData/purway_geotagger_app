from __future__ import annotations
from typing import TYPE_CHECKING

from purway_geotagger.core.utils import resource_path

if TYPE_CHECKING:
    from PySide6.QtGui import QPalette

def get_theme_colors(theme: str) -> dict[str, str]:
    is_dark = (theme or "light").strip().lower() == "dark"
    
    if is_dark:
        return {
            # GUI_CHANGESET_A11Y_001: contrast-tuned dark palette.
            "window_bg": "#18181B",
            "surface_bg": "#232327",
            "table_row_bg": "#232327",
            "table_alt_bg": "#26262B",
            "table_header_bg": "#2B2B30",
            "input_bg": "#2B2B30",
            "input_border": "#4C4C52",
            "text_primary": "#F5F5F7",
            "text_secondary": "#AEAEB2",
            "text_muted": "#8F8F94",
            "text_inverted": "#1C1C1E",
            "primary": "#0A84FF",
            "primary_hover": "#2A98FF",
            "primary_pressed": "#138EFF",
            "error": "#FF453A",
            "success": "#32D74B",
            "success_hover": "#4AE168",
            "success_pressed": "#3DDB57",
            "border": "#3A3A40",
            "card_border": "#4A4A4E",
            "dropzone_bg": "rgba(35, 35, 39, 0.72)",
            "dropzone_border": "#5A5A60",
            "dropzone_hover": "rgba(10, 132, 255, 0.20)",
            "nav_hover": "rgba(255, 255, 255, 0.08)",
            "nav_checked_bg": "rgba(10, 132, 255, 0.24)",
            "status_info": "#6AB6FF",
            "status_success_text": "#48D960",
            "status_error_text": "#FF7C73",
            "badge_running_bg": "rgba(10, 132, 255, 0.18)",
            "badge_running_text": "#6AB6FF",
            "badge_done_bg": "rgba(72, 217, 96, 0.20)",
            "badge_done_text": "#48D960",
            "badge_failed_bg": "rgba(255, 124, 115, 0.18)",
            "badge_failed_text": "#FF9A93",
            "badge_cancelled_bg": "rgba(143, 143, 148, 0.20)",
            "badge_cancelled_text": "#B6B6BC",
            "badge_queued_bg": "rgba(143, 143, 148, 0.20)",
            "badge_queued_text": "#C3C3CA",
            "button_secondary_bg": "#232327",
            "button_secondary_hover": "#2B2B30",
            "button_secondary_pressed": "#303036",
            "button_secondary_border": "#4A4A50",
            "stepper_bg": "#343842",
            "stepper_border": "#636A78",
            "stepper_divider": "#6D7482",
            "stepper_hover_bg": "#3D4450",
            "stepper_pressed_bg": "#2F3641",
            "button_primary_fg": "#1C1C1E",
            "button_run_fg": "#1C1C1E",
            "disabled_bg": "#2A2A2F",
            "disabled_text": "#7D7D84",
            "focus_ring": "#5AAEFF",
        }
    else:
        return {
            # GUI_CHANGESET_A11Y_001: contrast-tuned light palette.
            "window_bg": "#F3F4F6",
            "surface_bg": "#FFFFFF",
            "table_row_bg": "#FFFFFF",
            "table_alt_bg": "#F7F8FA",
            "table_header_bg": "#F7F8FA",
            "input_bg": "#FFFFFF",
            "input_border": "#BEBEC5",
            "text_primary": "#1D1D1F",
            "text_secondary": "#636366",
            "text_muted": "#6F6F75",
            "text_inverted": "#FFFFFF",
            "primary": "#0062CC",
            "primary_hover": "#005BB5",
            "primary_pressed": "#004A94",
            "error": "#E0382D",
            "success": "#34C759",
            "success_hover": "#2DB84F",
            "success_pressed": "#28A745",
            "border": "#D7D9DF",
            "card_border": "#C9C9CF",
            "dropzone_bg": "rgba(255, 255, 255, 0.75)",
            "dropzone_border": "#B5B5BD",
            "dropzone_hover": "rgba(0, 98, 204, 0.08)",
            "nav_hover": "rgba(0, 0, 0, 0.04)",
            "nav_checked_bg": "rgba(0, 98, 204, 0.12)",
            "status_info": "#005BB5",
            "status_success_text": "#1D7A36",
            "status_error_text": "#C6281E",
            "badge_running_bg": "rgba(0, 91, 181, 0.12)",
            "badge_running_text": "#005BB5",
            "badge_done_bg": "rgba(29, 122, 54, 0.12)",
            "badge_done_text": "#1D7A36",
            "badge_failed_bg": "rgba(198, 40, 30, 0.12)",
            "badge_failed_text": "#C6281E",
            "badge_cancelled_bg": "rgba(111, 111, 117, 0.14)",
            "badge_cancelled_text": "#5F6368",
            "badge_queued_bg": "rgba(111, 111, 117, 0.14)",
            "badge_queued_text": "#5F6368",
            "button_secondary_bg": "#FFFFFF",
            "button_secondary_hover": "#F3F4F6",
            "button_secondary_pressed": "#E9EBF0",
            "button_secondary_border": "#BEBEC5",
            "stepper_bg": "#EEF1F5",
            "stepper_border": "#AEB4BF",
            "stepper_divider": "#BCC2CC",
            "stepper_hover_bg": "#E3E8F0",
            "stepper_pressed_bg": "#D8DFEA",
            "button_primary_fg": "#FFFFFF",
            "button_run_fg": "#1D1D1F",
            "disabled_bg": "#F0F1F4",
            "disabled_text": "#787A82",
            "focus_ring": "#338DFF",
        }

def get_palette(theme: str) -> QPalette:
    from PySide6.QtGui import QColor, QPalette

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
    checkmark_white_icon = str(resource_path("assets/icons/checkmark_white.png")).replace("\\", "/")
    checkmark_blue_icon = str(resource_path("assets/icons/checkmark_blue.png")).replace("\\", "/")
    
    # Typography (System Font San Francisco equivalent)
    font_family = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

    # The QSS Template
    qss = f"""
    * {{
        font-family: {font_family};
        font-size: 13px;
        color: {c['text_primary']};
    }}
    
    QMainWindow, QDialog {{
        background-color: {c['window_bg']};
    }}

    QWidget#mainHeader {{
        background-color: {c['window_bg']};
        border-bottom: 1px solid {c['card_border']};
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

    /* GUI_CHANGESET_A11Y_001: semantic status/help label variants. */
    QLabel[cssClass="muted"] {{
        color: {c['text_muted']};
    }}

    QLabel[cssClass="label_strong"] {{
        font-size: 14px;
        font-weight: 600;
        color: {c['text_primary']};
    }}

    QLabel[cssClass="breadcrumb"] {{
        font-size: 12px;
        font-weight: 600;
        color: {c['text_muted']};
    }}

    QLabel[cssClass="wind_row_badge"] {{
        background-color: {c['nav_checked_bg']};
        border: 1px solid {c['card_border']};
        border-radius: 12px;
        color: {c['text_primary']};
        font-size: 12px;
        font-weight: 700;
        padding: 3px 10px;
    }}

    QLabel[cssClass="wind_preview_title"] {{
        color: {c['text_secondary']};
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }}

    QLabel[cssClass="wind_preview_heading"] {{
        color: {c['text_secondary']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }}

    QFrame[cssClass="wind_preview_row"] {{
        background-color: {c['table_alt_bg']};
        border: 1px solid {c['card_border']};
        border-radius: 10px;
    }}

    QLabel[cssClass="wind_preview_time"] {{
        color: {c['text_primary']};
        font-size: 14px;
        font-weight: 700;
    }}

    QLabel[cssClass="wind_preview_string"] {{
        color: {c['text_primary']};
        font-size: 14px;
        font-weight: 600;
    }}

    QLabel[cssClass="error"] {{
        color: {c['status_error_text']};
        font-weight: 600;
    }}

    QLabel[cssClass="status_info"] {{
        color: {c['status_info']};
        font-weight: 600;
    }}

    QLabel[cssClass="status_success"] {{
        color: {c['status_success_text']};
        font-weight: 600;
    }}

    QLabel[cssClass="status_error"] {{
        color: {c['status_error_text']};
        font-weight: 600;
    }}

    QLabel[cssClass="status_badge"] {{
        border: 1px solid transparent;
        border-radius: 11px;
        padding: 2px 10px;
        font-size: 12px;
        font-weight: 700;
        min-height: 18px;
    }}

    QLabel[cssClass="status_badge"][status="idle"] {{
        background-color: transparent;
        color: {c['text_muted']};
        border-color: {c['border']};
    }}

    QLabel[cssClass="status_badge"][status="running"] {{
        background-color: {c['badge_running_bg']};
        color: {c['badge_running_text']};
        border-color: {c['badge_running_text']};
    }}

    QLabel[cssClass="status_badge"][status="done"] {{
        background-color: {c['badge_done_bg']};
        color: {c['badge_done_text']};
        border-color: {c['badge_done_text']};
    }}

    QLabel[cssClass="status_badge"][status="failed"] {{
        background-color: {c['badge_failed_bg']};
        color: {c['badge_failed_text']};
        border-color: {c['badge_failed_text']};
    }}

    QLabel[cssClass="status_badge"][status="cancelled"] {{
        background-color: {c['badge_cancelled_bg']};
        color: {c['badge_cancelled_text']};
        border-color: {c['badge_cancelled_text']};
    }}

    QLabel[cssClass="status_badge"][status="queued"] {{
        background-color: {c['badge_queued_bg']};
        color: {c['badge_queued_text']};
        border-color: {c['badge_queued_text']};
    }}
    
    /* --- Cards --- */

    QFrame[cssClass="card"] {{
        background-color: {c['surface_bg']};
        border: 1px solid {c['card_border']};
        border-radius: 12px;
    }}

    QFrame[cssClass="mode_card"] {{
        background-color: {c['surface_bg']};
        border: 1px solid {c['card_border']};
        border-radius: 14px;
    }}

    QFrame[cssClass="mode_card"][hovered="true"] {{
        border: 1px solid {c['focus_ring']};
        background-color: {c['table_alt_bg']};
    }}

    QFrame[cssClass="mode_card"][lastUsed="true"] {{
        border: 1px solid {c['primary']};
    }}

    QFrame[cssClass="mode_card"]:focus {{
        border: 1px solid {c['focus_ring']};
    }}

    QLabel[cssClass="mode_card_icon"] {{
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        border-radius: 8px;
        background-color: {c['nav_checked_bg']};
        color: {c['primary']};
        font-size: 12px;
        font-weight: 700;
    }}

    QLabel[cssClass="mode_card_title"] {{
        font-size: 15px;
        font-weight: 650;
        color: {c['text_primary']};
    }}

    QLabel[cssClass="mode_card_chevron"] {{
        color: {c['text_muted']};
        font-size: 17px;
        font-weight: 700;
        min-width: 12px;
    }}

    QFrame[cssClass="mode_card"][hovered="true"] QLabel[cssClass="mode_card_chevron"] {{
        color: {c['primary']};
    }}

    QFrame[cssClass="mode_card_divider"] {{
        border: none;
        min-height: 1px;
        max-height: 1px;
        background-color: {c['card_border']};
    }}

    QLabel[cssClass="mode_card_bullets"] {{
        color: {c['text_secondary']};
        font-size: 13px;
    }}

    QLabel[cssClass="mode_card_hint"] {{
        color: {c['text_muted']};
        font-size: 12px;
        font-weight: 600;
    }}
    
    QGroupBox {{
        background-color: {c['surface_bg']};
        border: 1px solid {c['card_border']};
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

    /* GUI_CHANGESET_A11Y_001: accessible button contrast and states. */
    /* --- Buttons --- */
    QPushButton {{
        background-color: {c['button_secondary_bg']};
        border: 1px solid {c['button_secondary_border']};
        border-radius: 6px;
        padding: 6px 16px;
        color: {c['text_primary']};
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        background-color: {c['button_secondary_hover']};
        border-color: {c['card_border']};
    }}
    
    QPushButton:pressed {{
        background-color: {c['button_secondary_pressed']};
        border-color: {c['button_secondary_border']};
    }}

    QPushButton:focus {{
        border-color: {c['focus_ring']};
    }}
    
    QPushButton:disabled {{
        color: {c['disabled_text']};
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
    }}

    QToolButton[themeToggle="true"] {{
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 4px;
    }}

    QToolButton[themeToggle="true"]:hover {{
        background-color: {c['nav_hover']};
    }}

    QToolButton[themeToggle="true"]:checked {{
        background-color: {c['nav_checked_bg']};
        border-color: {c['primary']};
    }}

    /* Primary Action Button */
    QPushButton[cssClass="primary"] {{
        background-color: {c['primary']};
        color: {c['button_primary_fg']};
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
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
        color: {c['disabled_text']};
    }}

    /* Run/Go Button (Green) */
    QPushButton[cssClass="run"] {{
        background-color: {c['success']};
        color: {c['button_run_fg']};
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
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
        color: {c['disabled_text']};
    }}

    /* Open File Button */
    QPushButton[cssClass="open_file"] {{
        background-color: {c['primary']};
        color: {c['button_primary_fg']};
        border: 1px solid {c['primary']};
        font-weight: 600;
        font-size: 13px;
        padding: 0px 16px;
        border-radius: 16px;
        text-align: center;
    }}

    QPushButton[cssClass="open_file"]:hover {{
        background-color: {c['primary_hover']};
        border-color: {c['primary_hover']};
    }}

    QPushButton[cssClass="open_file"]:pressed {{
        background-color: {c['primary_pressed']};
        border-color: {c['primary_pressed']};
    }}

    QPushButton[cssClass="open_file"]:disabled {{
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
        color: {c['disabled_text']};
    }}

    QToolButton[cssClass="open_file"] {{
        background-color: {c['primary']};
        color: {c['button_primary_fg']};
        border: 1px solid {c['primary']};
        font-weight: 600;
        font-size: 13px;
        padding: 0px 16px;
        border-radius: 16px;
        text-align: center;
    }}

    QToolButton[cssClass="open_file"]:hover {{
        background-color: {c['primary_hover']};
        border-color: {c['primary_hover']};
    }}

    QToolButton[cssClass="open_file"]:pressed {{
        background-color: {c['primary_pressed']};
        border-color: {c['primary_pressed']};
    }}

    QToolButton[cssClass="open_file"]:disabled {{
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
        color: {c['disabled_text']};
    }}

    QWidget[cssClass="open_file_pill"] {{
        background-color: {c['primary']};
        border: 1px solid {c['primary']};
        border-radius: 16px;
    }}

    QWidget[cssClass="open_file_pill"]:hover {{
        background-color: {c['primary_hover']};
        border-color: {c['primary_hover']};
    }}

    QWidget[cssClass="open_file_pill"]:disabled {{
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
    }}

    QLabel[cssClass="open_file_pill_label"] {{
        color: {c['button_primary_fg']};
        font-weight: 600;
        font-size: 13px;
    }}

    QLabel[cssClass="open_file_pill_label"]:disabled {{
        color: {c['disabled_text']};
    }}

    /* GUI_CHANGESET_A11Y_002: unified table readability across pages/dialogs. */
    QTableView, QTableWidget {{
        border: 1px solid {c['card_border']};
        border-radius: 12px;
        background-color: {c['table_row_bg']};
        alternate-background-color: {c['table_alt_bg']};
        gridline-color: {c['border']};
        selection-background-color: {c['primary']};
        selection-color: {c['text_inverted']};
    }}

    QTableView::item, QTableWidget::item {{
        padding: 6px 8px;
    }}

    QHeaderView::section {{
        background-color: {c['table_header_bg']};
        color: {c['text_secondary']};
        border: none;
        border-bottom: 1px solid {c['card_border']};
        padding: 6px 8px;
        font-weight: 600;
    }}

    QTableCornerButton::section {{
        background-color: {c['table_header_bg']};
        border: none;
        border-bottom: 1px solid {c['card_border']};
    }}

    QTableWidget[cssClass="outputs_table"] {{
        padding: 2px;
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

    QToolButton[cssClass="chip"] {{
        background-color: {c['button_secondary_bg']};
        border: 1px solid {c['card_border']};
        border-radius: 14px;
        padding: 5px 12px;
        color: {c['text_primary']};
        font-size: 12px;
        font-weight: 600;
    }}

    QToolButton[cssClass="chip"]:hover {{
        background-color: {c['button_secondary_hover']};
        border-color: {c['focus_ring']};
    }}

    QToolButton[cssClass="chip"]:pressed {{
        background-color: {c['button_secondary_pressed']};
        border-color: {c['focus_ring']};
    }}

    QToolButton[cssClass="chip"]:checked {{
        background-color: {c['nav_checked_bg']};
        color: {c['primary']};
        border-color: {c['primary']};
    }}

    QToolButton[cssClass="chip"]:disabled {{
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
        color: {c['disabled_text']};
    }}

    /* Sticky Nav Buttons */
    QToolButton[cssClass="sticky_nav"] {{
        background-color: {c['button_secondary_bg']};
        border: 1px solid {c['card_border']};
        border-radius: 16px;
        padding: 6px 12px;
        min-height: 32px;
        font-size: 13px;
        font-weight: 600;
        color: {c['text_primary']};
    }}

    QToolButton[cssClass="sticky_nav"]:hover {{
        background-color: {c['button_secondary_hover']};
        border-color: {c['focus_ring']};
    }}

    QToolButton[cssClass="sticky_nav"]:pressed {{
        background-color: {c['button_secondary_pressed']};
        border-color: {c['focus_ring']};
    }}

    QToolButton[cssClass="sticky_nav"]:focus {{
        border-color: {c['focus_ring']};
    }}

    QToolButton[cssClass="sticky_nav"]:disabled {{
        background-color: {c['disabled_bg']};
        border-color: {c['border']};
        color: {c['disabled_text']};
    }}

    /* --- Inputs --- */
    QLineEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
        background-color: {c['input_bg']};
        border: 1px solid {c['input_border']};
        border-radius: 6px;
        padding: 6px 8px;
        color: {c['text_primary']};
        selection-background-color: {c['primary']};
        selection-color: {c['text_inverted']};
    }}
    
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
        border: 1px solid {c['focus_ring']};
    }}

    QLineEdit:read-only {{
        background-color: {c['table_header_bg']};
        color: {c['text_secondary']};
    }}

    QComboBox::drop-down {{
        border: none;
    }}

    QDateEdit::drop-down, QDateTimeEdit::drop-down {{
        border: none;
    }}

    QLineEdit[cssClass="date_picker_display"] {{
        font-weight: 600;
    }}

    QToolButton[cssClass="date_picker_btn"] {{
        background-color: {c['button_secondary_bg']};
        border: 1px solid {c['button_secondary_border']};
        border-radius: 8px;
        color: {c['text_primary']};
        padding: 5px 10px;
        min-height: 30px;
        font-size: 12px;
        font-weight: 600;
    }}

    QToolButton[cssClass="date_picker_btn"]:hover {{
        background-color: {c['button_secondary_hover']};
        border-color: {c['focus_ring']};
    }}

    QToolButton[cssClass="date_picker_btn"]:pressed {{
        background-color: {c['button_secondary_pressed']};
        border-color: {c['focus_ring']};
    }}

    QMenu[cssClass="calendar_menu"] {{
        background-color: {c['surface_bg']};
        border: 1px solid {c['card_border']};
        border-radius: 12px;
        padding: 8px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget {{
        background-color: {c['surface_bg']};
        color: {c['text_primary']};
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background-color: {c['table_header_bg']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        min-height: 32px;
        padding: 2px 6px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton {{
        background-color: transparent;
        border: none;
        color: {c['text_primary']};
        font-weight: 600;
        padding: 4px 8px;
        min-height: 24px;
        border-radius: 7px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton:hover {{
        background-color: {c['nav_hover']};
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton:pressed {{
        background-color: {c['dropzone_hover']};
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton#qt_calendar_prevmonth,
    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton#qt_calendar_nextmonth {{
        min-width: 22px;
        max-width: 22px;
        padding: 0px;
        font-size: 13px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton#qt_calendar_monthbutton {{
        min-width: 112px;
        text-align: left;
        padding: 2px 18px 2px 8px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton#qt_calendar_monthbutton::menu-indicator {{
        subcontrol-origin: padding;
        subcontrol-position: right center;
        right: 6px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QToolButton#qt_calendar_yearbutton {{
        min-width: 56px;
        text-align: left;
        padding: 2px 8px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QAbstractItemView:enabled {{
        color: {c['text_primary']};
        selection-background-color: {c['primary']};
        selection-color: {c['text_inverted']};
        background-color: {c['surface_bg']};
        outline: 0;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QAbstractItemView::item:hover {{
        background-color: {c['nav_hover']};
        border-radius: 6px;
    }}

    QMenu[cssClass="calendar_menu"] QCalendarWidget QAbstractItemView:disabled {{
        color: {c['disabled_text']};
    }}

    QWidget[cssClass="wind_stepper"] {{
        border: 1px solid {c['stepper_border']};
        border-radius: 8px;
        background-color: {c['stepper_bg']};
    }}

    QToolButton[cssClass="wind_stepper_btn"] {{
        border: none;
        padding: 0px;
        margin: 0px;
        min-width: 16px;
        min-height: 14px;
        max-width: 16px;
        max-height: 14px;
        font-size: 10px;
        font-weight: 700;
        color: {c['primary']};
        background-color: {c['stepper_bg']};
    }}

    QToolButton[cssClass="wind_stepper_btn"][stepPos="up"] {{
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
        border-bottom: 1px solid {c['stepper_divider']};
    }}

    QToolButton[cssClass="wind_stepper_btn"][stepPos="down"] {{
        border-bottom-left-radius: 7px;
        border-bottom-right-radius: 7px;
    }}

    QToolButton[cssClass="wind_stepper_btn"]:hover {{
        background-color: {c['stepper_hover_bg']};
    }}

    QToolButton[cssClass="wind_stepper_btn"]:pressed {{
        background-color: {c['stepper_pressed_bg']};
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

    QCheckBox::indicator:checked {{
        width: 16px;
        height: 16px;
        border-radius: 3px;
        border: 1px solid {c['primary']};
        background-color: {c['primary']};
        image: url("{checkmark_white_icon}");
        border-image: url("{checkmark_white_icon}");
    }}

    QCheckBox::indicator:checked:disabled {{
        border: 1px solid {c['border']};
        background-color: {c['disabled_bg']};
    }}

    /* Settings dialog checkbox variant: less saturated, clearer state separation. */
    QCheckBox[cssClass="settings_checkbox"]::indicator:unchecked {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {c['input_border']};
        background-color: {c['surface_bg']};
    }}

    QCheckBox[cssClass="settings_checkbox"]::indicator:unchecked:hover {{
        border: 1px solid {c['focus_ring']};
        background-color: {c['table_alt_bg']};
    }}

    QCheckBox[cssClass="settings_checkbox"]::indicator:checked {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {c['primary']};
        background-color: {c['surface_bg']};
        image: url("{checkmark_blue_icon}");
        border-image: url("{checkmark_blue_icon}");
    }}

    QCheckBox[cssClass="settings_checkbox"]::indicator:checked:hover {{
        border: 1px solid {c['focus_ring']};
        background-color: {c['dropzone_hover']};
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

    QListWidget:focus {{
        border: 1px solid {c['focus_ring']};
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
