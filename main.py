"""MTG Commander Game - Main Application Entry Point.

Desktop Magic: The Gathering Commander game with full rules engine,
AI opponents, and modern Qt interface.
"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# Import enhanced UI components
from ui.theme import apply_modern_theme

from engine.game_init import create_initial_game, new_game, parse_args
from image_cache import repair_cache, teardown_cache
from ui.decks_tab import DecksTabManager
from ui.game_app_api import GameAppAPI
from ui.home_tab import build_home_tab
from ui.settings_window import SettingsWindow
from ui.enhanced_lobby import build_enhanced_play_stack

# Window sizing constants (moved from removed ui_manager)
def get_default_window_size():
    """Get default window size for application."""
    return 1200, 800

class MainWindow(QMainWindow):
    """Main application window for MTG Commander.
    
    Provides the tabbed interface and coordinates between UI components
    and the game engine. All game logic is delegated to GameAppAPI.
    
    Features:
    - Home tab: Quick start and game overview
    - Decks tab: Deck management and validation
    - Lobby tab: Game setup and player configuration
    - Settings: Application preferences
    
    Keyboard shortcuts:
    - F9: Debug window
    - Esc: Close application
    """
    
    def __init__(self, game, ai_ids, args):
        """Initialize the main window.
        
        Args:
            game: Initial GameState instance
            ai_ids: List of player IDs to be controlled by AI
            args: Command line arguments
        """
        super().__init__()
        self.setWindowTitle("MTG Commander Game")
        
        # Initialize core components
        self.api = GameAppAPI(self, game, ai_ids, args, new_game)
        self.controller = self.api.controller
        self.game = self.api.game
        self.logging_enabled = self.controller.logging_enabled
        
        # Setup main interface
        self.tabs = QTabWidget()
        self._init_tabs()
        self.setCentralWidget(self.tabs)
        
        # Initialize window references
        self._debug_win = None
        self.settings_window = None

    def set_logging_enabled(self, value: bool):
        """Toggle phase logging."""
        self.controller.logging_enabled = bool(value)
        self.logging_enabled = self.controller.logging_enabled

    def _init_tabs(self):
        """Initialize all main tabs with enhanced UI components."""
        home = build_home_tab(self.api)
        self.tabs.addTab(home, "Home")
        self.decks_manager = DecksTabManager(self.api)
        self.tabs.addTab(self.decks_manager.build_tab(), "Decks")
        
        # Enhanced lobby (no fallback - legacy UI removed)
        self.play_stack, self.lobby_widget = build_enhanced_play_stack(self.api)
        play_tab = QWidget()
        v = QVBoxLayout(play_tab)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.play_stack)
        self.tabs.addTab(play_tab, "🏛️ Enhanced Lobby")

    def open_settings_window(self):
        """Show the settings window."""
        if self.settings_window is None or not self.settings_window.isVisible():
            self.settings_window = SettingsWindow(self.api, self)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def keyPressEvent(self, e):
        """Delegate key events to the API."""
        if e.key() == Qt.Key_Escape:
            self.close()
            return
        self.api.handle_key(e.key())

    def closeEvent(self, ev):
        """Cleanup on close."""
        try:
            # Close all child windows first
            if hasattr(self, 'api'):
                # Close debug window
                if hasattr(self.api, '_debug_win') and self.api._debug_win:
                    self.api._debug_win.close()
                    
                # Force close game window without quit confirmation
                if hasattr(self.api, 'board_window') and self.api.board_window:
                    # Set bypass flag to skip quit dialog
                    self.api.board_window.bypass_quit_dialog = True
                    self.api.board_window.close()
                    
                self.api.shutdown()
                
            # Close settings window
            if hasattr(self, 'settings_window') and self.settings_window:
                self.settings_window.close()
                
        except Exception:
            pass
        teardown_cache()
        super().closeEvent(ev)

def _prepare_environment():
    """
    Prepare environment variables for database backend if needed.
    """
    if os.path.exists(os.path.join("data", "cards", "cards.db")) and not os.environ.get("MTG_SQL"):
        os.environ["MTG_SQL"] = "1"

def main():
    """
    Application entry point with enhanced UI integration.
    """
    _prepare_environment()
    args = parse_args()
    game, ai_ids = create_initial_game(args)
    
    # Create application and apply modern theme
    app = QApplication(sys.argv)
    
    # Apply the professional theme system
    try:
        apply_modern_theme(app)
        print("✅ Modern theme applied successfully")
    except Exception as e:
        print(f"⚠️  Warning: Failed to apply modern theme - {e}")
    
    repair_cache()
    win = MainWindow(game=game, ai_ids=ai_ids, args=args)
    w, h = get_default_window_size()
    win.resize(w, h)
    win.show()
    
    print("🚀 MTG Commander Enhanced UI is running!")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()