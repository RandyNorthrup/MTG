from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QTimer

class GameWindow(QMainWindow):
    """Enhanced game board window with professional UI components."""
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.bypass_quit_dialog = False  # Flag to bypass quit confirmation
        self.setWindowTitle("MTG Commander - Game Board")
        self.setMinimumSize(1280, 720)
        
        # Enhanced game board (no fallback - legacy UI removed)
        from ui.enhanced_game_board import create_enhanced_game_board
        self.play_area = create_enhanced_game_board(api)
        self.enhanced_mode = True
        print("✅ Enhanced game board loaded")

        # Setup window layout
        root = QWidget()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(4)

        # Top bar with controls (only if not enhanced mode - enhanced includes its own)
        if not self.enhanced_mode:
            bar = QHBoxLayout()
            self.phase_lbl = QLabel("Phase: —")
            self.phase_lbl.setStyleSheet("font-weight:bold; font-size:16px; padding:4px 0 4px 8px; background:#23242a; color:#e0e0e0;")
            bar.addWidget(self.phase_lbl)
            bar.addStretch(1)
            btn_dbg = QPushButton("Debug")
            btn_dbg.clicked.connect(api.toggle_debug_window)
            btn_close = QPushButton("Close")
            btn_close.clicked.connect(self.close)
            bar.addWidget(btn_dbg)
            bar.addWidget(btn_close)
            v.addLayout(bar)
        else:
            # Enhanced mode - just store phase label reference for compatibility
            self.phase_lbl = QLabel()  # Dummy for compatibility

        # Add the play area
        v.addWidget(self.play_area, 1)

        if self.width() < 1280 or self.height() < 720:
            self.resize(max(self.width(), 1280), max(self.height(), 720))
        
        # Initial phase refresh
        self.refresh_phase()

    def refresh_phase(self):
        # Show active player, phase, and step in the top bar (real time)
        game = getattr(self.api, "game", None)
        ctrl = getattr(self.api, "controller", None)
        if not game or not ctrl:
            self.phase_lbl.setText("Phase: —")
            return
        ap_i = getattr(game, "active_player", 0)
        ap_name = "Player"
        if hasattr(game, "players") and 0 <= ap_i < len(game.players):
            ap_name = getattr(game.players[ap_i], "name", ap_name)
        phase = getattr(ctrl, "current_phase", getattr(game, "phase", ""))
        step = getattr(ctrl, "current_step", "")
        # Human-friendly phase/step
        try:
            from engine.phase_hooks import _DISPLAY_NAMES
            phase_disp = _DISPLAY_NAMES.get(str(phase).lower(), str(phase).capitalize())
        except Exception:
            phase_disp = str(phase).capitalize()
        step_disp = str(step).capitalize() if step and step != phase else ""
        # Add debug information about hand size and library size
        hand_size = len(game.players[0].hand) if game.players and len(game.players) > 0 else 0
        lib_size = len(game.players[0].library) if game.players and len(game.players) > 0 else 0
        game_phase_index = getattr(game, 'phase_index', -1)
        
        text = f"<b>{ap_name}</b> | Phase: <b>{phase_disp}</b>"
        if step_disp:
            text += f" | Step: <b>{step_disp}</b>"
        text += f" | Hand: <b>{hand_size}</b> | Lib: <b>{lib_size}</b> | PI: <b>{game_phase_index}</b>"
        self.phase_lbl.setText(text)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
            
        # Don't allow keyboard interaction until game is properly started (after roll)
        if hasattr(self.play_area, '_should_show_waiting_overlay') and self.play_area._should_show_waiting_overlay():
            return
            
        self.api.handle_key(e.key())
        # Refresh everything after key action
        self.refresh_phase()
        if hasattr(self.play_area, "force_refresh"):
            self.play_area.force_refresh()



    def closeEvent(self, ev):
        # Check if we should bypass the quit dialog (e.g., main window closing)
        if self.bypass_quit_dialog:
            # Skip quit dialog and proceed with closing
            ev.accept()
            super().closeEvent(ev)
            return
            
        # Check if game is actually in progress
        game_in_progress = (
            hasattr(self.api, 'controller') and 
            hasattr(self.api.controller, 'in_game') and 
            self.api.controller.in_game and
            hasattr(self.api.controller, 'first_player_decided') and
            self.api.controller.first_player_decided
        )
        
        if game_in_progress:
            # Show quit confirmation dialog
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Quit Game", 
                "Are you sure you want to quit this game?\n\nThis will count as a loss.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                # User chose not to quit
                ev.ignore()
                return
            
            # User confirmed quit - record loss and cleanup
            try:
                self.api.handle_game_quit_loss()
            except Exception as e:
                if hasattr(self.api, 'controller') and self.api.controller.logging_enabled:
                    # Error during game quit handling (debug print removed)
                    pass
        
        # Proceed with closing
        try:
            if hasattr(self.api, 'handle_game_window_closed'):
                self.api.handle_game_window_closed()
        except Exception:
            pass
        
        # Accept the close event to actually close the window
        ev.accept()
        super().closeEvent(ev)

    def _confirm(self, title: str, text: str):  # ADDED
        from PySide6.QtWidgets import QMessageBox
        return QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) == QMessageBox.Yes

    def open(self):
        mw = getattr(self.api, 'w', None)
        if mw:
            try:
                g = mw.frameGeometry()
                # Ensure not smaller than minimums
                w = max(1280, int(g.width() * 0.9))
                h = max(720, int(g.height() * 0.9))
                self.resize(w, h)
                c = g.center()
                self.move(c.x() - self.width() // 2, c.y() - self.height() // 2)
            except Exception:
                pass
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.show()
        self.raise_()
        self.activateWindow()
        # Drop always-on-top shortly after showing so both windows stay interactive
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))
