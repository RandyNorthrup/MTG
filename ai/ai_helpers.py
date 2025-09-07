import os

def build_default_deck_specs(player_deck_path: str, ai_deck_path: str, ai_enabled: bool):
    """
    Return initial deck specs (name, path, is_ai).
    """
    if ai_enabled:
        return [("You", player_deck_path, False),
                ("AI", ai_deck_path, True)]
    return [("You", player_deck_path, False)]

def collect_ai_player_ids(deck_specs, ai_enabled: bool):
    """
    Derive AI player id set from deck specs.
    """
    if not ai_enabled:
        return set()
    return {idx for idx, (_, _, is_ai) in enumerate(deck_specs) if is_ai}

def select_ai_deck(existing_paths):
    """
    Pick a deck file not already in existing_paths, fallback to placeholder.
    """
    decks_dir = os.path.join('data', 'decks')
    try:
        files = [os.path.join(decks_dir, f) for f in os.listdir(decks_dir)
                 if f.lower().endswith('.txt')]
    except Exception:
        files = []
    for p in sorted(files):
        if p not in existing_paths:
            return p
    return os.path.join(decks_dir, 'missing_ai_deck.txt')

def add_ai_player_pending(main_window):
    """
    Add an AI player to a pending match (max 4). Rebuilds game via main_window._rebuild_game_with_specs.
    """
    if not getattr(main_window, 'pending_match_active', False):
        return
    game = main_window.game
    if len(game.players) >= 4:
        return
    # Gather existing specs
    specs = []
    for p in game.players:
        is_ai = p.player_id in main_window.controller.ai_controllers
        specs.append((p.name, getattr(p, 'source_path', None), is_ai))
    used = {s[1] for s in specs}
    ai_path = select_ai_deck(used)
    ai_name = f"AI{len(specs)}"
    specs.append((ai_name, ai_path, True))
    main_window._rebuild_game_with_specs(specs)
    if hasattr(main_window, 'lobby_widget'):
        main_window.lobby_widget.sync_pending_controls(True)
    if main_window.controller.logging_enabled:
        print(f"[QUEUE] Added AI player '{ai_name}' ({len(main_window.game.players)}/4).")
