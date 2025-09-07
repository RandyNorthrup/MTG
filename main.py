import sys, os, json, re, argparse
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                               QVBoxLayout, QLabel, QPushButton, QMessageBox,
                               QListWidget, QListWidgetItem, QHBoxLayout, QLineEdit,
                               QStackedWidget, QSplitter)  # ADDED QStackedWidget, QSplitter
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap, QPainter
from config import *
from engine.game_state import GameState, PlayerState
from engine.game_controller import GameController
from ui.ui_manager import PlayArea              # CHANGED: direct import (no fallback)
from image_cache import ensure_card_image       # CHANGED: direct import (no fallback)
from engine.rules_engine import init_rules      # CHANGED: direct import (no fallback)

try:
    from mtgsdk import Card as MTGSDKCard  # type: ignore  # suppress pylance missing import
    _HAVE_MTGSDK = True
except Exception:
    _HAVE_MTGSDK = False

# --- added: ensure globals exist before use ---
_SDK_ONLINE = False          # set in main() if flag provided
_SDK_INJECT_CACHE = {}       # injected SDK-fetched cards

_NORMALIZE_RE = re.compile(r'[^a-z0-9]+')
def _normalize_name(s: str) -> str:
    return _NORMALIZE_RE.sub(' ', s.lower()).strip()

_CARD_DB_CACHE = None   # (by_id, by_name_lower, by_norm, path)
_CARD_NAME_LIST = None  # cached sorted list of names for deck editor search

def load_card_db(force: bool = False):
    global _CARD_DB_CACHE, _CARD_NAME_LIST
    if _CARD_DB_CACHE is not None and not force:
        return _CARD_DB_CACHE
    base = os.path.join('data','cards','card_db.json')
    full = os.path.join('data','cards','card_db_full.json')
    path = full if os.path.exists(full) else base
    with open(path,'r',encoding='utf-8') as f:
        raw = json.load(f)
    raw_cards = list(raw.values()) if isinstance(raw, dict) else list(raw)
    cards = []
    for c in raw_cards:
        if isinstance(c, dict) and 'id' in c and 'name' in c:
            cards.append(c)
    by_id = {c['id']:c for c in cards}
    by_name_lower = {c['name'].lower(): c for c in cards}
    by_norm = {_normalize_name(c['name']): c for c in cards}
    _CARD_DB_CACHE = (by_id, by_name_lower, by_norm, path)
    _CARD_NAME_LIST = sorted(by_name_lower.keys())
    return _CARD_DB_CACHE

def get_card_name_list():
    if _CARD_NAME_LIST is None:
        load_card_db()
    # Return human-readable (capitalized) names from by_id to preserve original case
    by_id, *_ = load_card_db()
    return sorted({c['name'] for c in by_id.values()})

def _sdk_card_pick(name: str):
    """
    Internal: return first best mtgsdk Card object for a given name (case-insensitive),
    or raise KeyError.
    """
    if not (_SDK_ONLINE and _HAVE_MTGSDK):
        raise KeyError(name)
    q = MTGSDKCard.where(name=name).all()
    if not q:
        # fallback broad search (can be large; keep first page)
        q = MTGSDKCard.where(page=1).all()
    # exact (case-insensitive) preference
    for c in q:
        if c.name.lower() == name.lower():
            return c
    if q:
        return q[0]
    raise KeyError(name)

def _sdk_fetch_rulings(card_obj):
    """Return list of ruling text strings for an mtgsdk Card (best-effort)."""
    try:
        raw = MTGSDKCard.rulings(card_obj.id)
        if raw:
            return [f"{r.get('date','')}: {r.get('text','')}" for r in raw]
    except Exception:
        pass
    return []

def _sdk_fetch_card(name: str):
    """
    Online fallback: fetch full card info via mtgsdk.
    Populates: mana_cost (generic int), mana_cost_str, power, toughness, text, color_identity, rulings.
    """
    pick = _sdk_card_pick(name)  # may raise KeyError
    cid = pick.id or pick.multiverse_id or (pick.set + ":" + pick.number)
    # Type parsing
    types = []
    if pick.type:
        main = pick.type.split('—')[0].strip()
        for t in main.replace('-', ' ').split():
            if t and t[0].isalpha():
                types.append(t)
    mana_cost_str = pick.mana_cost or ""
    # compute a simple generic numeric fallback (sum of generic + colored pips)
    total_cost = 0
    for num in re.findall(r'\{(\d+)\}', mana_cost_str):
        total_cost += int(num)
    total_cost += len(re.findall(r'\{[WUBRG]\}', mana_cost_str))
    rulings = _sdk_fetch_rulings(pick)
    card_dict = {
        'id': cid,
        'name': pick.name,
        'types': types or ['Card'],
        'mana_cost': total_cost,
        'mana_cost_str': mana_cost_str,
        'power': pick.power if (pick.power and pick.power.isdigit()) else None,
        'toughness': pick.toughness if (pick.toughness and pick.toughness.isdigit()) else None,
        'text': pick.text or "",
        'color_identity': pick.color_identity or [],
        'rulings': rulings
    }
    return card_dict

def _inject_sdk_card(c):
    """Insert fetched card into runtime caches so normal flow can use it."""
    global _CARD_DB_CACHE, _CARD_NAME_LIST
    if _CARD_DB_CACHE is None:
        return
    by_id, by_name_lower, by_norm, path = _CARD_DB_CACHE
    by_id[c['id']] = c
    by_name_lower[c['name'].lower()] = c
    by_norm[_normalize_name(c['name'])] = c
    _SDK_INJECT_CACHE[c['id']] = c
    _CARD_NAME_LIST = sorted(by_name_lower.keys())

def _resolve_entry(entry: str, by_id, by_name_lower, by_norm, deck_path, db_path):
    orig = entry
    if entry in by_id:
        return by_id[entry]
    low = entry.lower()
    c = by_name_lower.get(low)
    if c:
        return c
    c = by_norm.get(_normalize_name(entry))
    if c:
        return c
    matches = [v for k, v in by_name_lower.items() if k.startswith(low)]
    if len(matches) == 1:
        return matches[0]
    # NEW: SDK fallback
    try:
        fetched = _sdk_fetch_card(entry)
        _inject_sdk_card(fetched)
        return fetched
    except KeyError:
        pass
    raise KeyError(f"Card '{orig}' not found (deck={deck_path} db={db_path}{' sdk' if _SDK_ONLINE else ''})")

def _build_cards(entries, commander_name, *, by_id, by_name_lower, by_norm, db_path_used, deck_path, owner_id):
    from engine.card_engine import Card
    from engine.rules_engine import parse_and_attach
    cards = []
    commander_card = _resolve_entry(commander_name, by_id, by_name_lower, by_norm, deck_path, db_path_used) if commander_name else None
    for e in entries:
        c = _resolve_entry(e, by_id, by_name_lower, by_norm, deck_path, db_path_used)
        if commander_card and c['id'] == commander_card['id']:
            continue
        card_obj = Card(
            id=c['id'], name=c['name'], types=c['types'], mana_cost=c['mana_cost'],
            power=c.get('power'), toughness=c.get('toughness'), text=c.get('text', ''),
            is_commander=False, color_identity=c.get('color_identity', []),
            owner_id=owner_id, controller_id=owner_id
        )
        if 'mana_cost_str' in c:
            setattr(card_obj, 'mana_cost_str', c['mana_cost_str'])
        parse_and_attach(card_obj)
        cards.append(card_obj)
    commander_obj = None
    if commander_card:
        from engine.card_engine import Card
        commander_obj = Card(
            id=commander_card['id'], name=commander_card['name'], types=commander_card['types'],
            mana_cost=commander_card['mana_cost'], power=commander_card.get('power'),
            toughness=commander_card.get('toughness'), text=commander_card.get('text', ''),
            is_commander=True,  # CHANGED (was False) so engine can differentiate
            color_identity=commander_card.get('color_identity', []),
            owner_id=owner_id, controller_id=owner_id
        )
        if 'mana_cost_str' in commander_card:
            setattr(commander_obj, 'mana_cost_str', commander_card['mana_cost_str'])
        parse_and_attach(commander_obj)
    return cards, commander_obj

def load_deck(path, by_id, by_name_lower, by_norm, db_path_used, owner_id):
    entries, commander_name = parse_deck_txt_file(path)
    return _build_cards(entries, commander_name,
                        by_id=by_id, by_name_lower=by_name_lower, by_norm=by_norm,
                        db_path_used=db_path_used, deck_path=path, owner_id=owner_id)

def load_banlist(path):
    banned = set()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    banned.add(line)
    return banned

def parse_args():
    ap = argparse.ArgumentParser(description="MTG Commander (Qt)")
    ap.add_argument('--deck', action='append', metavar='NAME=PATH[:AI]',
                    help='Add player deck (optional :AI suffix)')
    ap.add_argument('--no-ai', action='store_true')
    ap.add_argument('--no-log', action='store_true')
    ap.add_argument('--sdk-online', action='store_true',
                    help='Enable mtg-sdk-python online lookup for missing cards')
    return ap.parse_args()

def _deck_specs_from_args(arg_list):
    specs = []
    if not arg_list:
        return specs
    for spec in arg_list:
        if '=' not in spec:
            print(f"[ARGS] Ignored malformed --deck '{spec}' (missing '=')")
            continue
        name, rest = spec.split('=',1)
        ai_flag = False
        path = rest
        if ':' in rest:
            path, tag = rest.rsplit(':',1)
            ai_flag = (tag.upper() == 'AI')
        if not os.path.exists(path):
            print(f"[ARGS] Deck file not found: {path}")
        specs.append((name, path, ai_flag))
    return specs

def _enrich_game_cards_with_sdk(game):
    """
    For each unique card name in players' libraries/commander (that lacks detailed fields),
    fetch full SDK data (if online) and update the Card objects in-place.
    Re-runs parse_and_attach after updating text.
    """
    if not (_SDK_ONLINE and _HAVE_MTGSDK):
        return
    from engine.rules_engine import parse_and_attach
    seen = set()
    for pl in game.players:
        pools = []
        if pl.commander:
            pools.append([pl.commander])
        pools.append(pl.library)
        for cards in pools:
            for card in cards:
                if not card or card.name in seen:
                    continue
                # Heuristic: enrich if text missing OR mana_cost_str missing OR rulings absent
                needs = (
                    not getattr(card, 'mana_cost_str', None) or
                    not getattr(card, 'text', None) or
                    not hasattr(card, 'rulings')
                )
                if not needs:
                    continue
                try:
                    data = _sdk_fetch_card(card.name)
                except KeyError:
                    continue
                # apply fields
                if data.get('mana_cost_str'):
                    setattr(card, 'mana_cost_str', data['mana_cost_str'])
                if data.get('text'):
                    card.text = data['text']
                if data.get('power') and data.get('toughness'):
                    try:
                        card.power = int(data['power'])
                        card.toughness = int(data['toughness'])
                    except Exception:
                        pass
                if 'rulings' in data:
                    setattr(card, 'rulings', data['rulings'])
                # Re-attach rules to reflect updated text
                try:
                    parse_and_attach(card)
                except Exception:
                    pass
                seen.add(card.name)

def new_game(deck_specs=None, ai_enabled=True):
    by_id, by_name_lower, by_norm, db_path_used = load_card_db()
    decks_dir = os.path.join('data', 'decks')
    os.makedirs(decks_dir, exist_ok=True)
    deck_files = sorted([os.path.join(decks_dir, f) for f in os.listdir(decks_dir) if f.lower().endswith('.txt')])
    # Auto-pick opponent (AI) deck = first deck file
    auto_ai_deck = deck_files[0] if deck_files else os.path.join(decks_dir, 'missing_ai_deck.txt')
    auto_player_deck = os.path.join(decks_dir, 'custom_deck.txt')
    if not os.path.exists(auto_player_deck):
        # fallback: use second deck file if distinct, else first
        if len(deck_files) > 1:
            auto_player_deck = deck_files[1]
        elif deck_files:
            auto_player_deck = deck_files[0]
    if not deck_specs:
        deck_specs = [
            ("You", auto_player_deck, False),
            ("AI", auto_ai_deck, True if ai_enabled else False)
        ]
        print(f"[AUTO-DECK] Player0={os.path.basename(auto_player_deck)}  AI={os.path.basename(auto_ai_deck)}")
    banlist = load_banlist(os.path.join('data','commander_banlist.txt'))
    players = []
    for pid, (name, path, use_ai) in enumerate(deck_specs):
        try:
            cards, commander = load_deck(path, by_id, by_name_lower, by_norm, db_path_used, pid)
        except Exception as e:
            print(f"[DECK][{name}] Load error: {e}")
            cards, commander = [], None
        players.append(PlayerState(player_id=pid, name=name, life=STARTING_LIFE, library=cards, commander=commander))
        # ADDED: persist original deck path for reload logic
        try:
            players[-1].source_path = path
        except Exception:
            pass
    game = GameState(players=players)
    game.setup()
    init_rules(game)  # now safely imported
    # --- NEW: defer opening hand draw until after roll ---
    for pl in game.players:
        if hasattr(pl, 'hand') and pl.hand:
            original = list(pl.hand)
            pl.hand.clear()
            # Preserve original order on top of library
            pl.library = original + pl.library
    setattr(game, '_opening_hands_deferred', True)
    # Prewarm (fire-and-forget) images for current decks (commander + first N)
    for pl in game.players:
        if pl.commander:
            ensure_card_image(pl.commander.id)
        for c in list(pl.library)[:25]:
            ensure_card_image(c.id)
    ai_players = {pid for pid, (_, _, ai_flag) in enumerate(deck_specs) if ai_flag and ai_enabled}
    return game, ai_players

class ScaledBackground(QWidget):  # NEW
    def __init__(self, img_path):
        super().__init__()
        self._pix = QPixmap(img_path)

    def paintEvent(self, ev):
        if self._pix.isNull():
            return
        p = QPainter(self)
        # Stretch to exact widget size (no aspect ratio preservation per prior request)
        p.drawPixmap(self.rect(), self._pix)

class LobbyWidget(QWidget):
    """
    Simple local lobby mock:
      - Left: match groups (static sample entries)
      - Right: player deck (commander + main deck list) read-only
    """
    def __init__(self, main_win: 'MainWindow'):
        super().__init__()
        self.main_win = main_win
        root = QHBoxLayout(self)
        root.setContentsMargins(4,4,4,4)

        splitter = QSplitter()
        root.addWidget(splitter)

        # LEFT: Matches
        left = QWidget()
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0)
        self.match_list = QListWidget()
        self.match_list.setSelectionMode(QListWidget.SingleSelection)
        lv.addWidget(QLabel("Open Matches"))
        lv.addWidget(self.match_list, 1)

        btn_row = QHBoxLayout()
        self.btn_join = QPushButton("Join")
        self.btn_create = QPushButton("Create")
        # NEW pending queue controls
        self.btn_add_ai = QPushButton("Add AI")
        self.btn_start = QPushButton("Start Game")
        self.btn_cancel = QPushButton("Cancel")
        btn_row.addWidget(self.btn_join)
        btn_row.addWidget(self.btn_create)
        btn_row.addWidget(self.btn_add_ai)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_cancel)
        lv.addLayout(btn_row)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color:#bbb;font-size:11px;")
        lv.addWidget(self.status_lbl)

        # RIGHT: Deck panel
        right = QWidget()
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0)
        rv.addWidget(QLabel("Your Deck (Commander + 99)"))
        self.deck_list = QListWidget()
        self.deck_list.setAlternatingRowColors(True)
        rv.addWidget(self.deck_list, 1)
        self.deck_hint = QLabel("")
        self.deck_hint.setStyleSheet("color:#999;font-size:11px;")
        rv.addWidget(self.deck_hint)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.btn_join.clicked.connect(self._join_clicked)
        self.btn_create.clicked.connect(self._create_clicked)
        self.btn_add_ai.clicked.connect(self._add_ai_clicked)
        self.btn_start.clicked.connect(self._start_clicked)
        self.btn_cancel.clicked.connect(self._cancel_clicked)

        # HIDE join (no fake matches now)
        self.btn_join.setVisible(False)
        # NEW: initial disabled state for pending controls
        for b in (self.btn_add_ai, self.btn_start, self.btn_cancel):
            b.setEnabled(False)

        self._populate_matches()
        self.refresh_deck()

    def _populate_matches(self):
        # Removed fake sample brackets; show empty state
        self.match_list.clear()
        self.status_lbl.setText("No open matches. Press Create to start a local game.")

    def refresh_deck(self):
        self.deck_list.clear()
        game = self.main_win.game
        if not game or not game.players:
            return
        p0 = game.players[0]
        total = 0
        if p0.commander:
            self.deck_list.addItem(f"[Commander] {p0.commander.name}")
            total += 1
        for c in p0.library:
            self.deck_list.addItem(c.name)
            total += 1
        self.deck_hint.setText(f"{total} cards listed.")
        self.deck_list.scrollToTop()

    def _join_clicked(self):
        cur = self.match_list.currentItem()
        if not cur:
            self.status_lbl.setText("Select a match/player row first.")
            return
        self.main_win._enter_match_from_lobby(join_existing=True)

    def _create_clicked(self):
        # NEW: start pending match instead of immediate game start
        self.main_win._create_pending_match()

    # NEW: button handlers for pending queue
    def _add_ai_clicked(self):
        self.main_win._add_ai_player_pending()

    def _start_clicked(self):
        self.main_win._start_pending_match()

    def _cancel_clicked(self):
        self.main_win._cancel_pending_match()

    # NEW: update UI for pending state
    def sync_pending_controls(self, active: bool):
        self.btn_add_ai.setEnabled(active and len(self.main_win.game.players) < 4)
        self.btn_start.setEnabled(active and len(self.main_win.game.players) >= 1)
        self.btn_cancel.setEnabled(active)
        self.btn_create.setEnabled(not active)
        self.status_lbl.setText(
            "Waiting for players... ({}/4). Add AI or Start Game.".format(len(self.main_win.game.players))
            if active else "No open matches. Press Create to start a local game."
        )
        self._render_pending_player_list(active)

    def _render_pending_player_list(self, active: bool):
        if not active:
            self._populate_matches()
            return
        self.match_list.clear()
        for pl in self.main_win.game.players:
            tag = " (AI)" if pl.player_id in getattr(self.main_win.controller, 'ai_controllers', {}) else ""
            self.match_list.addItem(f"{pl.player_id+1}. {pl.name}{tag}")

class MainWindow(QMainWindow):
    def __init__(self, game, ai_ids, args):
        super().__init__()
        self.setWindowTitle("MTG Commander (Qt)")
        self.args = args
        self.controller = GameController(game, ai_ids, logging_enabled=not (args and args.no_log))
        self.game = self.controller.game
        self.play_area = PlayArea(self.game)
        if hasattr(self.play_area, 'enable_drag_and_drop'):
            self.play_area.enable_drag_and_drop()
        # REMOVED: manual TurnManager creation & self.logging_enabled direct member (controller handles it)
        self._active_lobby_id = None
        self._phase_timer = QTimer(self)
        self._phase_timer.timeout.connect(self._maybe_ai_step)
        self._phase_timer.start(400)
        self.controller.log_phase()
        # Backward compat: mirror logging flag (read-only alias expectation)
        self.logging_enabled = self.controller.logging_enabled
        self.tabs = QTabWidget()                           # ADDED
        self._deck_editor_state_init()                     # ADDED
        self._init_tabs()                                  # ADDED
        self.setCentralWidget(self.tabs)                   # ADDED
        self._debug_win = None                             # ADDED: debug window handle

    # Backward compatibility helper (old code maybe toggles self.logging_enabled)
    def set_logging_enabled(self, value: bool):
        self.controller.logging_enabled = bool(value)
        self.logging_enabled = self.controller.logging_enabled

    # ADDED: deck editor state holder
    def _deck_editor_state_init(self):
        self.current_deck_path = os.path.join('data', 'decks', 'custom_deck.txt')
        self.current_deck_cards = []
        self.current_commander = None

    # ADDED: build tabs (Home, Decks, Play)
    def _init_tabs(self):
        home_bg = os.path.join('data', 'images', 'home_bg.png')
        if os.path.exists(home_bg):
            home = ScaledBackground(home_bg)
        else:
            home = QWidget()
        hv = QVBoxLayout(home); hv.setContentsMargins(0,0,0,0); hv.addStretch(1)
        self.tabs.addTab(home, "Home")
        self.tabs.addTab(self._build_decks_tab(), "Decks")
        play_tab = QWidget()
        pv = QVBoxLayout(play_tab); pv.setContentsMargins(0,0,0,0)
        pv.addWidget(self._build_play_tab_stack())
        self.tabs.addTab(play_tab, "Play")

    # ADDED: decks tab
    def _build_decks_tab(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(6,6,6,6)
        top = QHBoxLayout()
        self.deck_search_box = QLineEdit()
        self.deck_search_box.setPlaceholderText("Search (substring)")
        self.deck_search_box.textChanged.connect(self._refresh_deck_tab)
        btn_reload = QPushButton("Reload Player 0 Deck")
        btn_reload.clicked.connect(self._reload_player0)
        top.addWidget(self.deck_search_box, 1)
        top.addWidget(btn_reload)
        v.addLayout(top)
        self.deck_list_widget = QListWidget()
        v.addWidget(self.deck_list_widget, 1)
        self.deck_summary_lbl = QLabel("")
        self.deck_summary_lbl.setStyleSheet("color:#777;font-size:11px;")
        v.addWidget(self.deck_summary_lbl)
        self._refresh_deck_tab()
        return w

    # ADDED: refresh deck list
    def _refresh_deck_tab(self):
        if not hasattr(self, 'deck_list_widget'): return
        if not self.game or not self.game.players: return
        try:
            p0 = self.game.players[0]
        except Exception:
            return
        term = (self.deck_search_box.text().strip().lower()
                if self.deck_search_box.text() else "")
        rows = []
        if p0.commander:
            rows.append(("Commander", p0.commander.name))
        for c in p0.library:
            rows.append(("Library", c.name))
        for c in getattr(p0, 'hand', []):
            rows.append(("Hand", c.name))
        self.deck_list_widget.clear()
        shown = 0
        for zone, name in rows:
            if term and term not in name.lower():
                continue
            self.deck_list_widget.addItem(f"{zone}: {name}")
            shown += 1
        self.deck_summary_lbl.setText(f"Player0 cards (shown {shown}/{len(rows)})")

    # ADDED: stacked play (lobby + board)
    def _build_play_tab_stack(self):
        self.play_stack = QStackedWidget()
        self.lobby_widget = LobbyWidget(self)
        self.play_stack.addWidget(self.lobby_widget)
        wrap = QWidget()
        v = QVBoxLayout(wrap); v.setContentsMargins(0,0,0,0); v.setSpacing(2)
        top = QHBoxLayout()
        self.btn_return_lobby = QPushButton("Return to Lobby")
        self.btn_return_lobby.clicked.connect(lambda: self.play_stack.setCurrentIndex(0))
        top.addWidget(self.btn_return_lobby); top.addStretch(1)
        v.addLayout(top)
        v.addWidget(self.play_area, 1)
        self.play_stack.addWidget(wrap)
        self.play_stack.setCurrentIndex(0)
        return self.play_stack

    # CHANGED: ensure play_stack exists before switching
    def _enter_match_from_lobby(self, join_existing: bool):
        if getattr(self, 'pending_match_active', False):
            # In queued flow we start via Start Game button only
            return
        self.controller.ensure_ai_opponent(new_game)
        if hasattr(self, 'play_stack'):
            self.play_stack.setCurrentIndex(1)
        self.controller.enter_match()
        if len(self.game.players) > 1:
            # Prompt for first player roll
            QTimer.singleShot(50, self._prompt_first_player_roll)
        else:
            # Single-player immediate start
            self.controller.set_starter(0)
        if self.controller.logging_enabled:
            print(f"[LOBBY] {'Joined' if join_existing else 'Created'} local match. Starting game.")
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.refresh_deck()

    # --- PENDING MATCH QUEUE LOGIC (NEW) ---
    def _create_pending_match(self):
        # Build single-player game (just local user) for pending lobby
        if getattr(self, 'pending_match_active', False):
            return
        player_deck = getattr(self.game.players[0], 'source_path', None) or self.current_deck_path
        specs = [(self.game.players[0].name, player_deck, False)]
        self._rebuild_game_with_specs(specs)
        self.pending_match_active = True
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.sync_pending_controls(True)
        if self.controller.logging_enabled:
            print("[QUEUE] Pending match created. Awaiting players (max 4).")

    def _add_ai_player_pending(self):
        if not getattr(self, 'pending_match_active', False):
            return
        if len(self.game.players) >= 4:
            return
        # Collect existing deck paths
        used_paths = {getattr(p, 'source_path', None) for p in self.game.players}
        decks_dir = os.path.join('data', 'decks')
        deck_files = [os.path.join(decks_dir, f) for f in os.listdir(decks_dir)
                      if f.lower().endswith('.txt')]
        ai_path = None
        for path in sorted(deck_files):
            if path not in used_paths:
                ai_path = path
                break
        if not ai_path:
            ai_path = os.path.join(decks_dir, 'missing_ai_deck.txt')
        # Build new specs: existing players (preserve AI flags) + new AI
        specs = []
        for p in self.game.players:
            is_ai = p.player_id in self.controller.ai_controllers
            specs.append((p.name, getattr(p, 'source_path', None), is_ai))
        ai_name = f"AI{len(specs)}"
        specs.append((ai_name, ai_path, True))
        self._rebuild_game_with_specs(specs)
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.sync_pending_controls(True)
        if self.controller.logging_enabled:
            print(f"[QUEUE] Added AI player '{ai_name}' ({len(self.game.players)}/4).")

    def _start_pending_match(self):
        if not getattr(self, 'pending_match_active', False):
            return
        self.pending_match_active = False
        # Begin actual game
        self.play_stack.setCurrentIndex(1)
        self.controller.enter_match()
        if len(self.game.players) > 1:
            # Prompt for first player roll
            QTimer.singleShot(50, self._prompt_first_player_roll)
        else:
            # Single-player immediate start
            self.controller.set_starter(0)
        if self.controller.logging_enabled:
            print(f"[QUEUE] Match started with {len(self.game.players)} player(s).")
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.sync_pending_controls(False)

    def _cancel_pending_match(self):
        if not getattr(self, 'pending_match_active', False):
            return
        self.pending_match_active = False
        # Revert to default (ensure at least player + AI base for deck view)
        specs = [(self.game.players[0].name,
                  getattr(self.game.players[0], 'source_path', None), False)]
        self._rebuild_game_with_specs(specs)
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.sync_pending_controls(False)
        if self.controller.logging_enabled:
            print("[QUEUE] Pending match canceled.")

    def _rebuild_game_with_specs(self, specs):
        # Helper: rebuild game/controller preserving logging flag
        game, ai_ids = new_game(specs, ai_enabled=True)
        logging_flag = self.controller.logging_enabled
        self.controller = GameController(game, ai_ids, logging_enabled=logging_flag)
        self.game = self.controller.game
        if hasattr(self.play_area, 'set_game'):
            self.play_area.set_game(self.game)
        # Keep logging mirror
        self.logging_enabled = self.controller.logging_enabled
        # Refresh deck & pending list
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.refresh_deck()

    # --- ADDED: debug window toggle (restores F9 functionality) ---
    def _toggle_debug_window(self):
        try:
            from tools.game_debug_tests import GameDebugWindow
        except Exception as ex:
            QMessageBox.information(self, "Debug Window", f"Unavailable: {ex}")
            return
        if getattr(self, '_debug_win', None) and self._debug_win.isVisible():
            self._debug_win.close()
            self._debug_win = None
        else:
            self._debug_win = GameDebugWindow(self.game, getattr(self, 'play_area', None), self)
            self._debug_win.show()

    def _maybe_ai_step(self):
        self.controller.tick(lambda: (
            hasattr(self.play_area, 'refresh_board') and self.play_area.refresh_board()
        ))

    def _advance_phase(self):
        self.controller.advance_phase()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        if e.key() == Qt.Key_Space:
            if hasattr(self.game, 'stack') and self.game.stack.can_resolve():
                self.game.stack.resolve_top(self.game)
            else:
                self._advance_phase()
                self.controller.log_phase()
        elif e.key() == Qt.Key_L:
            self.set_logging_enabled(not self.controller.logging_enabled)
            print(f"[LOG] Phase logging {'enabled' if self.controller.logging_enabled else 'disabled'}")
        elif e.key() == Qt.Key_F9:
            self._toggle_debug_window()
        elif e.key() == Qt.Key_F5:
            self._refresh_deck_tab()
            return
        else:
            super().keyPressEvent(e)

    def _reload_player0(self):
        path = self.current_deck_path
        if not os.path.exists(path):
            QMessageBox.warning(self, "Reload", f"{os.path.basename(path)} not found.")
            return
        try:
            self.controller.reload_player0(new_game, path)
        except Exception as ex:
            QMessageBox.critical(self, "Reload Failed", str(ex))
            return
        self.game = self.controller.game
        if hasattr(self.play_area, 'set_game'):
            self.play_area.set_game(self.game)
        if self.controller.logging_enabled:
            print("[RELOAD] Player 0 deck reloaded.")
        self._refresh_deck_tab()
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.refresh_deck()

    def _prompt_first_player_roll(self):
        if self.controller.first_player_decided or len(self.game.players) < 2:
            return
        box = QMessageBox(self)
        box.setWindowTitle("Determine First Player")
        box.setText("Roll to determine who goes first.")
        roll_btn = box.addButton("Roll", QMessageBox.AcceptRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is roll_btn:
            winner, _rolls = self.controller.perform_first_player_roll()
            wn = self.game.players[winner].name
            choose = QMessageBox(self)
            choose.setWindowTitle("Roll Result")
            choose.setText(f"{wn} wins the roll.\nChoose turn order.")
            go_first = choose.addButton("Go First", QMessageBox.AcceptRole)
            pass_btn = choose.addButton("Pass", QMessageBox.DestructiveRole)
            choose.exec()
            starter = (winner + 1) % len(self.game.players) if choose.clickedButton() is pass_btn else winner
            self.controller.set_starter(starter)

def parse_deck_txt_file(path: str):
    """
    Simple deck parser:
      Optional line: Commander: <name>
      Card lines: '<count> Name' or 'Name'
      Ignores comments (#...) and blank lines.
      If no Commander line, last non-empty name becomes commander.
    """
    entries = []
    commander = None
    last_name = None
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, 'r', encoding='utf-8-sig') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            low = line.lower()
            if low.startswith('commander:'):
                cand = line.split(':', 1)[1].strip()
                if cand:
                    commander = cand
                continue
            m = re.match(r'^(\d+)\s+(.+)$', line)
            if m:
                ct = int(m.group(1))
                name = m.group(2).strip()
                if ct > 0 and name:
                    entries.extend([name] * ct)
                    last_name = name
            else:
                entries.append(line)
                last_name = line
    if commander is None:
        commander = last_name
    return entries, commander

def main():
    global _SDK_ONLINE
    args = parse_args()
    _SDK_ONLINE = bool(getattr(args, 'sdk_online', False) and _HAVE_MTGSDK)
    if getattr(args, 'sdk_online', False) and not _HAVE_MTGSDK:
        print("[SDK] mtg-sdk-python not installed; ignoring --sdk-online (pip install mtgsdk).")
    specs = _deck_specs_from_args(getattr(args, 'deck', None))
    game, ai_ids = new_game(specs if specs else None, ai_enabled=not args.no_ai)
    app = QApplication(sys.argv)
    w = MainWindow(game=game, ai_ids=ai_ids, args=args)
    w.resize(SCREEN_W, SCREEN_H)
    w.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()