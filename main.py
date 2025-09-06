import sys, os, json, re, argparse
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                               QVBoxLayout, QLabel, QPushButton, QMessageBox,
                               QListWidget, QListWidgetItem, QHBoxLayout, QLineEdit)
from PySide6.QtCore import QTimer, Qt
# ...existing game/engine imports untouched...
from config import *
from engine.game_state import GameState, PlayerState
from ai.basic_ai import BasicAI
from ui.ui_manager import PlayArea
from image_cache import ensure_card_image  # added
from engine.rules_engine import parse_and_attach, init_rules  # NEW
from engine.combat import attach_combat  # NEW
from engine.continuous import attach_continuous  # NEW

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
    skipped = 0
    for c in raw_cards:
        if not isinstance(c, dict):
            skipped += 1; continue
        if 'id' not in c or 'name' not in c:
            skipped += 1; continue
        cards.append(c)
    by_id = {c['id']:c for c in cards}
    by_name_lower = {c['name'].lower(): c for c in cards}
    by_norm = {_normalize_name(c['name']): c for c in cards}
    _CARD_DB_CACHE = (by_id, by_name_lower, by_norm, path)
    _CARD_NAME_LIST = sorted(by_name_lower.keys())
    if skipped:
        print(f"[CARD_DB] Loaded {len(cards)} cards; skipped {skipped} invalid entries")
    else:
        print(f"[CARD_DB] Loaded {len(cards)} cards")
    return _CARD_DB_CACHE

def get_card_name_list():
    if _CARD_NAME_LIST is None:
        load_card_db()
    # Return human-readable (capitalized) names from by_id to preserve original case
    by_id, by_name_lower, *_ = load_card_db()
    return sorted({c['name'] for c in by_id.values()})

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
    # NEW: attempt unique case-insensitive startswith match (cheap heuristic)
    matches = [v for k, v in by_name_lower.items() if k.startswith(low)]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"Card '{orig}' not found (deck={deck_path} db={db_path})")

def _build_cards(entries, commander_name, *, by_id, by_name_lower, by_norm, db_path_used, deck_path, owner_id):
    from engine.card_engine import Card
    cards = []
    commander_card = _resolve_entry(commander_name, by_id, by_name_lower, by_norm, deck_path, db_path_used) if commander_name else None
    for e in entries:
        c = _resolve_entry(e, by_id, by_name_lower, by_norm, deck_path, db_path_used)
        if commander_card and c['id'] == commander_card['id']:
            continue
        card_obj = Card(
            id=c['id'], name=c['name'], types=c['types'], mana_cost=c['mana_cost'],
            power=c.get('power'), toughness=c.get('toughness'), text=c.get('text',''),
            is_commander=False, color_identity=c.get('color_identity',[]),
            owner_id=owner_id, controller_id=owner_id
        )
        # NEW: store original cost string if available
        if 'mana_cost_str' in c:
            setattr(card_obj, 'mana_cost_str', c['mana_cost_str'])
        # NEW: attach parsed abilities
        parse_and_attach(card_obj)
        cards.append(card_obj)
    commander_obj = None
    if commander_card:
        commander_obj = Card(
            id=commander_card['id'], name=commander_card['name'], types=commander_card['types'],
            mana_cost=commander_card['mana_cost'], power=commander_card.get('power'),
            toughness=commander_card.get('toughness'), text=commander_card.get('text',''),
            is_commander=False, color_identity=commander_card.get('color_identity',[]),
            owner_id=owner_id, controller_id=owner_id
        )
        if 'mana_cost_str' in commander_card:
            setattr(commander_obj, 'mana_cost_str', commander_card['mana_cost_str'])
        parse_and_attach(commander_obj)  # NEW
    return cards, commander_obj

def load_deck(path, by_id, by_name_lower, by_norm, db_path_used, owner_id):
    # Native .txt only
    entries, commander_name = parse_deck_txt_file(path)
    return _build_cards(entries, commander_name,
                        by_id=by_id, by_name_lower=by_name_lower, by_norm=by_norm,
                        db_path_used=db_path_used, deck_path=path, owner_id=owner_id)

def load_banlist(path):
    banned = set()
    if os.path.exists(path):
        with open(path,'r',encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if line and not line.startswith('#'):
                    banned.add(line)
    return banned

def parse_args():
    ap = argparse.ArgumentParser(description="MTG Commander (Qt)")
    ap.add_argument('--deck', action='append', metavar='NAME=PATH[:AI]',
                    help='Add player deck (optional :AI suffix)')
    ap.add_argument('--no-ai', action='store_true')
    ap.add_argument('--no-log', action='store_true')
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
    decks_dir = os.path.join('data','decks')
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
    attach_combat(game)  # NEW: add combat API
    attach_continuous(game)  # NEW continuous layer
    # Prewarm (fire-and-forget) images for current decks (commander + first N)
    for pl in game.players:
        if pl.commander:
            ensure_card_image(pl.commander.id)
        for c in list(pl.library)[:25]:
            ensure_card_image(c.id)
    ai_players = {pid for pid, (_, _, ai_flag) in enumerate(deck_specs) if ai_flag and ai_enabled}
    return game, ai_players

def build_ai_controllers(ai_ids):
    return {pid: BasicAI(pid=pid) for pid in ai_ids}
# --- end added helpers ---

class MainWindow(QMainWindow):
    def __init__(self, game, ai_ids, args):
        super().__init__()
        self.setWindowTitle("MTG Commander (Qt)")
        self.game = game
        self.args = args
        self.ai_controllers = build_ai_controllers(ai_ids)
        self.logging_enabled = not (args and args.no_log)
        self.play_area = PlayArea(game)
        self.tabs = QTabWidget()
        self._init_tabs()
        # Ensure deck editor state initialized after tabs are created
        self._deck_editor_state_init()
        self.setCentralWidget(self.tabs)
        self._phase_timer = QTimer(self)
        self._phase_timer.timeout.connect(self._maybe_ai_step)
        self._phase_timer.start(400)
        self._log_phase()
        self._ai_disabled_after_game = False  # new guard

    def _init_tabs(self):
        # Home Tab
        home = QWidget()
        hl = QVBoxLayout(home)
        hl.addWidget(QLabel("Welcome to MTG Commander (Qt Edition)."))
        hl.addWidget(QLabel("- Build/validate decks, then play against a basic AI."))
        hl.addWidget(QLabel("- Press H in Play tab for help overlay keys."))
        self.tabs.addTab(home, "Home")

        # Decks Tab (embedded editor)
        decks_tab = QWidget()
        dl = QHBoxLayout(decks_tab)

        # Left: deck file list
        self.deck_file_list = QListWidget()
        self.deck_file_list.itemSelectionChanged.connect(self._on_select_deck_file)
        dl.addWidget(self.deck_file_list, 1)

        # Middle: current deck contents
        mid_box = QVBoxLayout()
        mid_box.addWidget(QLabel("Deck (dbl-click remove / right-click commander)"))
        self.deck_list_widget = QListWidget()
        self.deck_list_widget.itemDoubleClicked.connect(self._remove_card_from_deck)
        self.deck_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.deck_list_widget.customContextMenuRequested.connect(self._set_commander_from_deck)
        mid_box.addWidget(self.deck_list_widget, 1)
        self.save_deck_btn = QPushButton("Save Deck (.txt)")
        self.save_deck_btn.clicked.connect(self._save_current_deck)
        mid_box.addWidget(self.save_deck_btn)
        dl.addLayout(mid_box, 1)

        # Right: available cards
        right_box = QVBoxLayout()
        right_box.addWidget(QLabel("Available Cards (dbl-click add / right-click commander)"))
        self.card_search = QLineEdit()
        self.card_search.setPlaceholderText("Search cards...")
        self.card_search.textChanged.connect(self._refresh_available_cards)
        right_box.addWidget(self.card_search)
        self.available_cards_widget = QListWidget()
        self.available_cards_widget.itemDoubleClicked.connect(self._add_card_to_deck)
        self.available_cards_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.available_cards_widget.customContextMenuRequested.connect(self._set_commander_from_available)
        right_box.addWidget(self.available_cards_widget, 1)
        dl.addLayout(right_box, 1)

        self.tabs.addTab(decks_tab, "Decks")

        # Play Tab
        play_tab = QWidget()
        pl = QVBoxLayout(play_tab)
        pl.addWidget(self.play_area)
        self.tabs.addTab(play_tab, "Play")

    # ----- Helpers -----
    def _log_phase(self):
        if self.logging_enabled:
            print(f"[PHASE] Active={self.game.players[self.game.active_player].name} - {self.game.phase}")

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
        # Skip if game over already
        if self._ai_disabled_after_game:
            return
        if self.game.check_game_over():
            self._ai_disabled_after_game = True
            winners = [p for p in self.game.players if p.life > 0]
            msg = 'You Win!' if any(p.player_id != 0 and p.life <= 0 for p in self.game.players) else 'You Lose!'
            if len(self.game.players) > 2:
                msg = "Winners: " + ", ".join(p.name for p in winners) if winners else "All Lost"
            QMessageBox.information(self, "Game Over", msg)
            self._phase_timer.stop()
            return
        # Basic AI only for its controller & relevant phases
        if self.game.active_player in self.ai_controllers and self.game.phase in ('MAIN1','COMBAT_DECLARE'):
            try:
                self.ai_controllers[self.game.active_player].take_turn(self.game, self.play_area)
            except Exception as ex:
                print(f"[AI][ERR] {ex}")
        self.play_area.update()
        # NEW: resolve any queued triggered abilities
        if hasattr(self.game, 'rules_engine'):
            self.game.rules_engine.process_trigger_queue()
        if hasattr(self.game, 'continuous'):  # NEW recompute
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

    def _refresh_deck_list_widget(self):
        self.deck_list_widget.clear()
        # Count
        counts = {}
        for n in self.current_deck_cards:
            counts[n] = counts.get(n, 0) + 1
        for name in sorted(counts):
            label = f"{counts[name]}x {name}"
            if self.current_commander and name == self.current_commander:
                label += " [CMD]"
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, name)
            self.deck_list_widget.addItem(it)

    def _refresh_available_cards(self):
        q = self.card_search.text().lower().strip()
        self.available_cards_widget.clear()
        if not q:
            # show first N for speed
            subset = self._card_db_list[:500]
            for name_lower in subset:
                # convert back to original case via lookup
                # cheap: title-case fallback; accurate: use by_id mapping (already holds names)
                self.available_cards_widget.addItem(QListWidgetItem(next(iter({c['name'] for c in load_card_db()[0].values() if c['name'].lower()==name_lower}), name_lower)))
            return
        # filter
        added = 0
        for c in load_card_db()[0].values():
            nm = c['name']
            if q in nm.lower():
                it = QListWidgetItem(nm)
                it.setData(Qt.UserRole, nm)
                self.available_cards_widget.addItem(it)
                added += 1
                if added >= 500:
                    break

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
        # ...existing code but replace custom_deck.json path usage...
        spec = [(self.game.players[0].name, path, 0 in self.ai_controllers)]
        for p in self.game.players[1:]:
            # keep their original source if still .txt else fallback
            src = getattr(p,'source_path', os.path.join('data','decks','draconic_domination.txt'))
            spec.append((p.name, src, p.player_id in self.ai_controllers))
        try:
            new_state, ai_ids = new_game(spec, ai_enabled=True)
        except Exception as ex:
            QMessageBox.critical(self,"Reload Failed", str(ex)); return
        self.game = new_state
        self.play_area.game = self.game
        self.ai_controllers = build_ai_controllers(ai_ids)
        QMessageBox.information(self,"Reload","Player 0 deck reloaded.")
        self._log_phase()

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
    with open(path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            low = line.lower()
            if low.startswith('sideboard'):
                break
            if low.startswith('commander:'):
                commander = line.split(':',1)[1].strip()
                continue
            m = re.match(r'^(\d+)\s+(.+)$', line)
            if m:
                ct = int(m.group(1))
                name = m.group(2).strip()
                if ct < 1: 
                    continue
                entries.extend([name]*ct)
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
    args = parse_args()
    specs = _deck_specs_from_args(args.deck)
    game, ai_ids = new_game(specs if specs else None, ai_enabled=not args.no_ai)
    app = QApplication(sys.argv)
    w = MainWindow(game, ai_ids, args)
    w.resize(SCREEN_W, SCREEN_H)
    w.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()