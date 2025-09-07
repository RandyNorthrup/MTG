from PySide6.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, QPushButton,
    QHBoxLayout, QListWidget, QLabel, QSplitter, QVBoxLayout as VBox, QListWidgetItem)
from PySide6.QtCore import Qt, QTimer
from ai.ai_helpers import add_ai_player_pending

class LobbyWidget(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.main_win = main_win
        root = QHBoxLayout(self); root.setContentsMargins(4,4,4,4)
        splitter = QSplitter(); root.addWidget(splitter)

        # Left side: players list / status
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0)
        self.match_list = QListWidget(); self.match_list.setSelectionMode(QListWidget.SingleSelection)
        lv.addWidget(QLabel("Open Matches")); lv.addWidget(self.match_list, 1)

        row = QHBoxLayout()
        self.btn_create = QPushButton("Create")
        self.btn_add_ai = QPushButton("Add AI")
        self.btn_start = QPushButton("Start Game")
        self.btn_cancel = QPushButton("Cancel")
        for b in (self.btn_create, self.btn_add_ai, self.btn_start, self.btn_cancel): row.addWidget(b)
        lv.addLayout(row)

        self.status_lbl = QLabel(""); self.status_lbl.setStyleSheet("color:#bbb;font-size:11px;")
        lv.addWidget(self.status_lbl)

        # Right: Player 0 deck preview
        right = QWidget(); rv = VBox(right); rv.setContentsMargins(0,0,0,0)
        rv.addWidget(QLabel("Your Deck (Commander + 99)"))
        self.deck_list = QListWidget(); self.deck_list.setAlternatingRowColors(True)
        rv.addWidget(self.deck_list, 1)
        self.deck_hint = QLabel(""); self.deck_hint.setStyleSheet("color:#999;font-size:11px;")
        rv.addWidget(self.deck_hint)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(0,3); splitter.setStretchFactor(1,2)

        self.btn_create.clicked.connect(self._create_clicked)
        self.btn_add_ai.clicked.connect(lambda: add_ai_player_pending(self.main_win))
        self.btn_start.clicked.connect(lambda: self.main_win._start_pending_match())
        self.btn_cancel.clicked.connect(lambda: self.main_win._cancel_pending_match())

        for b in (self.btn_add_ai, self.btn_start, self.btn_cancel): b.setEnabled(False)
        self._empty_state()
        self.refresh_deck()

    def _empty_state(self):
        self.match_list.clear()
        self.status_lbl.setText("No open matches. Press Create to start a local game.")

    def refresh_deck(self):
        self.deck_list.clear()
        g = self.main_win.game
        if not g or not g.players: return
        p0 = g.players[0]; total = 0
        if p0.commander:
            self.deck_list.addItem(f"[Commander] {p0.commander.name}"); total += 1
        for c in p0.library:
            self.deck_list.addItem(c.name); total += 1
        self.deck_hint.setText(f"{total} cards listed.")

    def _create_clicked(self):
        self.main_win._create_pending_match()

    def sync_pending_controls(self, active: bool):
        g = self.main_win.game
        self.btn_add_ai.setEnabled(active and len(g.players) < 4)
        self.btn_start.setEnabled(active and len(g.players) >= 1)
        self.btn_cancel.setEnabled(active)
        self.btn_create.setEnabled(not active)
        self.status_lbl.setText(
            f"Waiting for players... ({len(g.players)}/4). Add AI or Start Game."
            if active else "No open matches. Press Create to start a local game."
        )
        self._render_players(active)

    def _render_players(self, active: bool):
        if not active:
            self._empty_state(); return
        self.match_list.clear()
        for pl in self.main_win.game.players:
            tag = " (AI)" if pl.player_id in getattr(self.main_win.controller, 'ai_controllers', {}) else ""
            self.match_list.addItem(f"{pl.player_id+1}. {pl.name}{tag}")

def build_play_stack(main_win):
    """
    Returns (play_stack_widget, lobby_widget)
    """
    stack = QStackedWidget()
    lobby = LobbyWidget(main_win)
    stack.addWidget(lobby)

    board_wrap = QWidget()
    v = QVBoxLayout(board_wrap); v.setContentsMargins(0,0,0,0); v.setSpacing(2)
    top = QHBoxLayout()
    btn_back = QPushButton("Return to Lobby")
    btn_back.clicked.connect(lambda: stack.setCurrentIndex(0))
    top.addWidget(btn_back); top.addStretch(1)
    v.addLayout(top)
    v.addWidget(main_win.play_area, 1)
    stack.addWidget(board_wrap)
    stack.setCurrentIndex(0)
    return stack, lobby
