from PySide6.QtCore import QTimer

# High-level phases we expose to UI
HIGH_LEVEL_PHASES = [
    "Beginning",
    "PreCombatMain",
    "Combat",
    "PostCombatMain",
    "End",
]

_DISPLAY_NAMES = {
    "Beginning": "Beginning Phase",
    "PreCombatMain": "Pre-Combat Main Phase",
    "Combat": "Combat Phase",
    "PostCombatMain": "Post Combat Main Phase",
    "End": "End Phase",
}

# Internal timing (ms)
_BEGIN_STEP_DELAYS = [500, 600, 600]        # Untap -> Upkeep -> Draw visualization
_COMBAT_AUTO_DELAYS = [400, 500, 600]       # Blockers -> Damage -> EndCombat after attackers

_PHASE_CTRL_REG = {}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
_BEGIN_TOKENS = {"UNTAP", "UPKEEP", "DRAW"}
_MAIN1_TOKENS = {"MAIN1", "PRECOMBAT_MAIN", "MAIN"}
_COMBAT_TOKENS = {
    "COMBAT", "BEGIN_COMBAT", "DECLARE_ATTACKERS", "DECLARE_BLOCKERS",
    "COMBAT_DAMAGE", "END_COMBAT"
}
_MAIN2_TOKENS = {"MAIN2", "POSTCOMBAT_MAIN"}
_END_TOKENS = {"END", "END_STEP", "CLEANUP"}

def _canon(raw):
    up = (raw or "").upper()
    if up in _BEGIN_TOKENS:
        return "Beginning"
    if up in _MAIN1_TOKENS:
        return "PreCombatMain"
    if up in _COMBAT_TOKENS:
        return "Combat"
    if up in _MAIN2_TOKENS:
        return "PostCombatMain"
    if up in _END_TOKENS:
        return "End"
    # Fallback: if engine is already at some phase between cycles treat as Beginning
    return "Beginning"
_canon_phase = _canon  # ADDED alias for legacy references

def _active_player(game):
    ap = getattr(game, "active_player", 0)
    try:
        if hasattr(game, "players") and 0 <= ap < len(game.players):
            return game.players[ap]
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# Phase log deduper
# ---------------------------------------------------------------------------
def install_phase_log_adapter(controller):
    """
    Wrap controller.log_phase to emit only high-level phases (Beginning, PreCombatMain,
    Combat, PostCombatMain, End) once per phase per turn after the match actually starts.
    Suppresses all pre-game (roll / lobby) UNTAP spam.
    """
    if hasattr(controller, "_phase_log_adapter_installed"):
        return
    controller._phase_log_adapter_installed = True

    if not hasattr(controller, "_orig_log_phase"):
        controller._orig_log_phase = getattr(controller, "log_phase", lambda: None)

    state = {
        "last_key": None,          # (active_player, turn_marker, hl_phase)
        "last_print": None         # (active_player, hl_phase) legacy fallback
    }

    BEGIN = {"UNTAP", "UPKEEP", "DRAW"}
    MAIN1 = {"MAIN1", "PRECOMBAT_MAIN", "MAIN"}
    MAIN2 = {"MAIN2", "POSTCOMBAT_MAIN"}
    COMBAT = {
        "COMBAT", "BEGIN_COMBAT", "DECLARE_ATTACKERS", "DECLARE_BLOCKERS",
        "COMBAT_DAMAGE", "END_COMBAT"
    }
    ENDING = {"END", "END_STEP", "CLEANUP"}

    def _map(raw_token: str) -> str:
        up = (raw_token or "").upper()
        if up in BEGIN: return "Beginning"
        if up in MAIN1: return "PreCombatMain"
        if up in COMBAT: return "Combat"
        if up in MAIN2: return "PostCombatMain"
        if up in ENDING: return "End"
        return _canon(up)

    def _turn_marker(g):
        # Prefer an existing turn counter; else synthesize from active player changes
        tm = getattr(g, "turn_number", None)
        if tm is not None:
            return tm
        # Fallback: (active_player, total_phases_seen_mod) – very coarse, but stable enough
        return getattr(g, "active_player", 0)

    def _player_name(g, idx):
        try:
            if hasattr(g, "players") and 0 <= idx < len(g.players):
                return getattr(g.players[idx], "name", f"P{idx}")
        except Exception:
            pass
        return f"P{idx}"

    def _adapter():
        g = getattr(controller, "game", None)
        if not g:
            return
        # NEW: suppress all phase logs until game actually started AND phases unlocked
        if (not getattr(controller, "in_game", False)
                or not getattr(controller, "first_player_decided", False)
                or getattr(controller, "_phases_locked", False)):
            return
        raw = getattr(g, "phase", None)
        hl = _map(raw)
        ap = getattr(g, "active_player", None)
        tm = _turn_marker(g)
        key = (ap, tm, hl)

        # Only log once per (turn_marker, high-level phase, active player)
        if key == state["last_key"]:
            return
        state["last_key"] = key

        if getattr(controller, "logging_enabled", False):
            try:
                print(f"[PHASE] Active={_player_name(g, ap)} Phase={hl}")
            except Exception:
                pass

    controller.log_phase = _adapter

# Backwards compatibility old name
install_phase_log_deduper = install_phase_log_adapter

# ---------------------------------------------------------------------------
# Controller patch (single authoritative high-level progression)
# ---------------------------------------------------------------------------
def register_phase_controller(controller):
    if controller in _PHASE_CTRL_REG:
        return
    game = getattr(controller, "game", None)
    if not game:
        return

    # Track high-level phase separately (do NOT assign to game.phase which appears read-only)
    controller._hl_phase = _canon_phase(getattr(game, "phase", None))
    controller._begin_seq_running = False
    controller._begin_step_index = 0
    controller._combat_wait_attackers = False
    controller._combat_seq_running = False
    controller._combat_skip_requested = False
    controller._phases_locked = True        # NEW: prevent auto-Beginning sequence until hands done

    if not hasattr(controller, "_original_advance_phase"):
        controller._original_advance_phase = controller.advance_phase

    # --- Helpers ------------------------------------------------------------
    def _underlying_token():
        return (getattr(game, "phase", None) or "").upper()

    def _refresh_high_level():
        controller._hl_phase = _canon_phase(_underlying_token())

    def _log_and_ui():
        if getattr(controller, "logging_enabled", False) and hasattr(controller, "log_phase"):
            try:
                controller.log_phase()
            except Exception:
                pass
        host = getattr(controller, "_ui_host", None)
        if host:
            try:
                update_phase_ui(host)
            except Exception:
                pass

    # Beginning automation: schedule underlying advances (call original) if engine
    # stays within UNTAP/UPKEEP/DRAW; once engine reaches MAIN1 we mark PreCombatMain.
    def _run_beginning_sequence():
        if controller._begin_seq_running or controller._phases_locked:
            return
        controller._begin_seq_running = True
        controller._begin_step_index = 0

        def _step():
            # Stop if underlying phase left beginning bucket
            if _canon_phase(_underlying_token()) != "Beginning":
                controller._begin_seq_running = False
                controller._begin_step_index = 0
                _refresh_high_level()
                if controller._hl_phase == "Beginning":
                    # Engine skipped directly to Main1? adjust to PreCombatMain
                    controller._hl_phase = "PreCombatMain"
                    _log_and_ui()
                return
            if controller._begin_step_index >= 3:
                controller._begin_seq_running = False
                controller._begin_step_index = 0
                # Force high-level shift if still in Beginning mapping
                if _canon_phase(_underlying_token()) == "Beginning":
                    controller._hl_phase = "PreCombatMain"
                    _log_and_ui()
                return
            controller._begin_step_index += 1
            # Advance underlying once (ignore errors)
            try:
                controller._original_advance_phase()
            except Exception:
                pass
            # Schedule next internal step
            delay = _BEGIN_STEP_DELAYS[min(controller._begin_step_index - 1, len(_BEGIN_STEP_DELAYS)-1)]
            QTimer.singleShot(delay, _step)

        # Kick off sequence
        QTimer.singleShot(_BEGIN_STEP_DELAYS[0], _step)

    # NEW: public unlock method invoked after opening hands / mulligans resolved
    def _unlock_phases():
        if not controller._phases_locked:
            return
        controller._phases_locked = False
        _refresh_high_level()
        if controller._hl_phase == "Beginning":
            _run_beginning_sequence()
        else:
            _log_and_ui()
    controller.unlock_phases = _unlock_phases

    def _has_attackers():
        pl = _active_player(game)
        if not pl:
            return False
        bf = getattr(pl, "battlefield", []) or []
        for c in bf:
            try:
                if 'Creature' not in getattr(c, 'types', []):
                    continue
                if getattr(c, 'tapped', False):
                    continue
                sick = getattr(c, 'summoning_sick', getattr(c, 'summoning_sickness', False))
                if sick and not (getattr(c, 'haste', False) or
                                 'Haste' in getattr(c, 'keywords', []) or
                                 'haste' in getattr(c, 'text', '').lower()):
                    continue
                return True
            except Exception:
                continue
        return False

    def _maybe_start_combat_wait():
        # Called after a transition into Combat
        if controller._combat_skip_requested:
            return False
        if not _has_attackers():
            return False
        controller._combat_wait_attackers = True
        return True

    def _start_combat_sequence_after_attackers():
        if controller._combat_seq_running:
            return
        controller._combat_seq_running = True
        controller._combat_wait_attackers = False
        steps = ["DeclareBlockers", "CombatDamage", "EndCombat"]
        idx = 0

        def _cstep():
            nonlocal idx
            # abort if engine left combat
            if _canon_phase(_underlying_token()) != "Combat":
                controller._combat_seq_running = False
                _refresh_high_level()
                return
            if idx >= len(steps):
                controller._combat_seq_running = False
                # Move high-level to PostCombatMain
                controller._hl_phase = "PostCombatMain"
                _log_and_ui()
                return
            idx += 1
            try:
                controller._original_advance_phase()
            except Exception:
                pass
            delay = _COMBAT_AUTO_DELAYS[min(idx-1, len(_COMBAT_AUTO_DELAYS)-1)]
            QTimer.singleShot(delay, _cstep)

        # First auto step after short delay (gives UI time to show "Attackers" window if needed)
        QTimer.singleShot(_COMBAT_AUTO_DELAYS[0], _cstep)

    def _fast_forward_to(target_hl: str, limit: int = 30):
        # Advance underlying until canonical high-level maps to target
        for _ in range(limit):
            _refresh_high_level()
            if controller._hl_phase == target_hl:
                return
            try:
                controller._original_advance_phase()
            except Exception:
                break
        _refresh_high_level()

    # --- Patched advance_phase ----------------------------------------------
    def _patched_advance_phase():
        _refresh_high_level()

        # Block any manual advance while phases are locked (before hands finished)
        if controller._phases_locked:
            return

        # If player ends Beginning early, ignore until automated sequence finishes
        if controller._hl_phase == "Beginning" and controller._begin_seq_running:
            return

        # If player ends Combat while waiting for attackers -> skip combat remainder
        if controller._hl_phase == "Combat" and controller._combat_wait_attackers:
            controller._combat_skip_requested = True
            controller._combat_wait_attackers = False
            controller._combat_seq_running = False
            controller._fast_forward_after_skip()
            return

        # Normal underlying advance
        try:
            controller._original_advance_phase()
        finally:
            _refresh_high_level()
            # Transition checks
            if controller._hl_phase == "Beginning":
                _run_beginning_sequence()
            elif controller._hl_phase == "Combat":
                if controller._combat_skip_requested or not _maybe_start_combat_wait():
                    # Skip entire combat
                    controller._combat_skip_requested = False
                    _fast_forward_to("PostCombatMain")
                    controller._hl_phase = "PostCombatMain"
            _log_and_ui()

    controller.advance_phase = _patched_advance_phase

    # Helper for skip call inside patched
    def _fast_forward_after_skip():
        _fast_forward_to("PostCombatMain")
        controller._hl_phase = "PostCombatMain"
        controller._combat_skip_requested = False
        _log_and_ui()
    controller._fast_forward_after_skip = _fast_forward_after_skip

    # Public helper: attackers declared
    def _mark_attackers_declared():
        if controller._hl_phase == "Combat" and controller._combat_wait_attackers:
            controller._combat_wait_attackers = False
            if controller._combat_skip_requested:
                _fast_forward_after_skip()
            else:
                _start_combat_sequence_after_attackers()
                _log_and_ui()
    controller.mark_combat_attackers_declared = _mark_attackers_declared

    # Public helper: request combat skip (UI)
    def _request_skip():
        if controller._hl_phase == "Combat" and controller._combat_wait_attackers:
            controller._combat_skip_requested = True
            controller._combat_wait_attackers = False
            _fast_forward_after_skip()
    controller.request_skip_combat = _request_skip

    # IMPORTANT: do NOT auto start beginning sequence here anymore
    _log_and_ui()
    _PHASE_CTRL_REG[controller] = True

# Backwards alias
install_phase_control = register_phase_controller

# ---------------------------------------------------------------------------
# UI banner update
# ---------------------------------------------------------------------------
def update_phase_ui(host):
    """
    Update a banner (play_area.update_phase_banner(display_phase, active_player_name))
    if play_area implements it. Silent on failure.
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
