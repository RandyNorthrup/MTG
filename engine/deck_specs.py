def build_default_deck_specs(auto_player_deck: str, auto_ai_deck: str, ai_enabled: bool):
    """
    Return default deck specs: human + optional AI.
    """
    return [
        ("You", auto_player_deck, False),
        ("AI", auto_ai_deck, True if ai_enabled else False)
    ]

def collect_ai_player_ids(deck_specs, ai_enabled: bool):
    """
    Collect AI player ids from deck specs honoring global ai toggle.
    """
    return {
        pid for pid, (_n, _p, ai_flag) in enumerate(deck_specs)
        if ai_flag and ai_enabled
    }
