from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict
import time, uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QPushButton,
    QHBoxLayout, QListWidget, QLabel, QSplitter, QVBoxLayout as VBox
)
from PySide6.QtCore import Qt

# --- Lobby dataclasses and server (merged from engine/lobby.py) ---
@dataclass
class LobbyPlayer:
    name: str
    deck_path: Optional[str] = None
    ready: bool = False
    is_host: bool = False

@dataclass
class LobbyState:
    lobby_id: str
    created_ts: float
    players: List[LobbyPlayer] = field(default_factory=list)
    started: bool = False

class LobbyServer:
    lobbies: Dict[str, LobbyState] = {}

    @classmethod
    def create_lobby(cls, host_name: str, deck_path: Optional[str]) -> LobbyState:
        lob = LobbyState(lobby_id=str(uuid.uuid4()), created_ts=time.time())
        lob.players.append(LobbyPlayer(name=host_name, deck_path=deck_path, ready=False, is_host=True))
        cls.lobbies[lob.lobby_id] = lob
        return lob

    @classmethod
    def list_lobbies(cls) -> List[LobbyState]:
        return list(cls.lobbies.values())

    @classmethod
    def join(cls, lobby_id: str, player_name: str) -> Optional[LobbyState]:
        lob = cls.lobbies.get(lobby_id)
        if not lob or lob.started:
            return None
        if any(p.name == player_name for p in lob.players):
            return lob
        lob.players.append(LobbyPlayer(name=player_name))
        return lob

    @classmethod
    def set_deck(cls, lobby_id: str, player_name: str, path: str):
        lob = cls.lobbies.get(lobby_id)
        if not lob: return
        for p in lob.players:
            if p.name == player_name:
                p.deck_path = path
                p.ready = False

    @classmethod
    def set_ready(cls, lobby_id: str, player_name: str, ready: bool):
        lob = cls.lobbies.get(lobby_id)
        if not lob: return
        for p in lob.players:
            if p.name == player_name:
                p.ready = ready

    @classmethod
    def can_start(cls, lobby_id: str) -> bool:
        lob = cls.lobbies.get(lobby_id)
        if not lob or not lob.players:
            return False
        host = next((p for p in lob.players if p.is_host), None)
        if not host:
            return False
        return all(p.deck_path and p.ready for p in lob.players)

    @classmethod
    def mark_started(cls, lobby_id: str):
        lob = cls.lobbies.get(lobby_id)
        if lob:
            lob.started = True

class LobbyWidget(QWidget):
    def __init__(self, ctx):
        """
        ctx: GameAppAPI (preferred). For legacy fallback, a MainWindow may be passed.
        """
        super().__init__()
        self.ctx = ctx
        # Underlying window (for play_area / existing references)
        self._win = getattr(ctx, 'w', ctx)
        root = QHBoxLayout(self); root.setContentsMargins(4,4,4,4)
        splitter = QSplitter(); root.addWidget(splitter)

        # LEFT: players / status
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0)
        self.match_list = QListWidget(); self.match_list.setSelectionMode(QListWidget.SingleSelection)
        lv.addWidget(QLabel("Open Matches")); lv.addWidget(self.match_list, 1)

        row = QHBoxLayout()
        self.btn_create = QPushButton("Create")
        self.btn_add_ai = QPushButton("Add AI")
        self.btn_start = QPushButton("Start Game")
        self.btn_cancel = QPushButton("Cancel")
        for b in (self.btn_create, self.btn_add_ai, self.btn_start, self.btn_cancel):
            row.addWidget(b)
        lv.addLayout(row)

        self.status_lbl = QLabel(""); self.status_lbl.setStyleSheet("color:#bbb;font-size:11px;")
        lv.addWidget(self.status_lbl)

        # RIGHT: deck preview (player 0)
        right = QWidget(); rv = VBox(right); rv.setContentsMargins(0,0,0,0)
        rv.addWidget(QLabel("Your Deck (Commander + 99)"))
        self.deck_list = QListWidget(); self.deck_list.setAlternatingRowColors(True)
        rv.addWidget(self.deck_list, 1)
        self.deck_hint = QLabel(""); self.deck_hint.setStyleSheet("color:#999;font-size:11px;")
        rv.addWidget(self.deck_hint)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(0,3); splitter.setStretchFactor(1,2)

        # Wiring to API
        self.btn_create.clicked.connect(self._create_clicked)
        self.btn_add_ai.clicked.connect(self._add_ai_clicked)
        self.btn_start.clicked.connect(self._start_clicked)
        self.btn_cancel.clicked.connect(self._cancel_clicked)

        for b in (self.btn_add_ai, self.btn_start, self.btn_cancel):
            b.setEnabled(False)

        self._empty_state()
        self.refresh_deck()

    # --- UI helpers ---
    def _empty_state(self):
        self.match_list.clear()
        self.status_lbl.setText("No open matches. Press Create to start a local game.")

    def refresh_deck(self):
        self.deck_list.clear()
        g = getattr(self.ctx, 'game', None)
        if not g or not g.players:
            return
        p0 = g.players[0]; total = 0
        if p0.commander:
            self.deck_list.addItem(f"[Commander] {p0.commander.name}"); total += 1
        for c in p0.library:
            self.deck_list.addItem(c.name); total += 1
        self.deck_hint.setText(f"{total} cards listed.")

    # --- Button handlers mapped to API facade ---
    def _create_clicked(self):
        if hasattr(self.ctx, 'create_pending_match'):
            self.ctx.create_pending_match()

    def _add_ai_clicked(self):
        if hasattr(self.ctx, 'add_ai_player_pending'):
            self.ctx.add_ai_player_pending()

    def _start_clicked(self):
        if hasattr(self.ctx, 'start_pending_match'):
            self.ctx.start_pending_match()
            if hasattr(self.ctx, 'open_game_window'):
                self.ctx.open_game_window()  # NEW: launch separate window

    def _cancel_clicked(self):
        if hasattr(self.ctx, 'cancel_pending_match'):
            self.ctx.cancel_pending_match()

    # --- Pending lobby sync (called by API via window) ---
    def sync_pending_controls(self, active: bool):
        g = getattr(self.ctx, 'game', None)
        if not g:
            return
        # Only allow 2 players max
        self.btn_add_ai.setEnabled(active and len(g.players) == 1)
        self.btn_start.setEnabled(active and len(g.players) == 2)
        self.btn_cancel.setEnabled(active)
        self.btn_create.setEnabled(not active)
        self.status_lbl.setText(
            f"Waiting for players... ({len(g.players)}/2). Add AI or Start Game."
            if active else "No open matches. Press Create to start a local game."
        )
        self._render_players(active)
        # Auto-start when 2 players joined
        if active and len(g.players) == 2:
            if hasattr(self.ctx, 'start_pending_match'):
                self.ctx.start_pending_match()

    def _render_players(self, active: bool):
        if not active:
            self._empty_state(); return
        self.match_list.clear()
        g = getattr(self.ctx, 'game', None)
        ctrl = getattr(self.ctx, 'controller', None)
        ai_map = getattr(ctrl, 'ai_controllers', {}) if ctrl else {}
        for pl in g.players:
            tag = " (AI)" if pl.player_id in ai_map else ""
            self.match_list.addItem(f"{pl.player_id+1}. {pl.name}{tag}")

# --- Public builder ---
def build_play_stack(ctx):
    """
    Build the play stack (lobby + board). ctx is GameAppAPI.
    Returns (stack, lobby_widget)
    """
    stack = QStackedWidget()
    lobby = LobbyWidget(ctx)
    stack.addWidget(lobby)

    board_wrap = QWidget()
    v = QVBoxLayout(board_wrap); v.setContentsMargins(0,0,0,0); v.setSpacing(2)
    top = QHBoxLayout()
    btn_back = QPushButton("Return to Lobby")
    btn_back.clicked.connect(lambda: stack.setCurrentIndex(0))
    top.addWidget(btn_back); top.addStretch(1)
    v.addLayout(top)
    # Access play area from underlying window
    play_area = getattr(ctx.w, 'play_area', None)
    if play_area:
        v.addWidget(play_area, 1)
    else:
        warn = QLabel("PlayArea not initialized.")
        warn.setStyleSheet("color:orange;")
        v.addWidget(warn, 1)
    stack.addWidget(board_wrap)
    stack.setCurrentIndex(0)
    # Expose lobby to underlying window for API callbacks
    setattr(ctx.w, 'lobby_widget', lobby)
    return stack, lobby
