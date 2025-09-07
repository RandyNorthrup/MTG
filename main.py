import sys, os, json, re, argparse
import random
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                               QVBoxLayout, QLabel, QPushButton, QMessageBox,
                               QListWidget, QListWidgetItem, QHBoxLayout, QLineEdit,
                               QComboBox, QTextEdit, QCheckBox, QStackedWidget)  # NEW UI widgets
from PySide6.QtCore import QTimer, Qt, QSize  # modified (added QSize)
from PySide6.QtGui import QPixmap, QPainter  # NEW
# ...existing game/engine imports untouched...
from config import *
from engine.game_state import GameState, PlayerState
from ai.basic_ai import BasicAI
from ui.ui_manager import PlayArea
from image_cache import ensure_card_image  # added
from engine.rules_engine import init_rules  # removed parse_and_attach (unused)
from engine.mana import parse_mana_cost  # removed GENERIC_KEY (unused)
from engine.lobby import LobbyServer  # NEW
from engine.turn_manager import TurnManager  # NEW

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

def _sdk_fetch_card(name: str):
    """
    Online fallback: fetch first matching exact-name card via mtgsdk.
    Returns normalized card dict or raises KeyError.
    """
    if not (_SDK_ONLINE and _HAVE_MTGSDK):
        raise KeyError(name)
    # mtgsdk search (exact first; fallback case-insensitive)
    q = MTGSDKCard.where(name=name).all()
    if not q:
        q = MTGSDKCard.where().where(page=1).all()  # minimal safeguard (unlikely to help)
    # pick best exact (case-insensitive)
    pick = None
    for c in q:
        if c.name.lower() == name.lower():
            pick = c
            break
    if not pick and q:
        pick = q[0]
    if not pick:
        raise KeyError(name)
    # Normalize fields expected by existing code
    cid = pick.id or pick.multiverse_id or pick.set + ":" + pick.number
    types = []
    if pick.type:
        # pick.type example: "Creature — Elf Druid"
        main = pick.type.split('—')[0].strip()
        parts = main.split()
        for t in parts:
            types.append(t)
    mana_cost = 0
    mana_cost_str = pick.mana_cost or ""
    # crude parse generic number
    m = re.findall(r'\{(\d+)\}', mana_cost_str)
    if m:
        mana_cost += sum(int(x) for x in m)
    # count colored symbols as 1
    mana_cost += len(re.findall(r'\{[WUBRG]\}', mana_cost_str))
    card_dict = {
        'id': cid,
        'name': pick.name,
        'types': types or ['Card'],
        'mana_cost': mana_cost,
        'mana_cost_str': mana_cost_str,
        'power': None,
        'toughness': None,
        'text': pick.text or "",
        'color_identity': pick.color_identity or []
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
            is_commander=False, color_identity=commander_card.get('color_identity', []),
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
    game = GameState(players=players)
    game.setup()
    init_rules(game)  # already present
    # Prewarm (fire-and-forget) images for current decks (commander + first N)
    for pl in game.players:
        if pl.commander:
            ensure_card_image(pl.commander.id)
        for c in list(pl.library)[:25]:
            ensure_card_image(c.id)
    ai_players = {pid for pid, (_, _, ai_flag) in enumerate(deck_specs) if ai_flag and ai_enabled}
    return game, ai_players

def build_ai_controllers(ai_ids):
    return {pid: BasicAI(pid=pid) for pid in ai_ids}  # simplified

def enhance_ai_controllers(game, ai_controllers):
    """
    Patch BasicAI instances with minimal logic to:
      - MAIN1: play 1 land, cast cheapest spells (creature/enchantment/artifact)
      - COMBAT_DECLARE: declare all untapped creatures as attackers
      - COMBAT_BLOCK: block attackers with all untapped creatures (1:1 first)
    """
    def card_total_cost(card):
        cost_dict = parse_mana_cost(getattr(card, 'mana_cost_str', ''))
        if not cost_dict:
            # fallback numeric generic
            if isinstance(card.mana_cost, int):
                return card.mana_cost
            try:
                return int(card.mana_cost)
            except Exception:
                return 0
        return sum(cost_dict.values())

    def play_land_if_possible(ctrl, player):
        if getattr(ctrl, '_land_played_this_turn', False):
            return
        for card in list(player.hand):
            if 'Land' in card.types:
                # Try engine method first
                if hasattr(game, 'play_land'):
                    try:
                        game.play_land(player.player_id, card)
                        ctrl._land_played_this_turn = True
                        return
                    except Exception:
                        pass
                # Fallback manual move
                try:
                    player.hand.remove(card)
                    # wrap into permanent if engine expects different object
                    if hasattr(game, 'enter_battlefield'):
                        game.enter_battlefield(player.player_id, card)
                    else:
                        player.battlefield.append(type("Perm", (), {"card": card, "tapped": False})())
                    ctrl._land_played_this_turn = True
                    return
                except Exception:
                    continue

    def available_untapped_lands(player):
        lands = []
        for perm in getattr(player, 'battlefield', []):
            c = getattr(perm, 'card', perm)
            if 'Land' in c.types and not getattr(perm, 'tapped', False):
                lands.append(perm)
        return lands

    def tap_for_generic(pid, needed):
        # naive: treat each land as 1 generic
        tapped = 0
        for perm in list(available_untapped_lands(game.players[pid])):
            if tapped >= needed:
                break
            try:
                # game.tap_for_mana may add mana; if produce_mana flag exists we let default
                if hasattr(game, 'tap_for_mana'):
                    game.tap_for_mana(pid, perm)
                else:
                    perm.tapped = True
                tapped += 1
            except Exception:
                perm.tapped = True
                tapped += 1
        return tapped >= needed

    def cast_spells(ctrl, player):
        made_progress = True
        safety = 0
        while made_progress and safety < 20:
            safety += 1
            made_progress = False
            # simple sort by total cost ascending
            castables = [c for c in list(player.hand)
                         if 'Land' not in c.types and any(t in c.types for t in ('Creature', 'Enchantment', 'Artifact'))]
            if not castables:
                break
            castables.sort(key=card_total_cost)
            for card in castables:
                cost = card_total_cost(card)
                if cost == 0:
                    try:
                        game.cast_spell(player.player_id, card)
                        made_progress = True
                        break
                    except Exception:
                        continue
                # ensure enough untapped lands
                if len(available_untapped_lands(player)) >= cost:
                    if tap_for_generic(player.player_id, cost):
                        try:
                            game.cast_spell(player.player_id, card)
                            made_progress = True
                            break
                        except Exception:
                            # ignore failure (maybe needs target) continue loop
                            pass

    def declare_attackers(ctrl, player):
        if not hasattr(game, 'combat'):
            return
        for perm in list(player.battlefield):
            card = getattr(perm, 'card', perm)
            if 'Creature' in card.types and not getattr(perm, 'tapped', False):
                try:
                    game.combat.toggle_attacker(player.player_id, perm)
                except Exception:
                    pass
        game.combat.attackers_committed()
        # Instead of setting game.phase directly, advance once if still in declare step
        if getattr(game, 'phase', '').upper() == 'COMBAT_DECLARE' and hasattr(game, 'next_phase'):
            try:
                game.next_phase()
            except Exception:
                pass

    def assign_blockers(ctrl, player):
        if not hasattr(game, 'combat'):
            return
        atk_map = game.combat.state.attackers
        if not atk_map:
            return
        blockers_used = set()
        for perm in list(player.battlefield):
            if len(blockers_used) >= len(atk_map):
                break
            card = getattr(perm, 'card', perm)
            if 'Creature' in card.types and not getattr(perm, 'tapped', False):
                attacker = atk_map[len(blockers_used)]
                try:
                    game.combat.toggle_blocker(player.player_id, perm, attacker)
                    blockers_used.add(perm)
                except Exception:
                    continue
        # Progress through damage (and possibly end combat) without assigning to phase
        if getattr(game, 'phase', '').upper() == 'COMBAT_BLOCK' and hasattr(game, 'next_phase'):
            try:
                game.next_phase()  # to COMBAT_DAMAGE
            except Exception:
                pass
            try:
                game.combat.assign_and_deal_damage()
            except Exception:
                pass
            # Skip any intermediate combat end step if engine requires multiple advances
            for _ in range(3):
                if getattr(game, 'phase', '').upper() == 'MAIN2':
                    break
                if hasattr(game, 'next_phase'):
                    try:
                        game.next_phase()
                    except Exception:
                        break

    def end_main_if_nothing(ctrl, player):
        # attempt to move to next phase if no stack & nothing else to do
        if getattr(game.stack, 'can_resolve', lambda: False)():
            return
        if hasattr(game, 'next_phase'):
            game.next_phase()

    for pid, ctrl in ai_controllers.items():
        # attach dynamic method
        def take_turn_bound(game_ref=game, controller=ctrl, pid=pid):
            phase = game_ref.phase.upper()
            player = game_ref.players[pid]
            # reset per-turn flags at start
            if phase == 'UNTAP':
                controller._land_played_this_turn = False
                controller._phase_done = set()
            done = getattr(controller, '_phase_done', set())
            if phase == 'MAIN1' and phase not in done:
                play_land_if_possible(controller, player)
                cast_spells(controller, player)
                done.add(phase)
                end_main_if_nothing(controller, player)
            elif phase == 'COMBAT_DECLARE' and game_ref.active_player == pid and phase not in done:
                declare_attackers(controller, player)
                done.add(phase)
            elif phase == 'COMBAT_BLOCK' and game_ref.active_player != pid and phase not in done:
                assign_blockers(controller, player)
                done.add(phase)
            elif phase == 'MAIN2' and phase not in done:
                cast_spells(controller, player)
                done.add(phase)
                end_main_if_nothing(controller, player)
            controller._phase_done = done
        ctrl.take_turn = take_turn_bound

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

class MainWindow(QMainWindow):
    def __init__(self, game, ai_ids, args):
        super().__init__()
        self.setWindowTitle("MTG Commander (Qt)")
        self.game = game
        self.args = args
        self.ai_controllers = build_ai_controllers(ai_ids)
        enhance_ai_controllers(game, self.ai_controllers)
        self.logging_enabled = not (args and args.no_log)
        self.play_area = PlayArea(game)  # direct (fallback removed)
        if hasattr(self.play_area, 'enable_drag_and_drop'):
            self.play_area.enable_drag_and_drop()
        # NEW: ensure TurnManager attached (idempotent)
        if not hasattr(self.game, 'turn_manager'):
            try:
                self.game.turn_manager = TurnManager(self.game)
            except Exception as ex:
                if self.logging_enabled:
                    print(f"[TURNMGR][INIT][ERR] {ex}")
        # --- NEW lobby state attrs (must exist before building lobby UI) ---
        self._active_lobby_id = None
        self._in_game = True              # starts with provided game; lobby builder will flip to False
        self._local_player_name = (self.game.players[0].name if self.game.players else "You")
        # ---------------------------------------------------------------
        self.tabs = QTabWidget()
        self._init_tabs()
        self._deck_editor_state_init()
        self.setCentralWidget(self.tabs)
        self._phase_timer = QTimer(self)
        self._phase_timer.timeout.connect(self._maybe_ai_step)
        self._phase_timer.start(400)
        self._log_phase()
        self._ai_disabled_after_game = False
        # Only run pre-game setup if we are actually in a game view now
        if self._in_game and len(self.game.players) > 1:
            QTimer.singleShot(50, self._initial_pregame_setup)

    # --- pre-game setup (first player + mulligans) ---
    def _initial_pregame_setup(self):
        # Guard if we are currently in lobby (no active game yet) or solo placeholder
        if not getattr(self, '_in_game', False) or len(self.game.players) < 2:
            return
        self._randomize_starting_player()
        self._run_mulligans()
        self._log_phase()

    def _randomize_starting_player(self):
        # Choose starting player randomly (single winner)
        old = self.game.active_player
        self.game.active_player = random.randint(0, len(self.game.players)-1)
        if self.logging_enabled:
            print(f"[START] Random first player: {self.game.players[self.game.active_player].name} (was {self.game.players[old].name})")
        QMessageBox.information(self, "First Player",
                                f"{self.game.players[self.game.active_player].name} will take the first turn.")

    def _run_mulligans(self):
        """
        Simplified London mulligan for player 0 (human).
        AI keeps first hand.
        - Human may mulligan repeatedly while hand size > 0.
        - After choosing keep: bottom (random) N cards where N = mulligans taken.
        """
        pl = self.game.players[0]
        if not hasattr(pl, 'hand'):
            return
        mulligans = 0
        while True:
            hand_sz = len(pl.hand)
            if hand_sz == 0:
                break
            resp = QMessageBox.question(self, "Mulligan",
                                        f"Hand size {hand_sz}. Take a mulligan? (You have taken {mulligans})",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp == QMessageBox.No:
                break
            mulligans += 1
            # Put hand back, shuffle, draw 7
            pl.library.extend(pl.hand)
            pl.hand.clear()
            random.shuffle(pl.library)
            draw_n = min(7, len(pl.library))
            for _ in range(draw_n):
                if pl.library:
                    pl.hand.append(pl.library.pop(0))
            if draw_n == 0:
                break
        if mulligans > 0 and len(pl.hand) > mulligans:
            # Bottom N random (simulate choosing)
            to_bottom = random.sample(pl.hand, mulligans)
            for c in to_bottom:
                pl.hand.remove(c)
                pl.library.append(c)  # append = bottom
        if mulligans and self.logging_enabled:
            print(f"[MULLIGAN] Player {pl.name} final hand={len(pl.hand)} after {mulligans} mulligan(s)")

    # --- LOBBY UI BUILD (NEW) ---
    def _build_play_tab_stack(self):
        # Wrapper stack: index 0 = Lobby, index 1 = Game
        self.play_stack = QStackedWidget()
        # Lobby panel
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
        lob_w = QWidget()
        v = QVBoxLayout(lob_w)
        v.addWidget(QLabel("Lobby - Host or Join"))
        # Deck select
        self.lobby_deck_combo = QComboBox()
        self._refresh_lobby_deck_list()
        v.addWidget(self.lobby_deck_combo)
        # Buttons
        btn_row = QHBoxLayout()
        self.btn_host = QPushButton("Host Game")
        self.btn_join_refresh = QPushButton("Refresh Lobbies")
        self.btn_ready = QPushButton("Ready")
        self.btn_start = QPushButton("Start (Host)")
        self.btn_ready.setEnabled(False)
        self.btn_start.setEnabled(False)
        for b in (self.btn_host, self.btn_join_refresh, self.btn_ready, self.btn_start):
            btn_row.addWidget(b)
        v.addLayout(btn_row)
        # Lobby list
        self.lobby_list = QListWidget()
        v.addWidget(self.lobby_list, 1)
        # Player status
        self.lobby_status = QTextEdit()
        self.lobby_status.setReadOnly(True)
        self.lobby_status.setFixedHeight(110)
        v.addWidget(self.lobby_status)
        # Wire handlers
        self.btn_host.clicked.connect(self._on_host_lobby)
        self.btn_join_refresh.clicked.connect(self._on_refresh_lobbies)
        self.btn_ready.clicked.connect(self._on_toggle_ready)
        self.btn_start.clicked.connect(self._on_start_lobby_game)
        self.lobby_list.itemDoubleClicked.connect(self._on_join_selected_lobby)
        self._on_refresh_lobbies()
        self._lobby_poll_timer = QTimer(self)
        self._lobby_poll_timer.timeout.connect(self._poll_lobby)
        self._lobby_poll_timer.start(1000)

        # Game panel wrapper (existing PlayArea)
        game_wrap = QWidget()
        gvl = QVBoxLayout(game_wrap)
        gvl.setContentsMargins(0,0,0,0)
        gvl.addWidget(self.play_area)

        self.play_stack.addWidget(lob_w)
        self.play_stack.addWidget(game_wrap)
        # Initially show lobby instead of immediate game (flip state)
        self._in_game = False
        self.play_stack.setCurrentIndex(0)
        return self.play_stack

    def _refresh_lobby_deck_list(self):
        self.lobby_deck_combo.clear()
        decks_dir = os.path.join('data','decks')
        if not os.path.isdir(decks_dir):
            return
        for fname in sorted(os.listdir(decks_dir)):
            if fname.lower().endswith('.txt'):
                self.lobby_deck_combo.addItem(fname, os.path.join(decks_dir,fname))

    def _on_refresh_lobbies(self):
        self.lobby_list.clear()
        for lob in LobbyServer.list_lobbies():
            item = QListWidgetItem(f"{lob.lobby_id[:8]}  Players:{len(lob.players)}{' *started' if lob.started else ''}")
            item.setData(Qt.UserRole, lob.lobby_id)
            self.lobby_list.addItem(item)

    def _on_host_lobby(self):
        deck_path = self.lobby_deck_combo.currentData()
        lob = LobbyServer.create_lobby(self._local_player_name, deck_path)
        self._active_lobby_id = lob.lobby_id
        self.btn_ready.setEnabled(True)
        self._update_lobby_status(lob)

    def _on_join_selected_lobby(self, item):
        lobby_id = item.data(Qt.UserRole)
        lob = LobbyServer.join(lobby_id, self._local_player_name)
        if not lob:
            QMessageBox.warning(self,"Join","Unable to join lobby.")
            return
        self._active_lobby_id = lobby_id
        deck_path = self.lobby_deck_combo.currentData()
        if deck_path:
            LobbyServer.set_deck(lobby_id, self._local_player_name, deck_path)
        self.btn_ready.setEnabled(True)
        self._update_lobby_status(lob)

    def _on_toggle_ready(self):
        if not self._active_lobby_id: return
        lob = next((l for l in LobbyServer.list_lobbies() if l.lobby_id==self._active_lobby_id), None)
        if not lob: return
        me = next((p for p in lob.players if p.name==self._local_player_name), None)
        if not me: return
        # set deck each toggle (in case changed)
        deck_path = self.lobby_deck_combo.currentData()
        if deck_path:
            LobbyServer.set_deck(lob.lobby_id, me.name, deck_path)
        LobbyServer.set_ready(lob.lobby_id, me.name, not me.ready)
        lob = next((l for l in LobbyServer.list_lobbies() if l.lobby_id==self._active_lobby_id), None)
        self._update_lobby_status(lob)

    def _on_start_lobby_game(self):
        if not self._active_lobby_id: return
        if not LobbyServer.can_start(self._active_lobby_id):
            QMessageBox.information(self,"Start","All players must have decks & be ready.")
            return
        lob = next((l for l in LobbyServer.list_lobbies() if l.lobby_id==self._active_lobby_id), None)
        if not lob: return
        LobbyServer.mark_started(self._active_lobby_id)
        # Auto-create dummy AI if only one player present
        if len(lob.players) < 2:
            # pick any deck (current selection or fallback first deck)
            decks_dir = os.path.join('data', 'decks')
            deck_choice = self.lobby_deck_combo.currentData()
            if not deck_choice and os.path.isdir(decks_dir):
                for fname in sorted(os.listdir(decks_dir)):
                    if fname.lower().endswith('.txt'):
                        deck_choice = os.path.join(decks_dir, fname)
                        break
            lob.players.append(type("Tmp", (), {
                "name": "GoldfishAI",
                "deck_path": deck_choice,
                "ready": True,
                "is_host": False
            })())
        # Build specs
        specs = []
        for p in lob.players:
            specs.append((p.name, p.deck_path, False if p.name == self._local_player_name else True))
        new_state, ai_ids = new_game(specs, ai_enabled=True)
        self.game = new_state
        self.play_area.set_game(self.game)  # rely on real PlayArea API
        self.ai_controllers = build_ai_controllers(ai_ids)
        enhance_ai_controllers(self.game, self.ai_controllers)
        self._in_game = True
        self.play_stack.setCurrentIndex(1)
        # Only run setup if now multiplayer
        if len(self.game.players) > 1:
            self._initial_pregame_setup()
        self._log_phase()

    def _poll_lobby(self):
        # Safe guards for early construction / no lobby
        if not hasattr(self, '_active_lobby_id') or not hasattr(self, '_in_game'):
            return
        if self._active_lobby_id is None or self._in_game:
            return
        lob = next((l for l in LobbyServer.list_lobbies() if l.lobby_id == self._active_lobby_id), None)
        if not lob:
            self._active_lobby_id = None
            return
        self._update_lobby_status(lob)
        me = next((p for p in lob.players if p.name == self._local_player_name), None)
        self.btn_start.setEnabled(bool(me and me.is_host and LobbyServer.can_start(lob.lobby_id)))

    def _update_lobby_status(self, lob):
        if not lob:
            self.lobby_status.setPlainText("No lobby selected.")
            return
        lines = [f"Lobby {lob.lobby_id}"]
        for p in lob.players:
            lines.append(f"{'[H]' if p.is_host else '   '} {p.name:12} Deck:{os.path.basename(p.deck_path) if p.deck_path else '-'}  {'READY' if p.ready else '...'}")
        if LobbyServer.can_start(lob.lobby_id):
            lines.append("All players ready. Host may start.")
        self.lobby_status.setPlainText("\n".join(lines))

    # --- modify _init_tabs to use lobby stack (NEW insertion) ---
    def _init_tabs(self):
        # Home Tab
        home_bg_path = os.path.join('data', 'images', 'home_bg.png')
        if os.path.exists(home_bg_path):
            home = ScaledBackground(home_bg_path)  # NEW use painter-based scaling
        else:
            home = QWidget()
        home.setObjectName("homeLanding")
        hl = QVBoxLayout(home)
        hl.setContentsMargins(0,0,0,0)
        hl.addStretch(1)
        self.tabs.addTab(home, "Home")

        # Decks Tab REPLACED
        decks_tab = self._build_decks_tab()
        self.tabs.addTab(decks_tab, "Decks")

        # Play Tab
        play_tab = QWidget()
        pl = QVBoxLayout(play_tab)
        # Replace direct PlayArea with lobby/game stacked widget
        pl.addWidget(self._build_play_tab_stack())
        self.tabs.addTab(play_tab, "Play")

    # --- NEW: build modern deck tab ---
    def _build_decks_tab(self):
        # FIX: ensure deck data attrs exist before using them (build tab now accesses them)
        if not hasattr(self, 'current_deck_cards'):
            self.current_deck_path = None
            self.current_deck_cards = []
            self.current_commander = None
            self.deck_dir = os.path.join('data', 'decks')
            os.makedirs(self.deck_dir, exist_ok=True)
            self._card_db_list = get_card_name_list()

        from PySide6.QtWidgets import (
            QHBoxLayout, QVBoxLayout, QGroupBox,
            QCheckBox, QListWidget, QPushButton, QLabel,
            QLineEdit, QListWidgetItem, QSpacerItem, QSizePolicy
        )
        w = QWidget()
        root = QHBoxLayout(w)
        root.setContentsMargins(6,6,6,6)
        root.setSpacing(10)

        # Left Filters
        filt_box = QVBoxLayout()
        # NEW: deck file list (needed by _refresh_deck_file_list)
        from PySide6.QtWidgets import QListWidget, QLabel  # local (already imported symbols OK)
        filt_box.addWidget(QLabel("Deck Files"))
        self.deck_file_list = QListWidget()
        self.deck_file_list.itemSelectionChanged.connect(self._on_select_deck_file)
        filt_box.addWidget(self.deck_file_list, 1)

        # Adjust stretch: search + filters should come after file list
        self.card_search = QLineEdit()
        self.card_search.setPlaceholderText("Search card names (substring)...")
        self.card_search.textChanged.connect(self._refresh_available_cards)
        filt_box.addWidget(self.card_search)

        color_group = QGroupBox("Color Identity (subset)")
        cg_l = QHBoxLayout(color_group)
        self.color_checks = {}
        for sym in ['W','U','B','R','G','C']:
            cb = QCheckBox(sym)
            cb.stateChanged.connect(self._refresh_available_cards)
            self.color_checks[sym] = cb
            cg_l.addWidget(cb)
        filt_box.addWidget(color_group)

        clear_filters_btn = QPushButton("Clear Filters")
        def _clr():
            self.card_search.clear()
            for cb in self.color_checks.values(): cb.setChecked(False)
            self._refresh_available_cards()
        clear_filters_btn.clicked.connect(_clr)
        filt_box.addWidget(clear_filters_btn)
        filt_box.addStretch(1)
        root.addLayout(filt_box, 0)

        # Center Card Grid
        from PySide6.QtWidgets import QListWidget
        self.card_grid = QListWidget()
        self.card_grid.setViewMode(QListWidget.IconMode)
        self.card_grid.setIconSize(QSize(150,210))
        self.card_grid.setResizeMode(QListWidget.Adjust)
        self.card_grid.setMovement(QListWidget.Static)
        self.card_grid.setWordWrap(True)
        self.card_grid.setSpacing(8)
        self.card_grid.itemDoubleClicked.connect(self._add_card_to_deck)
        # Backward compatibility for legacy method names
        self.available_cards_widget = self.card_grid
        root.addWidget(self.card_grid, 2)

        # Right Deck Panel
        deck_panel = QVBoxLayout()
        deck_panel.addWidget(QLabel("Deck (dbl-click remove / right-click set commander)"))
        self.deck_list_widget = QListWidget()
        self.deck_list_widget.itemDoubleClicked.connect(self._remove_card_from_deck)
        self.deck_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.deck_list_widget.customContextMenuRequested.connect(self._set_commander_from_deck)
        deck_panel.addWidget(self.deck_list_widget, 1)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_current_deck)
        clr_btn = QPushButton("Clear Deck")
        def _clr_deck():
            self.current_deck_cards.clear()
            self.current_commander = None
            self._refresh_deck_list_widget()
        clr_btn.clicked.connect(_clr_deck)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(clr_btn)
        deck_panel.addLayout(btn_row)

        self.deck_stats_label = QLabel("")
        self.deck_stats_label.setStyleSheet("color:#ccc; font-size:11px;")
        deck_panel.addWidget(self.deck_stats_label)
        deck_panel.addStretch(1)
        root.addLayout(deck_panel, 1)

        # Initial populate (safe now that attributes exist)
        self._refresh_available_cards()
        self._refresh_deck_file_list()
        self._refresh_deck_list_widget()
        return w

    # --- MODIFIED: refresh now feeds card grid instead of simple list ---
    def _refresh_available_cards(self):
        self._populate_card_grid()

    # --- NEW helper: does card match filters ---
    def _card_matches_filters(self, card):
        # Search
        q = self.card_search.text().strip().lower()
        if q and q not in card['name'].lower():
            return False
        # Colors
        chosen = {sym for sym, cb in self.color_checks.items() if cb.isChecked()}
        if chosen:
            # Treat 'C' as colorless identity requirement
            cid = set(card.get('color_identity') or [])
            if not cid and 'C' not in chosen:
                return False
            # card colors must be subset of selected (ignoring 'C')
            real_chosen = {c for c in chosen if c != 'C'}
            if cid and not cid.issubset(real_chosen):
                return False
            if not cid and 'C' not in chosen:
                return False
        return True

    # --- NEW builder for grid ---
    def _populate_card_grid(self):
        from PySide6.QtWidgets import QListWidgetItem
        self.card_grid.clear()
        try:
            by_id, by_name_lower, by_norm, path = load_card_db()
        except Exception:
            return
        added = 0
        # Iterate by original names (by_id values) to retain casing
        for c in by_id.values():
            if not self._card_matches_filters(c):
                continue
            item = QListWidgetItem(c['name'])
            # Attempt image
            img_path = None
            try:
                maybe = ensure_card_image(c['id'])
                if isinstance(maybe, str) and os.path.exists(maybe):
                    img_path = maybe
                else:
                    # fallback common cache path
                    cp = os.path.join('cache','cards', f"{c['id']}.jpg")
                    if os.path.exists(cp):
                        img_path = cp
            except Exception:
                pass
            if img_path:
                from PySide6.QtGui import QIcon, QPixmap
                pm = QPixmap(img_path)
                if not pm.isNull():
                    item.setIcon(QIcon(pm))
            item.setData(Qt.UserRole, c['name'])
            self.card_grid.addItem(item)
            added += 1
            if added >= 400:  # performance cap
                break

    # --- MODIFIED: deck list refresh adds stats ---
    def _refresh_deck_list_widget(self):
        # Count
        counts = {}
        for n in self.current_deck_cards:
            counts[n] = counts.get(n, 0) + 1
        total = sum(counts.values())
        self.deck_list_widget.clear()
        for name in sorted(counts):
            label = f"{counts[name]}x {name}"
            if self.current_commander and name == self.current_commander:
                label += " [CMD]"
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, name)
            self.deck_list_widget.addItem(it)
        # Basic stats
        self.deck_stats_label.setText(f"Cards: {total}  Commander: {self.current_commander or '-'}")

    # ---------------- NEW: Human turn helpers ----------------
    # (Removed unused manual human action helpers & buttons)
    # _reset_turn_flags_if_needed / _draw_card / _human_* methods removed
    # hotkeys still allow SPACE / A etc.

    def keyPressEvent(self, e):
        # Global hotkeys
        if e.key() == Qt.Key_Escape:
            self.close()
        elif e.key() == Qt.Key_Space:
            if self.game.stack.can_resolve():
                self.game.stack.resolve_top(self.game)
            else:
                self.game.next_phase()
                self._log_phase()
        elif e.key() == Qt.Key_A:
            if self.game.active_player == 0 and self.game.phase == 'COMBAT_DECLARE':
                self.game.declare_attackers(0)
        elif e.key() == Qt.Key_D:
            self._open_deckbuilder()
        elif e.key() == Qt.Key_R:
            self._reload_player0()
        elif e.key() == Qt.Key_L:
            self.logging_enabled = not self.logging_enabled
            print(f"[LOG] Phase logging {'enabled' if self.logging_enabled else 'disabled'}")
        elif e.key() == Qt.Key_H:
            QMessageBox.information(self, "Hotkeys",
                "SPACE: Advance/Resolve\nA: Declare Attackers\nD: Deck Builder\nR: Reload custom deck\nS: (in Play) toggle scoreboard\nL: Toggle phase log\nESC: Quit")
        elif e.key() == Qt.Key_S:
            # Forward scoreboard toggle to play area even if not focused
            if hasattr(self.play_area, 'scoreboard_visible'):
                self.play_area.scoreboard_visible = not self.play_area.scoreboard_visible
                self.play_area.update()

    def _maybe_ai_step(self):
        # Removed call to _reset_turn_flags_if_needed (deleted)
        if hasattr(self.game, 'ensure_progress'):
            self.game.ensure_progress()
        if self._ai_disabled_after_game:
            return
        if len(self.game.players) < 2:
            self.play_area.update()
            return
        # Basic AI only for its controller & relevant phases
        ap = self.game.active_player
        phase = self.game.phase
        if ap in self.ai_controllers and phase in ('MAIN1', 'COMBAT_DECLARE'):
            try:
                self.ai_controllers[ap].take_turn(self.game)
            except Exception as ex:
                print(f"[AI][ERR] {ex}")
        if hasattr(self.game, 'turn_manager'):
            try:
                self.game.turn_manager.tick()
            except Exception as ex:
                if self.logging_enabled:
                    print(f"[TURNMGR][ERR] {ex}")
        self.play_area.update()
        if hasattr(self.play_area, 'refresh_board'):
            self.play_area.refresh_board()  # keep widgets synced to model
        # NEW: resolve any queued triggered abilities
        if hasattr(self.game, 'rules_engine'):
            self.game.rules_engine.process_trigger_queue()
        if hasattr(self.game, 'continuous'):
            self.game.continuous.recompute()

    def _deck_editor_state_init(self):
        self.deck_dir = os.path.join('data','decks')
        os.makedirs(self.deck_dir, exist_ok=True)
        self.current_deck_path = None
        self.current_deck_cards = []
        self.current_commander = None
        # Use cached list (faster than rebuilding)
        self._card_db_list = get_card_name_list()
        self._refresh_deck_file_list()
        self._refresh_available_cards()

    def _refresh_deck_file_list(self):
        sel = self.current_deck_path
        self.deck_file_list.clear()
        for fname in sorted(os.listdir(self.deck_dir)):
            if fname.lower().endswith('.txt'):
                item = QListWidgetItem(fname)
                path = os.path.join(self.deck_dir, fname)
                item.setData(Qt.UserRole, path)
                self.deck_file_list.addItem(item)
                if path == sel:
                    item.setSelected(True)

    def _on_select_deck_file(self):
        items = self.deck_file_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        self._load_deck_file_into_editor(path)

    def _load_deck_file_into_editor(self, path):
        # (Inside MainWindow) replace external parser call
        self.current_deck_path = path
        self.current_deck_cards = []
        self.current_commander = None
        try:
            entries, commander_name = parse_deck_txt_file(path)
            self.current_commander = commander_name
            self.current_deck_cards = list(entries)
        except Exception as e:
            QMessageBox.warning(self, "Deck Load Error", str(e))
            self.current_deck_cards = []
        self._refresh_deck_list_widget()

    # --- Actions ---
    def _add_card_to_deck(self, item):
        name = item.data(Qt.UserRole)
        if not name:
            return
        # Singleton rule except basics (starts with)
        if not name.lower().startswith(('plains','island','swamp','mountain','forest')) and name in self.current_deck_cards:
            # ignore duplicate
            return
        self.current_deck_cards.append(name)
        self._refresh_deck_list_widget()

    def _remove_card_from_deck(self, item):
        name = item.data(Qt.UserRole)
        try:
            self.current_deck_cards.remove(name)
        except ValueError:
            pass
        if self.current_commander == name and name not in self.current_deck_cards:
            self.current_commander = None
        self._refresh_deck_list_widget()

    def _set_commander_from_deck(self, pos):
        it = self.deck_list_widget.itemAt(pos)
        if not it: return
        name = it.data(Qt.UserRole)
        self.current_commander = name
        self._refresh_deck_list_widget()

    def _set_commander_from_available(self, pos):
        it = self.available_cards_widget.itemAt(pos)
        if not it: return
        name = it.data(Qt.UserRole)
        self.current_commander = name
        # Ensure commander present (not duplicated if already)
        if name not in self.current_deck_cards:
            self.current_deck_cards.append(name)
        self._refresh_deck_list_widget()

    def _save_current_deck(self):
        if not self.current_commander:
            QMessageBox.warning(self,"Save","Set a commander (right-click a card).")
            return
        if not self.current_deck_path:
            # new file
            base = "custom_deck.txt"
            self.current_deck_path = os.path.join(self.deck_dir, base)
        save_deck_txt(self.current_deck_path, self.current_commander, self.current_deck_cards)
        self._refresh_deck_file_list()
        QMessageBox.information(self,"Saved", os.path.basename(self.current_deck_path))

    # ----- Removed old dialog open -----
    def _open_deckbuilder(self):
        # Embedded editor notice (shortcut retained for user muscle memory)
        QMessageBox.information(self,"Info","Embedded deck editor active on Decks tab (JSON removed).")

    def _reload_player0(self):
        path = os.path.join('data','decks','custom_deck.txt')
        if not os.path.exists(path):
            QMessageBox.warning(self,"Reload","custom_deck.txt not found. Save one in Decks tab.")
            return
        # ...existing code pre new_game...
        spec = [(self.game.players[0].name, path, 0 in self.ai_controllers)]
        for p in self.game.players[1:]:
            # keep their original source if still .txt else fallback
            src = getattr(p,'source_path', os.path.join('data','decks','draconic_domination.txt'))
            spec.append((p.name, src, p.player_id in self.ai_controllers))
        try:
            self.game, ai_ids = new_game(spec, ai_enabled=True)
        except Exception as ex:
            QMessageBox.critical(self,"Reload Failed", str(ex)); return
        self.play_area.set_game(self.game)
        self.ai_controllers = build_ai_controllers(ai_ids)
        QMessageBox.information(self,"Reload","Player 0 deck reloaded.")
        self._log_phase()

    def _log_phase(self):  # (RE)ADDED safeguard method
        if not getattr(self, 'logging_enabled', False):
            return
        try:
            ap = getattr(self.game, 'active_player', 0)
            pl_name = self.game.players[ap].name if self.game.players else '?'
            print(f"[PHASE] Active={pl_name} - {getattr(self.game, 'phase', '?')}")
        except Exception:
            pass

# -------- Native deck (.txt) parsing (replaces external parser) --------
def parse_deck_txt_file(path: str):
    """
    Supports two styles:
      1. 'Commander: <name>' line anywhere
      2. No Commander line -> last non-empty, non-count line treated as commander
    Card lines:
      'N Card Name' or plain 'Card Name' (count=1)
    Returns (entries_list, commander_name_or_None)
    """
    entries = []
    commander = None
    last_name_candidate = None
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, 'r', encoding='utf-8-sig') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            low = line.lower()
            if low.startswith('sideboard'):
                break
            if low.startswith('commander:'):
                cand = line.split(':',1)[1].strip()
                if cand:
                    commander = cand
                continue
            m = re.match(r'^(\d+)\s+(.+)$', line)
            if m:
                ct = int(m.group(1))
                name = m.group(2).strip()
                if ct <= 0 or not name:
                    continue
                entries.extend([name] * ct)
                last_name_candidate = name
            else:
                entries.append(line)
                last_name_candidate = line
    if commander is None:
        commander = last_name_candidate
    return entries, commander

def save_deck_txt(path: str, commander_name: str, card_names: list[str]):
    counts = {}
    for n in card_names:
        counts[n] = counts.get(n, 0) + 1
    lines = []
    if commander_name:
        lines.append(f"Commander: {commander_name}")
    for name in sorted(counts):
        lines.append(f"{counts[name]} {name}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'w',encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    print(f"[DECK][SAVE] {path}")

def main():
    global _SDK_ONLINE
    args = parse_args()
    _SDK_ONLINE = bool(getattr(args, 'sdk_online', False) and _HAVE_MTGSDK)
    if getattr(args, 'sdk_online', False) and not _HAVE_MTGSDK:
        print("[SDK] mtg-sdk-python not installed; ignoring --sdk-online (pip install mtgsdk).")
    specs = _deck_specs_from_args(getattr(args, 'deck', None))
    game, ai_ids = new_game(specs if specs else None, ai_enabled=not args.no_ai)
    app = QApplication(sys.argv)
    w = MainWindow(game, ai_ids, args)
    w.resize(SCREEN_W, SCREEN_H)
    w.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()