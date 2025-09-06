import sys, os, json, re, argparse, subprocess
from typing import List, Tuple, Optional
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                               QVBoxLayout, QLabel, QPushButton, QMessageBox)
from PySide6.QtCore import QTimer, Qt
# ...existing game/engine imports untouched...
from config import *
from engine.game_state import GameState, PlayerState
from engine.card_engine import Card
from ai.basic_ai import BasicAI
from tools.deck_text_parser import parse_commander_txt
from engine.deck_rules import validate_commander_deck
from deckbuilder.deckbuilder_ui import DeckBuilderDialog
from ui.ui_manager import PlayArea  # newly provided

# --- Added (restored) helper data & functions ---
BASIC_ALIASES = {
    "basic_forest": "Forest","basic_island":"Island","basic_mountain":"Mountain",
    "basic_plains":"Plains","basic_swamp":"Swamp"
}
CUSTOM_ALIASES = {
    "lightning_bolt_plus":"Lightning Bolt","divination":"Divination",
    "coiling_oracle":"Coiling Oracle","tatyova_benthic_druid":"Tatyova, Benthic Druid",
    "aesi_tyrant_of_gyre_strait":"Aesi, Tyrant of Gyre Strait","dragonspeaker_shaman":"Dragonspeaker Shaman",
    "thunderbreak_regent":"Thunderbreak Regent","the_ur_dragon":"The Ur-Dragon"
}
_NORMALIZE_RE = re.compile(r'[^a-z0-9]+')
def _normalize_name(s: str) -> str:
    return _NORMALIZE_RE.sub(' ', s.lower()).strip()

def load_card_db():
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
    if skipped:
        print(f"[CARD_DB] Loaded {len(cards)} cards; skipped {skipped} invalid entries")
    else:
        print(f"[CARD_DB] Loaded {len(cards)} cards")
    return by_id, by_name_lower, by_norm, path

def _resolve_entry(entry: str, by_id, by_name_lower, by_norm, deck_path, db_path):
    entry = BASIC_ALIASES.get(entry, entry)
    entry = CUSTOM_ALIASES.get(entry, entry)
    if entry in by_id: return by_id[entry]
    c = by_name_lower.get(entry.lower())
    if c: return c
    c = by_norm.get(_normalize_name(entry))
    if c: return c
    raise KeyError(f"Card '{entry}' not found (deck={deck_path} db={db_path})")

def _build_cards(entries, commander_name, *, by_id, by_name_lower, by_norm, db_path_used, deck_path, owner_id):
    from engine.card_engine import Card
    cards = []
    commander_card = _resolve_entry(commander_name, by_id, by_name_lower, by_norm, deck_path, db_path_used) if commander_name else None
    for e in entries:
        c = _resolve_entry(e, by_id, by_name_lower, by_norm, deck_path, db_path_used)
        if commander_card and c['id'] == commander_card['id']:
            continue
        cards.append(Card(
            id=c['id'], name=c['name'], types=c['types'], mana_cost=c['mana_cost'],
            power=c.get('power'), toughness=c.get('toughness'), text=c.get('text',''),
            is_commander=False, color_identity=c.get('color_identity',[]),
            owner_id=owner_id, controller_id=owner_id
        ))
    commander_obj = None
    if commander_card:
        commander_obj = Card(
            id=commander_card['id'], name=commander_card['name'], types=commander_card['types'],
            mana_cost=commander_card['mana_cost'], power=commander_card.get('power'),
            toughness=commander_card.get('toughness'), text=commander_card.get('text',''),
            is_commander=False, color_identity=commander_card.get('color_identity',[]),
            owner_id=owner_id, controller_id=owner_id
        )
    return cards, commander_obj

def load_deck(path, by_id, by_name_lower, by_norm, db_path_used, owner_id):
    _, ext = os.path.splitext(path.lower())
    if ext == '.txt':
        from tools.deck_text_parser import parse_commander_txt
        entries, commander_name = parse_commander_txt(path)
        return _build_cards(entries, commander_name,
                            by_id=by_id, by_name_lower=by_name_lower, by_norm=by_norm,
                            db_path_used=db_path_used, deck_path=path, owner_id=owner_id)
    with open(path,'r',encoding='utf-8') as f:
        d = json.load(f)
    commander_entry = d.get('commander')
    return _build_cards(d.get('cards',[]), commander_entry,
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
    if not deck_specs:
        deck_specs = [
            ("You", os.path.join('data','decks','Fynn The Fangbearer.txt'), False),
            ("AI", os.path.join('data','decks','draconic_domination.json'), True if ai_enabled else False)
        ]
    banlist = load_banlist(os.path.join('data','commander_banlist.txt'))
    players = []
    for pid, (name, path, use_ai) in enumerate(deck_specs):
        try:
            cards, commander = load_deck(path, by_id, by_name_lower, by_norm, db_path_used, pid)
        except Exception as e:
            print(f"[DECK][{name}] Load error: {e}")
            cards, commander = [], None
        from engine.game_state import PlayerState
        players.append(PlayerState(player_id=pid, name=name, life=STARTING_LIFE, library=cards, commander=commander))
    from engine.game_state import GameState
    game = GameState(players=players)
    game.setup()
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
        self.setCentralWidget(self.tabs)
        self._phase_timer = QTimer(self)
        self._phase_timer.timeout.connect(self._maybe_ai_step)
        self._phase_timer.start(400)
        self._log_phase()

    def _init_tabs(self):
        # Home Tab
        home = QWidget()
        hl = QVBoxLayout(home)
        hl.addWidget(QLabel("Welcome to MTG Commander (Qt Edition)."))
        hl.addWidget(QLabel("- Build/validate decks, then play against a basic AI."))
        hl.addWidget(QLabel("- Press H in Play tab for help overlay keys."))
        self.tabs.addTab(home, "Home")

        # Decks Tab (button to open deckbuilder dialog)
        decks = QWidget()
        dl = QVBoxLayout(decks)
        btn = QPushButton("Open Deck Builder Dialog")
        btn.clicked.connect(self._open_deckbuilder)
        dl.addWidget(QLabel("Commander Deck Tools"))
        dl.addWidget(btn)
        self.tabs.addTab(decks, "Decks")

        # Play Tab
        play_tab = QWidget()
        pl = QVBoxLayout(play_tab)
        pl.addWidget(self.play_area)
        self.tabs.addTab(play_tab, "Play")

    # ----- Helpers -----
    def _open_deckbuilder(self):
        card_db_path = os.path.join('data','cards','card_db_full.json')
        if not os.path.exists(card_db_path):
            card_db_path = os.path.join('data','cards','card_db.json')
        dlg = DeckBuilderDialog(card_db_path, os.path.join('data','commander_banlist.txt'), self)
        dlg.resize(1000,600)
        dlg.exec()

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
        # Basic AI triggers during MAIN1 or COMBAT_DECLARE after phase advancement
        if self.game.active_player in self.ai_controllers and self.game.phase in ('MAIN1','COMBAT_DECLARE'):
            self.ai_controllers[self.game.active_player].take_turn(self.game, self.play_area)
        self.play_area.update()
        if self.game.check_game_over():
            winners = [p for p in self.game.players if p.life > 0]
            if len(self.game.players) == 2:
                msg = 'You Win!' if any(p.player_id != 0 and p.life <= 0 for p in self.game.players) else 'You Lose!'
            else:
                msg = "Winners: " + ", ".join(p.name for p in winners) if winners else "All Lost"
            QMessageBox.information(self, "Game Over", msg)
            self._phase_timer.stop()

    def _reload_player0(self):
        path = os.path.join('data','decks','custom_deck.json')
        if not os.path.exists(path):
            QMessageBox.warning(self,"Reload","custom_deck.json not found.")
            return
        spec = [(self.game.players[0].name, path, 0 in self.ai_controllers)]
        for p in self.game.players[1:]:
            spec.append((p.name,
                         getattr(p,'source_path', os.path.join('data','decks','draconic_domination.json')),
                         p.player_id in self.ai_controllers))
        try:
            new_state, ai_ids = new_game(spec, ai_enabled=True)
        except Exception as ex:
            QMessageBox.critical(self,"Reload Failed", str(ex))
            return
        self.game = new_state
        self.play_area.game = self.game
        self.ai_controllers = build_ai_controllers(ai_ids)
        QMessageBox.information(self,"Reload","Player 0 deck reloaded.")
        self._log_phase()

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