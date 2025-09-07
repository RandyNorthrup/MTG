import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout

from config import *
from ui.home_tab import build_home_tab
from ui.decks_tab import DecksTabManager
from ui.game_app_api import GameAppAPI
from engine.game_init import parse_args, create_initial_game, new_game
from image_cache import teardown_cache, repair_cache  # REMOVED init_image_cache

# --- Main Window Shell (logic delegated to GameAppAPI) ----------------------
class MainWindow(QMainWindow):
    def __init__(self, game, ai_ids, args):
        super().__init__()
        self.setWindowTitle("MTG Commander (Qt)")
        self.args = args
        self.api = GameAppAPI(self, game, ai_ids, args, new_game)
        self.controller = self.api.controller
        self.game = self.api.game
        # REMOVED: embedded PlayArea & phase machinery (moved to GameWindow)
        self.logging_enabled = self.controller.logging_enabled
        self.tabs = QTabWidget()
        self._init_tabs()
        self.setCentralWidget(self.tabs)
        self._debug_win = None
        self.settings_manager = None

    def set_logging_enabled(self, value: bool):
        self.controller.logging_enabled = bool(value)
        self.logging_enabled = self.controller.logging_enabled

    def _init_tabs(self):
        home = build_home_tab(self.api)
        self.tabs.addTab(home, "Home")
        self.decks_manager = DecksTabManager(self.api)
        self.tabs.addTab(self.decks_manager.build_tab(), "Decks")
        # Lobby only (no board in main window)
        from ui.play_tab import build_play_stack
        self.play_stack, self.lobby_widget = build_play_stack(self.api)
        # Strip board page if present (keep lobby page only)
        # (build_play_stack returns a stack; we keep it for compatibility/lobby UI)
        play_tab = QWidget()
        v = QVBoxLayout(play_tab); v.setContentsMargins(0,0,0,0)
        v.addWidget(self.play_stack)
        self.tabs.addTab(play_tab, "Lobby")

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
        self.api.handle_key(e.key())

    def closeEvent(self, ev):  # ADDED graceful cache teardown
        # ADDED: ensure all auxiliary game windows / debug windows closed
        try:
            if hasattr(self, 'api'):
                self.api.shutdown()
        except Exception:
            pass
        teardown_cache()
        super().closeEvent(ev)

    # Legacy stubs
    def _reload_player0(self): self.api.reload_player0(getattr(self, 'current_deck_path', None))
    def _toggle_debug_window(self): self.api.toggle_debug_window()

# --- Entry ------------------------------------------------------------------
def _prepare_environment():
    """Set env toggles before game creation."""
    if os.path.exists(os.path.join("data", "cards", "cards.db")) and not os.environ.get("MTG_SQL"):
        os.environ["MTG_SQL"] = "1"

def main():
    """Application entry point."""
    _prepare_environment()
    args = parse_args()
    game, ai_ids = create_initial_game(args)
    app = QApplication(sys.argv)
    repair_cache()
    win = MainWindow(game=game, ai_ids=ai_ids, args=args)
    win.resize(SCREEN_W, SCREEN_H)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()