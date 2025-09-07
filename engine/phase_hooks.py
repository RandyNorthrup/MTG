from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout

# --- Canonical Phase Order ---------------------------------------------------
PHASE_SEQUENCE = [
    "Untap",
    "Upkeep",
    "Draw",
    "Main1",
    "BeginCombat",
    "DeclareAttackers",
    "DeclareBlockers",
    "CombatDamage",
    "EndCombat",
    "Main2",
    "End",
    "Cleanup",
]

_PHASE_ALIASES = {
    # core
    "UNTAP": "Untap",
    "UPKEEP": "Upkeep",
    "DRAW": "Draw",
    "PRECOMBAT_MAIN": "Main1",
    "MAIN": "Main1",
    "MAIN1": "Main1",
    "BEGIN_COMBAT": "BeginCombat",
    "DECLARE_ATTACKERS": "DeclareAttackers",
    "DECLARE_BLOCKERS": "DeclareBlockers",
    "COMBAT_DAMAGE": "CombatDamage",
    "END_COMBAT": "EndCombat",
    "POSTCOMBAT_MAIN": "Main2",
    "MAIN2": "Main2",
    "END_STEP": "End",
    "END": "End",
    "CLEANUP": "Cleanup",
}

def _normalize_phase(raw) -> str:
    if raw is None:
        return "-"
    s = str(raw).strip()
    if not s:
        return "-"
    key = s.upper().replace(" ", "_")
    return _PHASE_ALIASES.get(key, s if s in PHASE_SEQUENCE else "-")

def _phase_index(name: str) -> int:
    try:
        return PHASE_SEQUENCE.index(name)
    except ValueError:
        return -1

# --- Phase Validation --------------------------------------------------------
class PhaseOrderValidator:
    def __init__(self, controller):
        self.controller = controller
        self._last_index = None

    def check(self):
        g = getattr(self.controller, "game", None)
        if not g:
            return
        cur = _normalize_phase(getattr(g, "phase", None))
        idx = _phase_index(cur)
        if idx < 0:
            return
        if self._last_index is None:
            self._last_index = idx
            return
        # allow wrap (Cleanup -> Untap)
        if idx == 0 and self._last_index == len(PHASE_SEQUENCE) - 1:
            self._last_index = idx
            return
        # allow staying or advancing one
        if idx in (self._last_index, self._last_index + 1):
            self._last_index = idx
            return
        if self.controller.logging_enabled:
            print(f"[PHASE][WARN] Irregular jump {PHASE_SEQUENCE[self._last_index]} -> {cur}")
        self._last_index = idx

# --- Automatic Turn Start (Untap -> Upkeep -> Draw) --------------------------
class OpeningTurnSkipper:
    """
    Auto turn start helper:
      Automatically advances from Untap to Upkeep after a 1s delay once the turn begins.
      DOES NOT auto-advance from Upkeep to Draw (so upkeep triggers & player priority occur).
    """
    def __init__(self, controller):
        self.controller = controller
        self._pending = False  # waiting to fire Untap->Upkeep
        self._armed_turn_id = None  # track turn to avoid multiple schedules

    def _schedule(self):
        QTimer.singleShot(1000, self._fire)

    def _fire(self):
        # Execute only if still valid
        g = getattr(self.controller, "game", None)
        if not g or not self.controller.in_game or not self.controller.first_player_decided:
            self._pending = False
            return
        cur = _normalize_phase(getattr(g, "phase", None))
        if cur == "Untap":
            try:
                self.controller.advance_phase()  # -> Upkeep
            except Exception:
                pass
        # Clear pending regardless (never chain to Draw)
        self._pending = False
        self._armed_turn_id = None

    def tick(self):
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        g = self.controller.game
        cur = _normalize_phase(getattr(g, "phase", None))
        # Identify turn by active player + a simple turn counter if present
        turn_id = (getattr(g, "active_player", None), getattr(g, "turn_number", None))
        if cur == "Untap":
            if not self._pending or self._armed_turn_id != turn_id:
                self._pending = True
                self._armed_turn_id = turn_id
                self._schedule()
        else:
            # Any other phase cancels pending auto
            self._pending = False
            self._armed_turn_id = None

# --- Phase Stall Advancer ----------------------------------------------------
class PhaseAdvanceManager:
    """
    If a phase sits too long with empty stack & all players passed priority (simple heuristic),
    we can nudge the controller to auto-advance (mainly for AI progression).
    """
    def __init__(self, controller, min_interval: float = 0.75, stall_seconds: float = 15.0):
        self.controller = controller
        self.min_interval = max(0.25, float(min_interval))
        self.stall_seconds = stall_seconds
        self._last_phase = None
        self._last_change_time = 0.0
        self._last_tick_time = 0.0
        self.validator = PhaseOrderValidator(controller)

    def tick(self):
        import time
        now = time.time()
        if now - self._last_tick_time < self.min_interval:
            return
        self._last_tick_time = now
        g = getattr(self.controller, "game", None)
        if not g:
            return
        cur = _normalize_phase(getattr(g, "phase", None))
        if cur != self._last_phase:
            self._last_phase = cur
            self._last_change_time = now
        else:
            # same phase too long? attempt soft advance (not during combat subsections unless AI)
            if (now - self._last_change_time) > self.stall_seconds:
                if cur not in ("DeclareBlockers", "CombatDamage") and self.controller.in_game:
                    if self.controller.logging_enabled:
                        print(f"[PHASE][AUTO] Advancing stalled phase {cur}")
                    try:
                        self.controller.advance_phase()
                        self._last_change_time = now
                    except Exception:
                        pass
        # validate after potential change
        self.validator.check()

# --- UI Phase Bar ------------------------------------------------------------
def _ensure_phase_bar(host):
    """
    Create phase bar (horizontal labels) once.
    host expected: MainWindow shell (has play_stack or layout). Labels cached at host._phase_bar_labels.
    """
    if hasattr(host, "_phase_bar_labels"):
        return
    bar = QWidget()
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(4, 2, 4, 2)
    lay.setSpacing(6)
    labels = []
    for name in PHASE_SEQUENCE:
        lbl = QLabel(name)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color:#666;padding:2px 4px;border:1px solid #333;border-radius:3px;font-size:10px;")
        lay.addWidget(lbl)
        labels.append(lbl)
    host._phase_bar_labels = labels
    host._phase_bar_widget = bar
    # Try to insert into board wrapper (play_stack index 1)
    try:
        if hasattr(host, "play_stack"):
            board_widget = host.play_stack.widget(1)
            if board_widget and board_widget.layout():
                board_widget.layout().insertWidget(1, bar)  # under top control row
    except Exception:
        pass

def _highlight(host, norm):
    labels = getattr(host, "_phase_bar_labels", [])
    for lbl in labels:
        txt = lbl.text()
        if txt == norm:
            lbl.setStyleSheet(
                "color:#fff;background:#2d6b9e;padding:2px 4px;"
                "border:1px solid #66aadd;border-radius:3px;font-weight:bold;font-size:10px;"
            )
        else:
            lbl.setStyleSheet(
                "color:#666;padding:2px 4px;border:1px solid #333;border-radius:3px;font-size:10px;"
            )

# --- Public UI Update --------------------------------------------------------
def update_phase_ui(host):
    """
    Called by MainWindow each timer tick.
    Shows bar even if starter not chosen (no highlight if no phase yet).
    """
    try:
        _ensure_phase_bar(host)
        game = getattr(host, "game", None)
        if not game:
            return
        raw = getattr(game, "phase", None)
        norm = _normalize_phase(raw)
        if norm in PHASE_SEQUENCE:
            _highlight(host, norm)
        else:
            # no known phase yet -> dim all (already default)
            pass
    except Exception as ex:
        ctrl = getattr(host, "controller", None)
        if ctrl and getattr(ctrl, "logging_enabled", False):
            print(f"[PHASE][ERR] UI update failed: {ex}")

def install_phase_log_deduper(controller):
    """
    Wrap controller.log_phase to suppress duplicate consecutive logs
    of identical (active_player, phase). Safe to call multiple times.
    """
    if hasattr(controller, '_phase_dedupe_installed'):
        return
    controller._phase_dedupe_installed = True
    orig = getattr(controller, 'log_phase', None)
    if orig is None:
        return
    state = {'last': None}

    def _wrapped():
        g = getattr(controller, 'game', None)
        if not g:
            return orig()
        cur_phase = _normalize_phase(getattr(g, 'phase', None))
        ap = getattr(g, 'active_player', None)
        key = (ap, cur_phase)
        if state['last'] == key:
            return  # skip duplicate
        state['last'] = key
        orig()
    controller.log_phase = _wrapped
