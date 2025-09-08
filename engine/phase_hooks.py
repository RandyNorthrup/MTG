from PySide6.QtCore import QTimer
import time

# Canonical phase order and display names
_PHASE_ORDER = [
    "untap", "upkeep", "draw",
    "precombat_main",
    "begin_combat", "declare_attackers", "declare_blockers", "combat_damage", "end_combat",
    "postcombat_main",
    "end", "cleanup"
]

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

# Official Magic: The Gathering turn structure (phases and steps)
PHASE_SEQUENCE = [
    "beginning",
    "precombat_main",
    "combat",
    "postcombat_main",
    "ending"
]

PHASE_STEPS = {
    "beginning": ["untap", "upkeep", "draw"],
    "precombat_main": ["main1"],
    "combat": [
        "begin_combat",
        "declare_attackers",
        "declare_blockers",
        "combat_damage",
        "end_of_combat"
    ],
    "postcombat_main": ["main2"],
    "ending": ["end_step", "cleanup"]
}

FLAT_TURN_ORDER = [
    (phase, step) for phase in PHASE_SEQUENCE for step in PHASE_STEPS[phase]
]

def _canon_phase(name: str) -> str:
    if not name:
        return ""
    return name.lower().strip().replace(" ", "_")

def first_step_of_phase(phase: str) -> str:
    return PHASE_STEPS[phase][0]

def is_last_step_in_phase(phase: str, step: str) -> bool:
    steps = PHASE_STEPS[phase]
    return steps and steps[-1] == step

def next_phase_after(phase: str):
    try:
        idx = PHASE_SEQUENCE.index(phase)
    except ValueError:
        return None
    if idx + 1 < len(PHASE_SEQUENCE):
        return PHASE_SEQUENCE[idx + 1]
    return None

def next_flat_step(phase: str, step: str):
    try:
        phase_steps = PHASE_STEPS[phase]
        idx = phase_steps.index(step)
    except Exception:
        return None
    if idx + 1 < len(phase_steps):
        return phase, phase_steps[idx + 1]
    nxt = next_phase_after(phase)
    if nxt is None:
        return None
    return nxt, first_step_of_phase(nxt)

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

CANON_PHASES = tuple(_PHASE_ORDER)

def update_phase_ui(host):
    """
    Update visible phase widgets with active player prefix.
    """
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

# --- Merge from import time.py ---

class OpeningTurnSkipper:
    """
    Skip UNTAP & UPKEEP on the first turn (player turn_number 1).
    Waits until those phases occur; then fast-forwards past them once.
    """
    def __init__(self, controller):
        self.controller = controller
        self._done = False
        self._busy = False

    def tick(self):
        if self._done or self._busy:
            return False
        ctrl = self.controller
        try:
            tn = getattr(ctrl, 'turn_number', 0) or 0
            phase = getattr(ctrl, 'phase', None)

            # Not yet at first turn phases—keep waiting.
            if tn < 1 or phase is None:
                return False

            # Already beyond what we want to skip.
            if tn > 1 or phase not in ('UNTAP', 'UPKEEP'):
                self._done = True
                return False

            adv = (getattr(ctrl, 'advance_phase', None) or
                   getattr(ctrl, 'next_phase', None))
            if not callable(adv):
                return False

            self._busy = True
            changed = False
            guard = 0
            # Advance until we leave both UNTAP & UPKEEP (reach DRAW or later)
            while getattr(ctrl, 'phase', None) in ('UNTAP', 'UPKEEP') and guard < 6:
                adv()
                changed = True
                guard += 1
            self._done = True
            return changed
        except Exception:
            self._done = True
            return False
        finally:
            self._busy = False

class PhaseAdvanceManager:
    """
    Fallback auto phase advancement for when phases stall.
    Uses conservative heuristics: advances only if
      - first player decided
      - controller not waiting for user input (common attr names checked)
      - stack (if present) empty
      - minimal interval elapsed
    """
    def __init__(self, controller, min_interval=0.5):
        self.controller = controller
        self.min_interval = float(min_interval)
        self._last_phase_name = getattr(controller, 'phase', None)
        self._last_phase_change_ts = time.time()
        self._last_tick_ts = 0.0

    def _can_advance(self):
        c = self.controller
        # Must have decided first player
        if not getattr(c, 'first_player_decided', False):
            return False
        # Common "waiting" flags
        if getattr(c, 'awaiting_player_action', False):
            return False
        if getattr(c, 'waiting_for_input', False):
            return False
        # Stack not empty?
        st = getattr(c, 'stack', None)
        if st and len(st) > 0:
            return False
        # Rate limit
        if (time.time() - self._last_tick_ts) < self.min_interval:
            return False
        return True

    def tick(self):
        """
        Returns True if phase advanced or phase changed externally.
        """
        self._last_tick_ts = time.time()
        c = self.controller
        current = getattr(c, 'phase', None)
        if current != self._last_phase_name:
            self._last_phase_name = current
            self._last_phase_change_ts = time.time()
            return True

        # If phase unchanged for a while, attempt progression.
        idle_for = time.time() - self._last_phase_change_ts
        if idle_for < (self.min_interval * 2):
            return False

        if not self._can_advance():
            return False

        adv = (getattr(c, 'advance_phase', None) or
               getattr(c, 'next_phase', None))
        if not callable(adv):
            return False

        try:
            adv()
            new_phase = getattr(c, 'phase', None)
            if new_phase != self._last_phase_name:
                self._last_phase_name = new_phase
                self._last_phase_change_ts = time.time()
                return True
        except Exception:
            return False
        return False

def update_phase_ui(main_win):
    """
    Update visible phase widgets with active player prefix.
    """
    try:
        ap = getattr(main_win.game, 'active_player', 0)
        players = getattr(main_win.game, 'players', [])
        pname = players[ap].name if players and 0 <= ap < len(players) else "?"
