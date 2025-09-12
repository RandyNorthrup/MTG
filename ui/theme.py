"""Modern theming system for MTG Commander application.

Provides consistent styling, colors, and UI components that match
professional Magic: The Gathering interfaces.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QFont, QLinearGradient
from PySide6.QtWidgets import QApplication

class MTGTheme:
    """Modern dark theme for MTG Commander application."""
    
    # Core colors
    BACKGROUND_DARK = QColor(15, 15, 18)
    BACKGROUND_MEDIUM = QColor(25, 25, 30)  
    BACKGROUND_LIGHT = QColor(35, 35, 40)
    CARD_BACKGROUND = QColor(20, 20, 25)
    
    # UI element colors
    BORDER_DARK = QColor(60, 60, 70)
    BORDER_MEDIUM = QColor(70, 70, 80)  # Added for enhanced card widgets
    BORDER_LIGHT = QColor(80, 80, 90)
    HOVER_HIGHLIGHT = QColor(70, 120, 180)
    ACTIVE_HIGHLIGHT = QColor(50, 100, 160)
    
    # Text colors
    TEXT_PRIMARY = QColor(230, 230, 235)
    TEXT_SECONDARY = QColor(180, 180, 190)
    TEXT_DISABLED = QColor(120, 120, 130)
    
    # Accent colors
    MANA_WHITE = QColor(249, 250, 244)
    MANA_BLUE = QColor(14, 104, 171)
    MANA_BLACK = QColor(21, 11, 0)
    MANA_RED = QColor(211, 32, 42)
    MANA_GREEN = QColor(0, 115, 62)
    MANA_COLORLESS = QColor(204, 194, 192)
    
    # Status colors
    SUCCESS = QColor(92, 184, 92)
    WARNING = QColor(240, 173, 78)
    DANGER = QColor(217, 83, 79)
    INFO = QColor(91, 192, 222)
    
    @classmethod
    def apply_theme(cls, app: QApplication):
        """Apply the dark theme to the entire application."""
        app.setStyle('Fusion')
        
        palette = QPalette()
        
        # Window colors
        palette.setColor(QPalette.Window, cls.BACKGROUND_DARK)
        palette.setColor(QPalette.WindowText, cls.TEXT_PRIMARY)
        
        # Base colors (for input fields, etc.)
        palette.setColor(QPalette.Base, cls.BACKGROUND_MEDIUM)
        palette.setColor(QPalette.AlternateBase, cls.BACKGROUND_LIGHT)
        
        # Text colors
        palette.setColor(QPalette.Text, cls.TEXT_PRIMARY)
        palette.setColor(QPalette.BrightText, cls.TEXT_PRIMARY)
        
        # Button colors
        palette.setColor(QPalette.Button, cls.BACKGROUND_LIGHT)
        palette.setColor(QPalette.ButtonText, cls.TEXT_PRIMARY)
        
        # Highlight colors
        palette.setColor(QPalette.Highlight, cls.HOVER_HIGHLIGHT)
        palette.setColor(QPalette.HighlightedText, cls.TEXT_PRIMARY)
        
        app.setPalette(palette)
    
    @classmethod
    def button_style(cls, variant='default'):
        """Get modern button styling."""
        base_style = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(45, 45, 50, 255),
                stop:1 rgba(35, 35, 40, 255));
            border: 1px solid rgba(80, 80, 90, 255);
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
            color: rgb(230, 230, 235);
            min-height: 20px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(70, 120, 180, 255),
                stop:1 rgba(50, 100, 160, 255));
            border: 1px solid rgba(100, 150, 200, 255);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(40, 80, 120, 255),
                stop:1 rgba(30, 70, 110, 255));
        }
        QPushButton:disabled {
            background: rgba(25, 25, 30, 255);
            border: 1px solid rgba(60, 60, 70, 255);
            color: rgb(120, 120, 130);
        }
        """
        
        if variant == 'primary':
            return base_style.replace(
                "rgba(45, 45, 50, 255)", "rgba(70, 120, 180, 255)"
            ).replace(
                "rgba(35, 35, 40, 255)", "rgba(50, 100, 160, 255)"
            )
        elif variant == 'success':
            return base_style.replace(
                "rgba(45, 45, 50, 255)", "rgba(92, 184, 92, 255)"
            ).replace(
                "rgba(35, 35, 40, 255)", "rgba(72, 164, 72, 255)"
            )
        elif variant == 'danger':
            return base_style.replace(
                "rgba(45, 45, 50, 255)", "rgba(217, 83, 79, 255)"
            ).replace(
                "rgba(35, 35, 40, 255)", "rgba(197, 63, 59, 255)"
            )
        
        return base_style
    
    @classmethod
    def card_style(cls):
        """Get card container styling."""
        return """
        QWidget {
            background: rgba(20, 20, 25, 255);
            border: 1px solid rgba(60, 60, 70, 255);
            border-radius: 8px;
        }
        QWidget:hover {
            border: 1px solid rgba(100, 150, 200, 255);
            background: rgba(25, 25, 32, 255);
        }
        """
    
    @classmethod
    def input_style(cls):
        """Get input field styling."""
        return """
        QLineEdit, QTextEdit, QSpinBox {
            background: rgba(25, 25, 30, 255);
            border: 1px solid rgba(80, 80, 90, 255);
            border-radius: 4px;
            padding: 6px 8px;
            font-size: 13px;
            color: rgb(230, 230, 235);
            selection-background-color: rgba(70, 120, 180, 255);
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
            border: 2px solid rgba(70, 120, 180, 255);
            background: rgba(30, 30, 35, 255);
        }
        QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled {
            background: rgba(20, 20, 25, 255);
            color: rgb(120, 120, 130);
            border: 1px solid rgba(60, 60, 70, 255);
        }
        """
    
    @classmethod
    def list_style(cls):
        """Get list widget styling."""
        return """
        QListWidget {
            background: rgba(20, 20, 25, 255);
            border: 1px solid rgba(80, 80, 90, 255);
            border-radius: 6px;
            outline: none;
            selection-background-color: rgba(70, 120, 180, 100);
        }
        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid rgba(40, 40, 45, 255);
            color: rgb(230, 230, 235);
        }
        QListWidget::item:selected {
            background: rgba(70, 120, 180, 150);
            border: none;
        }
        QListWidget::item:hover {
            background: rgba(50, 50, 55, 255);
        }
        QScrollBar:vertical {
            background: rgba(25, 25, 30, 255);
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: rgba(80, 80, 90, 255);
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(100, 100, 110, 255);
        }
        """
    
    @classmethod
    def group_box_style(cls):
        """Get group box styling."""
        return """
        QGroupBox {
            font-weight: bold;
            font-size: 14px;
            border: 2px solid rgba(80, 80, 90, 255);
            border-radius: 8px;
            margin: 6px 0px;
            padding-top: 10px;
            color: rgb(230, 230, 235);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: rgb(180, 180, 190);
        }
        """
    
    @classmethod
    def tab_style(cls):
        """Get tab widget styling."""
        return """
        QTabWidget::pane {
            border: 1px solid rgba(80, 80, 90, 255);
            background: rgba(20, 20, 25, 255);
        }
        QTabBar::tab {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(45, 45, 50, 255),
                stop:1 rgba(35, 35, 40, 255));
            border: 1px solid rgba(80, 80, 90, 255);
            padding: 8px 16px;
            margin-right: 2px;
            color: rgb(180, 180, 190);
        }
        QTabBar::tab:selected {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(70, 120, 180, 255),
                stop:1 rgba(50, 100, 160, 255));
            color: rgb(230, 230, 235);
        }
        QTabBar::tab:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(55, 55, 60, 255),
                stop:1 rgba(45, 45, 50, 255));
            color: rgb(210, 210, 220);
        }
        """
    
    @classmethod
    def phase_indicator_style(cls):
        """Get phase indicator styling."""
        return """
        QLabel {
            background: rgba(30, 30, 35, 255);
            border: 1px solid rgba(80, 80, 90, 255);
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
            font-size: 12px;
            color: rgb(180, 180, 190);
        }
        QLabel[active="true"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(70, 120, 180, 255),
                stop:1 rgba(50, 100, 160, 255));
            color: rgb(255, 255, 255);
            border: 1px solid rgba(100, 150, 200, 255);
        }
        """
    
    @classmethod  
    def player_panel_style(cls):
        """Get player panel styling."""
        return """
        QWidget {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(32, 32, 36, 255),
                stop:1 rgba(28, 28, 32, 255));
            border: 1px solid rgba(70, 70, 80, 255);
            border-radius: 8px;
        }
        QLabel {
            color: rgb(230, 230, 235);
            font-size: 12px;
        }
        """

def apply_modern_theme(app: QApplication):
    """Apply the modern MTG theme to the application."""
    MTGTheme.apply_theme(app)

# Export commonly used styles as constants
BUTTON_STYLE = MTGTheme.button_style()
PRIMARY_BUTTON_STYLE = MTGTheme.button_style('primary')
SUCCESS_BUTTON_STYLE = MTGTheme.button_style('success')
DANGER_BUTTON_STYLE = MTGTheme.button_style('danger')
CARD_STYLE = MTGTheme.card_style()
INPUT_STYLE = MTGTheme.input_style()
LIST_STYLE = MTGTheme.list_style()
GROUP_BOX_STYLE = MTGTheme.group_box_style()
TAB_STYLE = MTGTheme.tab_style()
PHASE_INDICATOR_STYLE = MTGTheme.phase_indicator_style()
PLAYER_PANEL_STYLE = MTGTheme.player_panel_style()
