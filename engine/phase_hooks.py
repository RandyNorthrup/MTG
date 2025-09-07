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
    if not name:
        return ""
    n = name.lower().strip().replace(" ", "_")
    return n

# Add/restore _DISPLAY_NAMES for phase banner display
_DISPLAY_NAMES = {
    "untap": "Untap",
    "upkeep": "Upkeep",
    "draw": "Draw",
    "precombat_main": "Main (Precombat)",
    "begin_combat": "Begin Combat",
    "declare_attackers": "Declare Attackers",
    "declare_blockers": "Declare Blockers",
    "combat_damage": "Combat Damage",
    "end_combat": "End Combat",
    "postcombat_main": "Main (Postcombat)",
    "end": "End",
    "cleanup": "Cleanup",
}

# --- Add/restore PHASE_STEPS for proper substep logic ---
PHASE_STEPS = {
    "untap": ["untap"],
    "upkeep": ["upkeep"],
    "draw": ["draw"],
    "precombat_main": ["precombat_main"],
    "begin_combat": ["begin_combat"],
    "declare_attackers": ["declare_attackers"],
    "declare_blockers": ["declare_blockers"],
    "combat_damage": ["combat_damage"],
    "end_combat": ["end_combat"],
    "postcombat_main": ["postcombat_main"],
    "end": ["end"],
    "cleanup": ["cleanup"],
}

def first_step_of_phase(phase):
    canon = _canon_phase(phase)
    steps = PHASE_STEPS.get(canon)
    if steps:
        return steps[0]
    return canon

def next_flat_step(phase, step):
    canon = _canon_phase(phase)
    steps = PHASE_STEPS.get(canon)
    if not steps:
        return None
    idx = steps.index(step) if step in steps else -1
    if idx + 1 < len(steps):
        return (canon, steps[idx + 1])
    # Move to next phase
    try:
        phase_idx = _PHASE_ORDER.index(canon)
        next_phase = _PHASE_ORDER[(phase_idx + 1) % len(_PHASE_ORDER)]
        return (next_phase, first_step_of_phase(next_phase))
    except Exception:
        return None

def advance_phase(controller):
    """
    Advance to the next phase in the canonical phase order.
    """
    if not hasattr(controller, "current_phase"):
        return
    try:
        idx = _PHASE_ORDER.index(_canon_phase(controller.current_phase))
    except Exception:
        idx = 0
    next_idx = (idx + 1) % len(_PHASE_ORDER)
    controller.current_phase = _PHASE_ORDER[next_idx]
    if hasattr(controller, "current_step"):
        controller.current_step = first_step_of_phase(controller.current_phase)
    update_phase_ui(controller)
    log_phase(controller)

def advance_step(controller):
    """
    Advance to the next step (or phase if no steps).
    """
    if hasattr(controller, "current_phase") and hasattr(controller, "current_step"):
        nxt = next_flat_step(controller.current_phase, controller.current_step)
        if nxt is None:
            advance_phase(controller)
        else:
            controller.current_phase, controller.current_step = nxt
        update_phase_ui(controller)
        log_phase(controller)
    else:
        advance_phase(controller)

def set_phase(controller, phase_name):
    """
    Set the controller's phase directly to the given phase name.
    """
    canon = _canon_phase(phase_name)
    if canon in _PHASE_ORDER:
        controller.current_phase = canon
        if hasattr(controller, "current_step"):
            controller.current_step = first_step_of_phase(canon)
        update_phase_ui(controller)
        log_phase(controller)

# Export (optional convenience)
CANON_PHASES = tuple(_PHASE_ORDER)

__all__ = [
    "register_phase_controller",
    "install_phase_log_adapter",
    "install_phase_log_deduper",
    "update_phase_ui",
    "advance_phase",
    "advance_step",
    "set_phase",
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

"""
DEPRECATED: Legacy phase hook system replaced by strict turn_structure + GameController.advance_step().
All functions are inert no-ops retained for backward compatibility only.
"""

def register_phase_hook(*_, **__): pass
def clear_phase_hooks(): pass
def run_phase_hooks(*_, **__): pass
# Export these for use in debug window and UI
__all__ += [
    "advance_phase",
    "advance_step",
    "set_phase",
]

def log_phase(controller):
    """
    Log the current phase and active player, only if changed since last log.
    """
    if not getattr(controller, "logging_enabled", False):
        return
    try:
        game = getattr(controller, "game", None)
        if not game:
            return
        ap = getattr(game, "active_player", None)
        nm = game.players[ap].name if game and game.players and ap is not None else "?"
        phase = getattr(controller, "current_phase", "unknown")
        step = getattr(controller, "current_step", "unknown")
        log_msg = f"Phase: {phase}, Step: {step}, Active Player: {nm}"
        print(log_msg)  # Replace with actual logging mechanism
    except Exception:
        pass
