import sys
import os  # ADDED
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Qt
from config import *
from ui.ui_manager import PlayArea
from ui.home_tab import build_home_tab
from ui.decks_tab import DecksTabManager
from ui.play_tab import build_play_stack
from ui.phase_ui import update_phase_ui as _phase_update
from ui.game_app_api import GameAppAPI
from engine.game_init import parse_args, create_initial_game, new_game  # ADDED (moved logic)

# --- Main Window Shell (logic delegated to GameAppAPI) ----------------------
class MainWindow(QMainWindow):
    def __init__(self, game, ai_ids, args):
        super().__init__()
        self.setWindowTitle("MTG Commander (Qt)")
        self.args = args
        self.api = GameAppAPI(self, game, ai_ids, args, new_game)  # still supply factory
        self.controller = self.api.controller
        self.game = self.api.game
        self.play_area = PlayArea(self.game)
        if hasattr(self.play_area, 'enable_drag_and_drop'):
            self.play_area.enable_drag_and_drop()
        self.logging_enabled = self.controller.logging_enabled
        self.tabs = QTabWidget()
        self._init_tabs()
        self.setCentralWidget(self.tabs)
        self._phase_timer = QTimer(self)
        self._phase_timer.timeout.connect(self.api.ai_tick)
        self._phase_timer.start(400)
        self._debug_win = None
        self.settings_manager = None
        self._update_phase_ui()

    def set_logging_enabled(self, value: bool):
        self.controller.logging_enabled = bool(value)
        self.logging_enabled = self.controller.logging_enabled

    def _init_tabs(self):
        home = build_home_tab(self.api)
        self.tabs.addTab(home, "Home")
        self.decks_manager = DecksTabManager(self.api)
        self.tabs.addTab(self.decks_manager.build_tab(), "Decks")
        self.play_stack, self.lobby_widget = build_play_stack(self.api)
        play_tab = QWidget()
        pv = QVBoxLayout(play_tab)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.addWidget(self.play_stack)
        self.tabs.addTab(play_tab, "Play")

    def _refresh_deck_tab(self):
        if hasattr(self, 'decks_manager'):
            self.decks_manager.refresh()

    def _update_phase_ui(self):
        if not getattr(self.controller, 'first_player_decided', False):
            return
        _phase_update(self)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
            return
        self.api.handle_key(e.key())

    # Legacy stubs
    def _reload_player0(self): self.api.reload_player0(getattr(self, 'current_deck_path', None))
    def _toggle_debug_window(self): self.api.toggle_debug_window()

# --- Entry ------------------------------------------------------------------
def main():
    # Optional: user can pre-create data/cards/cards.db or set MTG_SQL=1
    if os.path.exists(os.path.join('data','cards','cards.db')) and not os.environ.get('MTG_SQL'):
        os.environ['MTG_SQL'] = '1'
    args = parse_args()                      # moved out
    game, ai_ids = create_initial_game(args) # moved out
    app = QApplication(sys.argv)
    w = MainWindow(game=game, ai_ids=ai_ids, args=args)
    w.resize(SCREEN_W, SCREEN_H)
    w.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()