import os
import argparse
from engine.game_state import GameState, PlayerState
from engine.rules_engine import init_rules
from engine.card_db import load_card_db, maybe_bootstrap_sql  # ADDED
from engine.game_ids import generate_game_id, register_game_id  # ADDED

try:
    from engine.card_fetch import set_sdk_online          # CHANGED: safe optional import
except Exception:
    def set_sdk_online(_flag: bool):  # fallback no-op
        return

# Remove this import (causes ImportError):
# from engine.deck_rules import build_default_deck_specs, collect_ai_player_ids

# --- Inline the helpers here (or import from where they are actually defined) ---
def build_default_deck_specs(auto_player_deck: str, auto_ai_deck: str, ai_enabled: bool):
    """
    Return default two-seat specs: local human + optional AI.
    """
    return [
        ("You", auto_player_deck, False),
        ("AI", auto_ai_deck, True if ai_enabled else False)
    ]

def collect_ai_player_ids(deck_specs, ai_enabled: bool):
    """
    Derive AI player id set from deck specs honoring global ai_enabled.
    """
    return {pid for pid, (_, _, ai_flag) in enumerate(deck_specs) if ai_flag and ai_enabled}

def parse_args():
    ap = argparse.ArgumentParser(description="MTG Commander (Qt)")
    ap.add_argument('--deck', action='append', metavar='NAME=PATH[:AI]')
    ap.add_argument('--no-ai', action='store_true')
    ap.add_argument('--no-log', action='store_true')
    ap.add_argument('--sdk-online', action='store_true')
    return ap.parse_args()


def _deck_specs_from_args(arg_list):
    specs = []
    if not arg_list:
        return specs
    for spec in arg_list:
        if '=' not in spec:
            print(f"[ARGS] Ignored malformed --deck '{spec}'")
            continue
        name, rest = spec.split('=', 1)
        ai_flag = False
        path = rest
        if ':' in rest:
            path, tag = rest.rsplit(':', 1)
            ai_flag = (tag.upper() == 'AI')
        if not os.path.exists(path):
            print(f"[ARGS] Deck file not found: {path}")
        specs.append((name, path, ai_flag))
    return specs


def _auto_decks(decks_dir: str):
    files = sorted(
        os.path.join(decks_dir, f) for f in os.listdir(decks_dir)
        if f.lower().endswith('.txt')
    )
    ai = files[0] if files else os.path.join(decks_dir, 'missing_ai_deck.txt')
    player = os.path.join(decks_dir, 'custom_deck.txt')
    if not os.path.exists(player):
        if len(files) > 1:
            player = files[1]
        elif files:
            player = files[0]
    return player, ai


# NEW: unified deck loader (with fallback if card_fetch.load_deck missing)
try:
    from engine.card_fetch import load_deck as _load_deck  # primary path
except Exception:
    def _load_deck(path: str, owner_id: int):
        # Fallback lightweight loader (no SDK enrich)
        by_id, by_name_lower, by_norm, db_path = load_card_db()
        entries, commander_name = _parse_deck_file(path)
        cards, commander = _build_cards_fallback(entries, commander_name, by_id, by_name_lower, by_norm, path, owner_id)
        return cards, commander

    import re

    def _parse_deck_file(path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        entries = []
        commander = None
        last = None
        with open(path, 'r', encoding='utf-8-sig') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                low = line.lower()
                if low.startswith('commander:'):
                    cand = line.split(':', 1)[1].strip()
                    if cand: commander = cand
                    continue
                m = re.match(r'^(\d+)\s+(.+)$', line)
                if m:
                    ct = int(m.group(1)); name = m.group(2).strip()
                    if ct > 0 and name:
                        entries.extend([name]*ct); last = name
                else:
                    entries.append(line); last = line
        if commander is None:
            commander = last
        return entries, commander

    def _build_cards_fallback(entries, commander_name, by_id, by_name_lower, by_norm, deck_path, owner_id):
        from engine.card_engine import Card
        from engine.rules_engine import parse_and_attach
        import random
        def _norm(s): return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
        def _resolve(name):
            if name in by_id: return by_id[name]
            low = name.lower()
            c = by_name_lower.get(low)
            if c: return c
            c = by_norm.get(_norm(name))
            if c: return c
            cand = [v for k,v in by_name_lower.items() if k.startswith(low)]
            if len(cand) == 1: return cand[0]
            raise KeyError(f"Card '{name}' not found (deck={deck_path})")
        commander_src = _resolve(commander_name) if commander_name else None
        lib = []
        for n in entries:
            src = _resolve(n)
            if commander_src and src['id'] == commander_src['id']:
                continue
            card = Card(
                id=src['id'], name=src['name'], types=src['types'],
                mana_cost=src['mana_cost'], power=src.get('power'),
                toughness=src.get('toughness'), text=src.get('text',''),
                is_commander=False, color_identity=src.get('color_identity',[]),
                owner_id=owner_id, controller_id=owner_id
            )
            if 'mana_cost_str' in src:
                setattr(card, 'mana_cost_str', src['mana_cost_str'])
            parse_and_attach(card)
            lib.append(card)
        commander_obj = None
        if commander_src:
            commander_obj = Card(
                id=commander_src['id'], name=commander_src['name'], types=commander_src['types'],
                mana_cost=commander_src['mana_cost'], power=commander_src.get('power'),
                toughness=commander_src.get('toughness'), text=commander_src.get('text',''),
                is_commander=True, color_identity=commander_src.get('color_identity',[]),
                owner_id=owner_id, controller_id=owner_id
            )
            if 'mana_cost_str' in commander_src:
                setattr(commander_obj, 'mana_cost_str', commander_src['mana_cost_str'])
            parse_and_attach(commander_obj)
        return lib, commander_obj

def new_game(deck_specs=None, ai_enabled=True):
    """
    Construct a fresh GameState and return (game, ai_player_ids).
    """
    load_card_db()
    decks_dir = os.path.join('data', 'decks')
    os.makedirs(decks_dir, exist_ok=True)
    player_deck, ai_deck = _auto_decks(decks_dir)
    if not deck_specs:
        deck_specs = build_default_deck_specs(player_deck, ai_deck, ai_enabled)
    players = []
    for pid, (name, path, is_ai) in enumerate(deck_specs):
        try:
            cards, commander = _load_deck(path, pid)   # CHANGED
        except Exception as e:
            print(f"[DECK][{name}] Load error: {e}")
            cards, commander = [], None
        ps = PlayerState(player_id=pid, name=name,
                         library=cards, commander=commander)  # REMOVED: life=STARTING_LIFE
        ps.source_path = path
        players.append(ps)
    game = GameState(players=players)
    game.setup()
    init_rules(game)  # This now sets starting life

    # Defer opening hands (push any pre-drawn cards back)
    for pl in game.players:
        if getattr(pl, 'hand', None) and pl.hand:
            pl.library = list(pl.hand) + pl.library
            pl.hand.clear()
    setattr(game, '_opening_hands_deferred', True)
    ai_ids = collect_ai_player_ids(deck_specs, ai_enabled)
    return game, ai_ids


def create_initial_game(args):
    """
    High-level boot helper used by main.py.
    """
    maybe_bootstrap_sql()  # ADDED: enable + migrate JSON -> SQLite if configured
    set_sdk_online(bool(getattr(args, 'sdk_online', False)))
    specs = _deck_specs_from_args(getattr(args, 'deck', None))
    game, ai_ids = new_game(specs if specs else None, ai_enabled=not args.no_ai)
    gid = generate_game_id()
    register_game_id(gid)
    game.game_id = gid
    return game, ai_ids

# (No logic change – image cache initializes lazily in main window via init_image_cache)
