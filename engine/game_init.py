import os
import argparse
from config import STARTING_LIFE
from engine.game_state import GameState, PlayerState
from engine.rules_engine import init_rules
from engine.card_db import load_card_db, maybe_bootstrap_sql  # ADDED
from engine.card_fetch import load_deck, prewarm_card_images, set_sdk_online
from engine.deck_specs import build_default_deck_specs, collect_ai_player_ids


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
            cards, commander = load_deck(path, pid)
        except Exception as e:
            print(f"[DECK][{name}] Load error: {e}")
            cards, commander = [], None
        ps = PlayerState(player_id=pid, name=name,
                         life=STARTING_LIFE, library=cards, commander=commander)
        ps.source_path = path
        players.append(ps)

    game = GameState(players=players)
    game.setup()
    init_rules(game)

    # Defer opening hands (push any pre-drawn cards back)
    for pl in game.players:
        if getattr(pl, 'hand', None) and pl.hand:
            pl.library = list(pl.hand) + pl.library
            pl.hand.clear()
    setattr(game, '_opening_hands_deferred', True)

    prewarm_card_images(game.players)
    ai_ids = collect_ai_player_ids(deck_specs, ai_enabled)
    return game, ai_ids


def create_initial_game(args):
    """
    High-level boot helper used by main.py.
    """
    maybe_bootstrap_sql()  # ADDED: enable + migrate JSON -> SQLite if configured
    set_sdk_online(bool(getattr(args, 'sdk_online', False)))
    specs = _deck_specs_from_args(getattr(args, 'deck', None))
    return new_game(specs if specs else None, ai_enabled=not args.no_ai)
