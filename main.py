import sys, os, json, re, argparse
import random  # ADDED for shuffling & random bottom selection
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QLabel, QPushButton, QMessageBox, QListWidget, QListWidgetItem,
    QHBoxLayout, QLineEdit, QStackedWidget, QSplitter,
    QGridLayout, QListView, QSpinBox, QGroupBox, QFrame, QCheckBox,
    QFileDialog)  # ADDED QFileDialog
from PySide6.QtCore import QTimer, Qt, QSize  # ADDED QSize
from PySide6.QtGui import QPixmap, QPainter
from config import *
from engine.game_state import GameState, PlayerState
from engine.game_controller import GameController
from ui.ui_manager import PlayArea              # CHANGED: direct import (no fallback)
from image_cache import ensure_card_image       # CHANGED: direct import (no fallback)
from engine.rules_engine import init_rules      # CHANGED: direct import (no fallback)
from ai.ai_helpers import (build_default_deck_specs, collect_ai_player_ids, add_ai_player_pending)  # ADDED
from ui.home_tab import build_home_tab                     # ADDED
from ui.decks_tab import DecksTabManager                   # ADDED
from ui.play_tab import build_play_stack                   # ADDED
from ui.settings_tab import SettingsTabManager             # ADDED
from ui.phase_ui import update_phase_ui as _phase_update   # ADDED

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
        deck_specs = build_default_deck_specs(auto_player_deck, auto_ai_deck, ai_enabled)  # CHANGED
        print(f"[AUTO-DECK] Player0={os.path.basename(auto_player_deck)}"
              f"{'  AI='+os.path.basename(auto_ai_deck) if ai_enabled and len(deck_specs) > 1 else ''}")
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
    ai_players = collect_ai_player_ids(deck_specs, ai_enabled)  # CHANGED
    return game, ai_players

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
        # REMOVED early phase logging (was: self.controller.log_phase())
        # Backward compat: mirror logging flag (read-only alias expectation)
        self.logging_enabled = self.controller.logging_enabled
        self.tabs = QTabWidget()
        # REMOVE: old deck/state init calls moved into managers
        self._init_tabs()            # now modular
        self.setCentralWidget(self.tabs)
        self._debug_win = None                             # ADDED: debug window handle
        self._settings_tab = None                 # ADDED: settings tab handle
        self._settings_tab_index = None           # ADDED: index cache
        self._selected_settings_image = None      # ADDED: current image path
        _phase_update(self)                   # replaces self._update_phase_ui()
        self._opening_sequence_done = False
        self._match_started = False          # ADDED: guard so enter_match only once

    # Backward compatibility helper (old code maybe toggles self.logging_enabled)
    def set_logging_enabled(self, value: bool):
        self.controller.logging_enabled = bool(value)
        self.logging_enabled = self.controller.logging_enabled

    # ADDED: build tabs (Home, Decks, Play)
    def _init_tabs(self):  # REPLACED
        home = build_home_tab(self)
        self.tabs.addTab(home, "Home")
        self.decks_manager = DecksTabManager(self)
        self.tabs.addTab(self.decks_manager.build_tab(), "Decks")
        # play stack
        self.play_stack, self.lobby_widget = build_play_stack(self)
        play_tab = QWidget()
        pv = QVBoxLayout(play_tab); pv.setContentsMargins(0,0,0,0)
        pv.addWidget(self.play_stack)
        self.tabs.addTab(play_tab, "Play")

    # SETTINGS open wrapper (old body removed)
    def _open_settings_tab(self):  # REPLACED
        if not self.settings_manager:
            self.settings_manager = SettingsTabManager(self)
        self.settings_manager.open()

    # Deck builder refresh wrapper (compat with F5 / old calls)
    def _refresh_deck_tab(self):   # REPLACED
        if hasattr(self, 'decks_manager'):
            self.decks_manager.refresh()

    # Commander selection wrappers (if external code still calls)
    def _set_commander_from_selection(self):  # REPLACED
        self.decks_manager._set_commander_from_selection()

    def _clear_commander(self):  # REPLACED
        self.decks_manager._clear_commander()

    # Phase UI wrapper (keep old name)
    def _update_phase_ui(self):  # REPLACED
        # CHANGED: display "Awaiting Roll" until first player decided
        if not getattr(self.controller, 'first_player_decided', False):
            bar = getattr(self.play_area, 'phase_progress_bar', None)
            if bar is not None:
                try:
                    base_fmt = getattr(bar, '_orig_format', None)
                    if base_fmt is None:
                        base_fmt = bar.format() if hasattr(bar, 'format') else "%v/%m"
                        if not base_fmt:
                            base_fmt = "%v/%m"
                        bar._orig_format = base_fmt
                    bar.setFormat(f"Awaiting Roll - {base_fmt}")
                except Exception:
                    pass
            lbl = getattr(self.play_area, 'phase_label', None)
            if lbl is not None:
                try:
                    base_txt = getattr(lbl, '_orig_text', None)
                    if base_txt is None:
                        base_txt = lbl.text()
                        lbl._orig_text = base_txt
                    lbl.setText(f"Awaiting Roll - {base_txt}")
                except Exception:
                    pass
            return
        # ...existing code (original _phase_update logic still runs afterwards if roll decided)...
        _phase_update(self)

    # Adjusted existing internal calls to use wrapper name still (logic unchanged)
    def _enter_match_from_lobby(self, join_existing: bool):
        if getattr(self, 'pending_match_active', False):
            return
        self.controller.ensure_ai_opponent(new_game)
        if hasattr(self, 'play_stack'):
            self.play_stack.setCurrentIndex(1)
        # DEFER controller.enter_match() until after roll / starter decided
        if len(self.game.players) > 1:
            QTimer.singleShot(50, self._prompt_first_player_roll)
        else:
            self._start_game_without_roll()   # ADDED single-player immediate path
        if self.controller.logging_enabled:
            print(f"[LOBBY] {'Joined' if join_existing else 'Created'} local match (awaiting start).")
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.refresh_deck()
        self._update_phase_ui()

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

    def _add_ai_player_pending(self):  # CHANGED body -> delegate
        add_ai_player_pending(self)

    def _start_pending_match(self):
        if not getattr(self, 'pending_match_active', False):
            return
        self.pending_match_active = False
        self.play_stack.setCurrentIndex(1)
        # DEFER enter_match until after roll
        if len(self.game.players) > 1:
            QTimer.singleShot(50, self._prompt_first_player_roll)
        else:
            self._start_game_without_roll()
        if self.controller.logging_enabled:
            print(f"[QUEUE] Match initialized (awaiting {'roll' if len(self.game.players)>1 else 'phase start'}).")
        if hasattr(self, 'lobby_widget'):
            self.lobby_widget.sync_pending_controls(False)
        self._update_phase_ui()

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
        self._update_phase_ui()     # ADDED

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
        # CHANGED: block ticking until first player decided
        if not getattr(self.controller, 'first_player_decided', False):
            return
        if not self._match_started:
            return  # ADDED: extra safety
        self.controller.tick(lambda: (
            hasattr(self.play_area, 'refresh_board') and self.play_area.refresh_board()
        ))
        self._update_phase_ui()

    def _advance_phase(self):
        # CHANGED: prevent manual phase advance prior to roll
        if not getattr(self.controller, 'first_player_decided', False) or not self._match_started:
            return
        self.controller.advance_phase()
        self._update_phase_ui()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
        # CHANGED: ignore gameplay keys until after roll; allow logging toggle / debug access only after
        if e.key() == Qt.Key_Space and (self.controller.in_game and self.controller.first_player_decided and self._match_started):
            if hasattr(self.game, 'stack') and self.game.stack.can_resolve():
                self.game.stack.resolve_top(self.game)
            else:
                self._advance_phase()
                self.controller.log_phase()
                self._update_phase_ui()
            return
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

    # ADDED helper: start full game after starter known (multi-player)
    def _finalize_start_after_roll(self, starter_index: int):
        if not self._match_started:
            self.controller.enter_match()
            self._match_started = True
        self.controller.set_starter(starter_index)
        self._handle_opening_hands_and_mulligans()
        self.controller.log_phase()          # first phase log now
        self._update_phase_ui()

    # ADDED helper: single-player start (no roll)
    def _start_game_without_roll(self):
        if not self._match_started:
            self.controller.enter_match()
            self._match_started = True
        self.controller.set_starter(0)
        self._handle_opening_hands_and_mulligans()
        self.controller.log_phase()
        self._update_phase_ui()

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
            # MOVED: enter_match & phase log now handled in helper
            self._finalize_start_after_roll(starter)
        # ...existing code...

    def _handle_opening_hands_and_mulligans(self):  # ADDED
        """
        Execute deferred opening draws and London mulligan.
        Multiplayer ( >2 players ) uses free first mulligan (Commander rule 103.5c).
        Only interactive for local player (player 0). Others auto-keep.
        """
        if self._opening_sequence_done:
            return
        if not getattr(self.game, '_opening_hands_deferred', False):
            return
        # Initial draw (7 each) if hands empty
        for pl in self.game.players:
            if not hasattr(pl, 'hand'):
                pl.hand = []
            if not pl.hand:
                draw_n = 7
                for _ in range(draw_n):
                    if pl.library:
                        pl.hand.append(pl.library.pop(0))
            pl.mulligans_taken = 0
        is_multiplayer = (len(self.game.players) > 2)
        human = self.game.players[0] if self.game.players else None
        if human:
            while True:
                hand_names = ", ".join(c.name for c in human.hand)
                box = QMessageBox(self)
                box.setWindowTitle("Opening Hand")
                box.setText(
                    f"Opening Hand ({len(human.hand)} cards):\n{hand_names or '(empty)'}\n\n"
                    "Mulligan? (London mulligan: always draw 7 then put cards on bottom equal to mulligans taken"
                    f"{' (first one free in multiplayer)' if is_multiplayer else ''})."
                )
                mull_btn = box.addButton("Mulligan", QMessageBox.DestructiveRole)
                keep_btn = box.addButton("Keep", QMessageBox.AcceptRole)
                box.exec()
                if box.clickedButton() is keep_btn:
                    break
                # Perform mulligan
                human.mulligans_taken += 1
                # Return current hand to library, shuffle
                returned = human.hand[:]
                human.hand.clear()
                human.library = returned + human.library
                random.shuffle(human.library)
                # Draw 7
                for _ in range(7):
                    if human.library:
                        human.hand.append(human.library.pop(0))
                # London bottom step: put N cards = mulligans_taken minus free one (if multiplayer)
                effective = human.mulligans_taken - (1 if is_multiplayer and human.mulligans_taken == 1 else 0)
                if effective > 0 and len(human.hand) > effective:
                    # Simple heuristic: bottom random 'effective' cards (UI selection omitted for brevity)
                    to_bottom_idx = random.sample(range(len(human.hand)), effective)
                    to_bottom_idx.sort(reverse=True)
                    moving = []
                    for idx in to_bottom_idx:
                        moving.append(human.hand.pop(idx))
                    # Chosen order: put in chosen sequence (could allow re-order UI)
                    human.library.extend(moving)
        # Mark done
        self._opening_sequence_done = True
        # Clear deferred flag
        setattr(self.game, '_opening_hands_deferred', False)

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