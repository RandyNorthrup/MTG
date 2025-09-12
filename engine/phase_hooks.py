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

# Ensure all phases used by the engine are present here:
PHASE_STEPS = {
    "beginning": ["untap", "upkeep", "draw"],
    "untap": ["untap"],
    "upkeep": ["upkeep"],
    "draw": ["draw"],
    "precombat_main": ["main1"],
    "combat": [
        "begin_combat",
        "declare_attackers",
        "declare_blockers",
        "combat_damage",
        "end_combat"
    ],
    "begin_combat": ["begin_combat"],
    "declare_attackers": ["declare_attackers"],
    "declare_blockers": ["declare_blockers"],
    "combat_damage": ["combat_damage"],
    "end_combat": ["end_combat"],
    "postcombat_main": ["main2"],
    "ending": ["end", "cleanup"],
    "end": ["end"],
    "cleanup": ["cleanup"],
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
    
    # Execute phase-specific actions
    _execute_phase_actions(controller, controller.current_phase)
    
    # Refresh UI after phase change
    _refresh_ui_after_phase_change(controller)
    
    update_phase_ui(controller)
    log_phase(controller)

def advance_step(controller):
    """
    Advance to the next step (or phase if no steps).
    """
    old_phase = getattr(controller, "current_phase", "none")
    old_step = getattr(controller, "current_step", "none")
    
    if hasattr(controller, "current_phase") and hasattr(controller, "current_step"):
        nxt = next_flat_step(controller.current_phase, controller.current_step)
        if nxt is None:
            advance_phase(controller)
        else:
            controller.current_phase, controller.current_step = nxt
            # Execute step-specific actions
            _execute_phase_actions(controller, controller.current_step)
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
        
        # Execute phase-specific actions
        _execute_phase_actions(controller, canon)
        
        update_phase_ui(controller)
        log_phase(controller)

CANON_PHASES = tuple(_PHASE_ORDER)

def _refresh_ui_after_phase_change(controller):
    """
    Refresh the UI after a phase changes to update phase display.
    """
    try:
        # Get the API reference that was stored during controller creation
        api = getattr(controller, '_api_ref', None)
        
        if api and hasattr(api, 'board_window') and api.board_window:
            # Update phase display in board window
            if hasattr(api.board_window, 'refresh_phase'):
                api.board_window.refresh_phase()
                
            # Also trigger general UI update
            if hasattr(api, '_phase_ui'):
                api._phase_ui()
                
    except Exception as e:
        pass

def _refresh_ui_after_draw(controller):
    """
    Refresh the UI after a card is drawn to show the updated hand and library counts.
    """
    try:
        # Get the API reference that was stored during controller creation
        api = getattr(controller, '_api_ref', None)
        
        if api:
            # Force full refresh of all UI elements
            if hasattr(api, 'board_window') and api.board_window:
                # Refresh the board window's play area to show updated hand
                if hasattr(api.board_window, 'play_area'):
                    # Ensure board window play area has the latest game reference
                    if hasattr(api.board_window.play_area, 'set_game'):
                        api.board_window.play_area.set_game(api.game)
                    # Force a complete refresh of the play area
                    api.board_window.play_area.update()
                    # Also trigger playables update
                    if hasattr(api.board_window.play_area, '_update_playables'):
                        api.board_window.play_area._update_playables()
                    # Force refresh of the entire board display
                    if hasattr(api.board_window.play_area, 'refresh_board'):
                        api.board_window.play_area.refresh_board()
                        
                # Update phase display in board window
                if hasattr(api.board_window, 'refresh_phase'):
                    api.board_window.refresh_phase()
                    
                # Force a complete window update
                api.board_window.update()
                    
            # Main window no longer has a play area - only dedicated board window is used
                    
            # Also trigger phase UI update
            if hasattr(api, '_phase_ui'):
                api._phase_ui()
                
    except Exception as e:
        pass

def _execute_phase_actions(controller, phase_name):
    """
    Execute the game logic associated with entering a specific phase/step.
    """
    if not hasattr(controller, "game") or not controller.game:
        return
    
    game = controller.game
    active_player_id = getattr(game, "active_player", 0)
    
    try:
        # Map phase/step names to actions
        phase_canon = _canon_phase(phase_name)
        
        if phase_canon == "untap":
            # Untap all permanents for active player
            if hasattr(game, "players") and game.players:
                active_player = game.players[active_player_id]
                for perm in active_player.battlefield:
                    if hasattr(perm, "tapped"):
                        perm.tapped = False
                # Reset mana
                if hasattr(active_player, "reset_mana"):
                    active_player.reset_mana()
                    
        elif phase_canon == "draw":
            # Active player draws a card (skip on first turn for starting player)
            if hasattr(game, "players") and game.players:
                active_player = game.players[active_player_id]
                # Check if this is the first turn and starting player
                turn_num = getattr(game, "turn", 1)
                is_first_turn = turn_num == 1
                is_starting_player = active_player_id == getattr(controller, "skip_first_draw_player", None)
                
                # Skip first draw only for starting player on turn 1 (MTG rule)
                should_skip_draw = is_first_turn and is_starting_player and not getattr(controller, "skip_first_draw_used", False)
                
                # Draw step logic
                
                if should_skip_draw:
                    controller.skip_first_draw_used = True
                else:
                    # Draw the card
                    if hasattr(active_player, "draw") and hasattr(active_player, "library") and active_player.library:
                        hand_before = len(active_player.hand)
                        library_before = len(active_player.library)
                        active_player.draw(1)
                        
                        # Card draw completed successfully
                        
                        # Force immediate and complete UI refresh after draw
                        try:
                            api = getattr(controller, '_api_ref', None)
                            if api:
                                # Update all UI components immediately
                                if hasattr(api, 'board_window') and api.board_window:
                                    # Refresh phase display
                                    if hasattr(api.board_window, 'refresh_phase'):
                                        api.board_window.refresh_phase()
                                    # Refresh play area completely
                                    if hasattr(api.board_window, 'play_area'):
                                        play_area = api.board_window.play_area
                                        # Set the updated game state
                                        play_area.game = controller.game
                                        # Force complete repaint
                                        play_area.force_refresh()
                                        # Process all pending UI events
                                        from PySide6.QtWidgets import QApplication
                                        QApplication.processEvents()
                        except Exception as e:
                            print(f"[UI REFRESH ERROR] {e}")
                        
                        _refresh_ui_after_draw(controller)
                        
                # Automatically advance to main phase after draw step (no pause)
                from PySide6.QtCore import QTimer
                def auto_advance_to_main():
                    try:
                        # Advance to precombat main phase
                        controller.current_phase = "precombat_main"
                        controller.current_step = "main1"
                        _execute_phase_actions(controller, "precombat_main")
                        update_phase_ui(controller)
                        log_phase(controller)
                    except Exception as e:
                        pass
                
                # Use a small delay to ensure UI updates are processed first
                QTimer.singleShot(100, auto_advance_to_main)
                    
        elif phase_canon == "cleanup":
            # Cleanup step actions
            if hasattr(game, "players") and game.players:
                for player in game.players:
                    # Reset damage on permanents
                    for perm in player.battlefield:
                        if hasattr(perm, "damage"):
                            perm.damage = 0
                    # Reset mana pools
                    if hasattr(player, "reset_mana"):
                        player.reset_mana()
                        
    except Exception as e:
        pass

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
        phase = getattr(controller, "current_phase", "unknown")
        step = getattr(controller, "current_step", "unknown")
        log_msg = f"Phase: {phase}, Step: {step}, Active Player: {nm}"
        # Phase log message (debug print removed)
    except Exception:
        pass

# Remove duplicate log_phase and __all__ mutation, and define __all__ at the top.
__all__ = [
    "advance_phase",
    "advance_step",
    "set_phase",
    "update_phase_ui",
    "log_phase",
    "OpeningTurnSkipper",
    "PhaseAdvanceManager",
    "CANON_PHASES",
]

"""
DEPRECATED: Legacy phase hook system replaced by strict turn_structure + GameController.advance_step().
All functions are inert no-ops retained for backward compatibility only.
"""

def register_phase_hook(*_, **__): pass
def clear_phase_hooks(): pass
def run_phase_hooks(*_, **__): pass

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
        # Optionally update UI banner if present
        pa = getattr(main_win, "play_area", None)
        if pa and hasattr(pa, "update_phase_banner"):
            phase = getattr(main_win.game, "phase", "Beginning")
            hl = _canon_phase(phase)
            disp = _DISPLAY_NAMES.get(hl, hl)
            pa.update_phase_banner(disp, pname)
    except Exception:
        pass
    try:
        ap = getattr(main_win.game, 'active_player', 0)
        players = getattr(main_win.game, 'players', [])
        pname = players[ap].name if players and 0 <= ap < len(players) else "?"
        # Optionally update UI banner if present
        pa = getattr(main_win, "play_area", None)
        if pa and hasattr(pa, "update_phase_banner"):
            phase = getattr(main_win.game, "phase", "Beginning")
            hl = _canon_phase(phase)
            disp = _DISPLAY_NAMES.get(hl, hl)
            pa.update_phase_banner(disp, pname)
    except Exception:
        pass
        disp = _DISPLAY_NAMES.get(hl, hl)
        pa.update_phase_banner(disp, pname)
    except Exception:
        pass

def init_turn_phase_state(controller):
    """
    Set up the phase and step for a new turn, using board/player state.
    Only the very first turn for the starting player begins at precombat_main.
    All subsequent turns (and all other players) begin at untap.
    """
    # Determine turn number and active player
    turn_no = getattr(controller, "_turn_no", 1)
    active_player = getattr(controller.game, "active_player", 0)
    is_first_turn = (turn_no == 1)
    is_first_player = (active_player == 0)
    if is_first_turn and is_first_player:
        phase = "precombat_main"
        step = first_step_of_phase(phase)
    else:
        phase = "untap"
        step = first_step_of_phase("beginning")
    # Store canonical phase/step on controller for legacy code, but always use these helpers
    controller._phase_state = {"phase": phase, "step": step}
    # Optionally, update game object for UI
    controller.current_phase = phase
    controller.current_step = step
    controller.visited_phases = set()

def get_current_phase(controller):
    # Always prefer canonical state
    if hasattr(controller, "_phase_state"):
        return controller._phase_state.get("phase")
    return getattr(controller, "current_phase", None)

def get_current_step(controller):
    if hasattr(controller, "_phase_state"):
        return controller._phase_state.get("step")
    return getattr(controller, "current_step", None)
