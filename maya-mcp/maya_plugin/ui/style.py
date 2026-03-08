"""QSS stylesheet constants for Maya MCP Panel."""

# Colors matching Maya's dark theme
BG_PRIMARY = "#3a3a3a"
BG_SECONDARY = "#444444"
BG_INPUT = "#2b2b2b"
TEXT_PRIMARY = "#cccccc"
TEXT_SECONDARY = "#999999"
ACCENT = "#5285a6"
ACCENT_HOVER = "#6ba0c4"
SUCCESS = "#4CAF50"
ERROR = "#F44336"
WARNING = "#FF9800"
BORDER = "#555555"

PANEL_STYLE = f"""
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_PRIMARY};
}}
QTabBar::tab {{
    background: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    padding: 6px 16px;
    border: 1px solid {BORDER};
    border-bottom: none;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {ACCENT};
    color: white;
}}
QPushButton {{
    background: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    padding: 6px 14px;
    border-radius: 3px;
}}
QPushButton:hover {{
    background: {ACCENT_HOVER};
    color: white;
}}
QPushButton:pressed {{
    background: {ACCENT};
}}
QPushButton:disabled {{
    background: {BG_PRIMARY};
    color: {TEXT_SECONDARY};
}}
QComboBox, QSpinBox, QTextEdit, QPlainTextEdit, QLineEdit {{
    background: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    padding: 4px;
    border-radius: 2px;
}}
QProgressBar {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    text-align: center;
    color: {TEXT_PRIMARY};
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 2px;
}}
QLabel {{
    color: {TEXT_PRIMARY};
}}
QScrollArea {{
    border: none;
}}
"""
