from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget
from PySide6.QtCore import Qt
from ui.ui_manager import PlayArea
from engine.phase_hooks import update_phase_ui as _phase_update, install_phase_log_deduper

class GameWindow(QMainWindow):
    def __init__(self, api, game_id: str):
        super().__init__()
        self.api = api
        self.controller = api.controller
        install_phase_log_deduper(self.controller)
        self.game = self.controller.game
        self.setWindowTitle(f"Game {game_id}")
        # Stacked layout to reuse existing phase bar insertion logic (expects play_stack index1)
        self.play_stack = QStackedWidget()
        self.play_stack.addWidget(QWidget())  # placeholder index0
        board_wrap = QWidget()
        v = QVBoxLayout(board_wrap)
        v.setContentsMargins(0,0,0,0); v.setSpacing(2)
        top = QHBoxLayout()
        btn_close = QPushButton("Concede / Close")
        btn_phase = QPushButton("Advance Phase")          # ADDED
        btn_ai = QPushButton("AI Step")                   # ADDED
        btn_phase.clicked.connect(self._advance_phase)    # ADDED
        btn_ai.clicked.connect(self._ai_step)             # ADDED
        top.addWidget(btn_close)
        top.addWidget(btn_phase)
        top.addWidget(btn_ai)
        top.addStretch(1)
        v.addLayout(top)
        self.play_area = PlayArea(self.game)
        if hasattr(self.play_area, "enable_drag_and_drop"):
            self.play_area.enable_drag_and_drop()
        v.addWidget(self.play_area, 1)
        self.play_stack.addWidget(board_wrap)
        self.play_stack.setCurrentIndex(1)
        root = QWidget(); root_l = QVBoxLayout(root); root_l.setContentsMargins(0,0,0,0)
        root_l.addWidget(self.play_stack, 1)
        self.setCentralWidget(root)
        _phase_update(self)

    def _advance_phase(self):  # ADDED
        self.api.advance_phase()
        if hasattr(self.play_area, "refresh_board"):
            self.play_area.refresh_board()
        _phase_update(self)

    def _ai_step(self):  # ADDED
        self.api.ai_tick()
        if hasattr(self.play_area, "refresh_board"):
            self.play_area.refresh_board()
        _phase_update(self)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
        self.api.handle_key(e.key())
        if hasattr(self.play_area, "refresh_board"):
            self.play_area.refresh_board()
        _phase_update(self)

    def closeEvent(self, ev):
        try:
            self.api.handle_game_window_closed()
        except Exception:
            pass
        super().closeEvent(ev)
