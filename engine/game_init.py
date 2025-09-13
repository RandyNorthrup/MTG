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
        print(f"⚠️  MTG SDK integration not available")
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
    ap = argparse.ArgumentParser(
        description="MTG Commander (Qt) - Magic: The Gathering Commander format game with AI opponents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  %(prog)s                           # Start with default decks
  %(prog)s --sdk-online              # Enable MTG SDK for accurate card data
  %(prog)s --deck "Me=my_deck.txt"   # Use custom deck
  %(prog)s --deck "P1=deck1.txt" --deck "P2=deck2.txt:AI"  # Multi-player

MTG SDK INTEGRATION:
  Use --sdk-online to enable official Magic: The Gathering API integration.
  This provides:
    • Accurate mana costs (e.g., {2}{U}{U} for Counterspell)
    • Proper card text and abilities
    • Correct power/toughness values
    • Enhanced Commander format support
  
  Requires: pip install mtgsdk
  See docs/MTG_SDK_Integration.md for details.
"""
    )
    ap.add_argument('--deck', action='append', metavar='NAME=PATH[:AI]',
                    help='Specify player deck: NAME=PATH or NAME=PATH:AI for AI player')
    ap.add_argument('--no-ai', action='store_true',
                    help='Disable AI opponents')
    ap.add_argument('--no-log', action='store_true',
                    help='Disable phase logging')
    ap.add_argument('--sdk-online', action='store_true',
                    help='Enable MTG SDK integration for enhanced card data (requires mtgsdk package)')
    return ap.parse_args()


def _deck_specs_from_args(arg_list):
    specs = []
    if not arg_list:
        return specs
    for spec in arg_list:
        if '=' not in spec:
            # Ignored malformed --deck specification (debug print removed)
            continue
        name, rest = spec.split('=', 1)
        ai_flag = False
        path = rest
        if ':' in rest:
            path, tag = rest.rsplit(':', 1)
            ai_flag = (tag.upper() == 'AI')
        if not os.path.exists(path):
            # Deck file not found (debug print removed)
            pass
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


# Use enhanced card loading system
from engine.card_fetch import load_deck as _load_deck

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
            cards, commander = [], None
        ps = PlayerState(player_id=pid, name=name,
                         library=cards, commander=commander)  # REMOVED: life=STARTING_LIFE
        ps.source_path = path
        players.append(ps)
    game = GameState(players=players)
    game.setup()
    init_rules(game)  # This now sets starting life

    # Set flag so mulligan system knows to run, but don't clear the already-drawn hands
    # The mulligan system will handle the hands properly
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
