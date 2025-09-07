from PySide6.QtCore import QTimer

# --- ADDED canonical phase utilities ---
_PHASE_ORDER = [
    "untap", "upkeep", "draw",
    "precombat_main",
    "begin_combat", "declare_attackers", "declare_blockers", "combat_damage", "end_combat",
    "postcombat_main",
    "end", "cleanup"
]

def _canon_phase(name: str) -> str:
    """Return canonical lowercase identifier for a phase/step."""
    if not name:
        return ""
    n = name.lower().strip().replace(" ", "_")
    return n

_DISPLAY_NAMES = {
    "precombat_main": "Main (Precombat)",
    "postcombat_main": "Main (Postcombat)",
    "begin_combat": "Begin Combat",
    "declare_attackers": "Declare Attackers",
    "declare_blockers": "Declare Blockers",
    "combat_damage": "Combat Damage",
    "end_combat": "End Combat",
}

# Export (optional convenience)
CANON_PHASES = tuple(_PHASE_ORDER)

__all__ = [
    "register_phase_controller",
    "install_phase_log_adapter",
    "install_phase_log_deduper",
    "update_phase_ui",
]

# ================= UI Banner =================
def update_phase_ui(host):
    try:
        game = getattr(host, "game", None)
        if not game:
            return
        raw = getattr(game, "phase", "Beginning")
        hl = _canon_phase(raw)
        disp = _DISPLAY_NAMES.get(hl, hl)
        ap_i = getattr(game, "active_player", 0)
        ap_name = "Player"
        if hasattr(game, "players") and 0 <= ap_i < len(game.players):
            ap_name = getattr(game.players[ap_i], "name", ap_name)
        pa = getattr(host, "play_area", None)
        if pa is None and hasattr(host, "api"):
            gw = getattr(host.api, "_game_window", None)
            if gw:
                pa = getattr(gw, "play_area", None)
        if pa and hasattr(pa, "update_phase_banner"):
            pa.update_phase_banner(disp, ap_name)
    except Exception:
        pass
