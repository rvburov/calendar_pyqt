class Colors:
    BG             = "#FFFFFF"
    SECONDARY_BG   = "#F2F2F7"
    SEPARATOR      = "#E5E5EA"
    PRIMARY_TEXT   = "#1C1C1E"
    SECONDARY_TEXT = "#8E8E93"
    ACCENT         = "#007AFF"
    ACCENT_LIGHT   = "#E5F0FF"
    TODAY_TEXT     = "#FFFFFF"
    WEEKEND        = "#8E8E93"
    RED            = "#FF3B30"
    GREEN          = "#34C759"
    HOVER          = "#E5E5EA"
    WHITE          = "#FFFFFF"
    ACTIVITY_BAR   = "#EBEBEB"


APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {Colors.BG};
    color: {Colors.PRIMARY_TEXT};
    font-family: "Helvetica Neue", "Arial", sans-serif;
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: {Colors.SECONDARY_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {Colors.SEPARATOR};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{
    background: {Colors.SECONDARY_BG};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.SEPARATOR};
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
"""