import time

# ...existing update_phase_ui (keep if already defined) or will be appended below...

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
    except Exception:
        pname = "?"
    bar = getattr(main_win.play_area, 'phase_progress_bar', None)
    if bar is not None:
        try:
            base = getattr(bar, '_orig_format', None)
            if base is None:
                base = bar.format() if hasattr(bar, 'format') else "%v/%m"
                if not base:
                    base = "%v/%m"
                bar._orig_format = base
            bar.setFormat(f"{pname} - {base}")
        except Exception:
            pass
    lbl = getattr(main_win.play_area, 'phase_label', None)
    if lbl is not None:
        try:
            base_txt = getattr(lbl, '_orig_text', None)
            if base_txt is None:
                base_txt = lbl.text()
                lbl._orig_text = base_txt
            lbl.setText(f"{pname} - {base_txt}")
        except Exception:
            pass
