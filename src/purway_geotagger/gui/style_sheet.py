from __future__ import annotations

def get_stylesheet(theme: str) -> str:
    """Returns the QSS stylesheet for the given theme ('light' or 'dark')."""
    
    is_dark = theme == "dark"

    # Color Palette
    if is_dark:
        # Backgrounds
        c_window_bg = "#1C1C1E"       # Deep charcoal
        c_surface_bg = "#2C2C2E"      # Slightly lighter gray for cards/panels
        c_input_bg = "#3A3A3C"        # Input fields
        c_input_border = "#48484A"    # Input borders
        
        # Text
        c_text_primary = "#F5F5F7"    # Off-white
        c_text_secondary = "#AEAEB2"  # Lighter gray
        c_text_inverted = "#1C1C1E"   # For text on primary buttons
        
        # Primary / Accents
        c_primary = "#0A84FF"         # Bright Blue
        c_primary_hover = "#409CFF"
        c_primary_pressed = "#0071E3"
        
        # Status
        c_error = "#FF453A"
        c_success = "#32D74B"
        
        # Borders
        c_border = "#38383A"
        
        # Special
        c_dropzone_bg = "rgba(44, 44, 46, 0.6)"
        c_dropzone_border = "#48484A"
        c_dropzone_hover = "rgba(10, 132, 255, 0.15)"
        
    else:
        # Backgrounds
        c_window_bg = "#F5F5F7"       # Soft off-white
        c_surface_bg = "#FFFFFF"      # Pure white cards
        c_input_bg = "#FFFFFF"
        c_input_border = "#D1D1D6"
        
        # Text
        c_text_primary = "#1D1D1F"    # Dark gray
        c_text_secondary = "#86868B"
        c_text_inverted = "#FFFFFF"
        
        # Primary / Accents
        c_primary = "#007AFF"         # Deep Blue
        c_primary_hover = "#0062CC"
        c_primary_pressed = "#0051A8"
        
        # Status
        c_error = "#FF3B30"
        c_success = "#34C759"
        
        # Borders
        c_border = "#E5E5EA"
        
        # Special
        c_dropzone_bg = "rgba(255, 255, 255, 0.6)"
        c_dropzone_border = "#C7C7CC"
        c_dropzone_hover = "rgba(0, 122, 255, 0.05)"

    # Typography (System Font San Francisco equivalent)
    font_family = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

    # The QSS Template
    qss = f"""
    * {{
        font-family: {font_family};
        font-size: 13px;
        color: {c_text_primary};
        outline: none;
    }}
    
    QMainWindow, QDialog {{
        background-color: {c_window_bg};
    }}
    
    QTabWidget::pane {{
        border: 1px solid {c_border};
        background: {c_window_bg};
        border-radius: 4px;
    }}
    
    QTabBar::tab {{
        background: {c_window_bg};
        color: {c_text_secondary};
        padding: 8px 16px;
        border-bottom: 2px solid transparent;
        font-weight: 500;
    }}
    
    QTabBar::tab:selected {{
        color: {c_primary};
        border-bottom: 2px solid {c_primary};
    }}
    
    QTabBar::tab:hover {{
        color: {c_text_primary};
    }}

    /* --- Headings --- */
    QLabel[cssClass="h1"] {{
        font-size: 24px;
        font-weight: 700;
        color: {c_text_primary};
        margin-bottom: 8px;
    }}
    
    QLabel[cssClass="h2"] {{
        font-size: 18px;
        font-weight: 600;
        color: {c_text_primary};
        margin-bottom: 6px;
    }}
    
    QLabel[cssClass="subtitle"] {{
        font-size: 14px;
        color: {c_text_secondary};
    }}
    
    /* --- Cards --- */
    QFrame[cssClass="card"] {{
        background-color: {c_surface_bg};
        border: 1px solid {c_border};
        border-radius: 12px;
    }}
    
    QGroupBox {{
        background-color: {c_surface_bg};
        border: 1px solid {c_border};
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
        color: {c_text_primary};
    }}

    /* --- Buttons --- */
    QPushButton {{
        background-color: {c_surface_bg};
        border: 1px solid {c_border};
        border-radius: 6px;
        padding: 6px 16px;
        color: {c_text_primary};
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        background-color: {c_window_bg}; /* Slight darkening/lightening depending on mode context logic, kept simple here */
        border-color: {c_text_secondary}; 
    }}
    
    QPushButton:pressed {{
        background-color: {c_border};
    }}
    
    QPushButton:disabled {{
        color: {c_text_secondary};
        background-color: {c_window_bg};
        border-color: {c_border};
    }}

    /* Primary Action Button */
    QPushButton[cssClass="primary"] {{
        background-color: {c_primary};
        color: {c_text_inverted};
        border: 1px solid {c_primary};
        font-weight: 600;
        font-size: 14px;
        padding: 8px 20px;
        border-radius: 8px;
    }}
    
    QPushButton[cssClass="primary"]:hover {{
        background-color: {c_primary_hover};
        border-color: {c_primary_hover};
    }}
    
    QPushButton[cssClass="primary"]:pressed {{
        background-color: {c_primary_pressed};
        border-color: {c_primary_pressed};
    }}
    
    QPushButton[cssClass="primary"]:disabled {{
        background-color: {c_border};
        border-color: {c_border};
        color: {c_text_secondary};
    }}

    /* Ghost/Text Button */
    QPushButton[cssClass="ghost"] {{
        background-color: transparent;
        border: none;
        color: {c_primary};
    }}
    
    QPushButton[cssClass="ghost"]:hover {{
        color: {c_primary_hover};
        text-decoration: underline;
    }}

    /* --- Inputs --- */
    QLineEdit, QSpinBox, QComboBox {{
        background-color: {c_input_bg};
        border: 1px solid {c_input_border};
        border-radius: 6px;
        padding: 6px 8px;
        color: {c_text_primary};
        selection-background-color: {c_primary};
        selection-color: {c_text_inverted};
    }}
    
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {c_primary};
    }}
    
    /* --- Lists --- */
    QListWidget {{
        background-color: {c_input_bg};
        border: 1px solid {c_input_border};
        border-radius: 6px;
    }}
    
    QListWidget::item {{
        padding: 4px;
    }}
    
    QListWidget::item:selected {{
        background: {c_primary};
        color: {c_text_inverted};
        border-radius: 4px;
    }}

    /* --- Drop Zone --- */
    QFrame[cssClass="dropzone"] {{
        background-color: {c_dropzone_bg};
        border: 2px dashed {c_dropzone_border};
        border-radius: 12px;
    }}
    
    QFrame[cssClass="dropzone"]:hover {{
        background-color: {c_dropzone_hover};
        border-color: {c_primary};
    }}

    /* --- Scrollbars (Mac-like slim) --- */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {c_text_secondary};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QToolTip {{
        color: {c_text_primary};
        background-color: {c_surface_bg};
        border: 1px solid {c_border};
        padding: 4px;
        border-radius: 4px;
    }}
    """
    return qss
