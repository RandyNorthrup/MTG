import os, time, random
from typing import Callable, Dict, Iterable
from engine.mana import parse_mana_cost
from image_cache import ensure_card_image
from config import STARTING_LIFE
from engine.game_state import GameState, PlayerState
from ai.basic_ai import BasicAI
from engine.turn_manager import TurnManager
from engine.rules_engine import init_rules
from ai_players.ai_player_simple import enhance_ai_controllers  # CHANGED
from engine.turn_structure import (
    PHASE_SEQUENCE, PHASE_STEPS, first_step_of_phase, next_flat_step
)
from engine.phase_hooks import (
    advance_phase,
    advance_step,
    set_phase,
    update_phase_ui,
    log_phase,  # Import log_phase from phase_hooks
)

class GameController:
    """
    Decouples play logic from MainWindow UI.
    UI should:
      - call enter_match() when user starts game
      - call tick(refresh_callable) from a QTimer
      - delegate key actions (advance phase, space key, etc.)
    """
    def __init__(self, game: GameState, ai_ids: Iterable[int], *, logging_enabled: bool):
        self.game = game
        if not hasattr(self.game, 'turn_manager'):
            try:
                self.game.turn_manager = TurnManager(self.game)
            except Exception:
                pass
        self.logging_enabled = logging_enabled
        self.ai_controllers: Dict[int, BasicAI] = {pid: BasicAI(pid=pid) for pid in ai_ids}
        enhance_ai_controllers(self.game, self.ai_controllers)  # CHANGED

        # Flow state
        self.in_game = False
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        self._game_flow_started = False

        # Turn structure state
        self.current_phase: str = PHASE_SEQUENCE[0]
        self.current_step: str = first_step_of_phase(self.current_phase)
        self.visited_phases: set[str] = set()  # phases fully completed this turn

        # ---------- Strict Stack Mechanics ----------
        self.stack = []  # Strict stack: list of stack objects (LIFO)
        self._stack_id_counter = 1  # Unique id for stack objects

    # ---------- Logging ----------
    def log_phase(self):
        if not self.logging_enabled:
            return
        try:
            ap = self.game.active_player
            nm = self.game.players[ap].name
            # Only log if phase actually changed since last log
            if not hasattr(self, "_last_logged_phase"):
                self._last_logged_phase = None
            current = (nm, getattr(self.game, 'phase', '?'))
            if self._last_logged_phase != current:
                print(f"[PHASE] Active={nm} Phase={getattr(self.game,'phase','?')}")
                self._last_logged_phase = current
        except Exception:
            pass

    # ---------- Game start ----------
    def enter_match(self):
        self.in_game = True
        self._begin_game_flow()
        self._init_turn_structure()

    def _begin_game_flow(self):
        if self._game_flow_started: return
        self._game_flow_started = True
        if len(self.game.players) > 1:
            # UI should prompt roll; controller waits
            return
        # single player immediate start
        if not self.opening_hands_drawn:
            self.draw_opening_hands()
        self.first_player_decided = True
        if self.logging_enabled:
            print("[START] Single-player game begun (no roll).")

    def _init_turn_structure(self):
        """Initialize / reset turn-structure state for a new game or turn."""
        self.current_phase = PHASE_SEQUENCE[0]
        self.current_step = first_step_of_phase(self.current_phase)
        # track for sanity (not re-entry)
        self._turn_no = 1
        self._active_player = 0  # Index of the active player

    # ---------- Roll / mulligans ----------
    def perform_first_player_roll(self):
        """
        Pure logic: returns (winner_id, rolls_dict) after resolving ties internally.
        Caller (UI) then decides keep/pass and sets starter with set_starter(starter_id).
        """
        while True:
            rolls = {pl.player_id: random.randint(1,20) for pl in self.game.players}
            hi = max(rolls.values())
            winners = [pid for pid,v in rolls.items() if v==hi]
            if self.logging_enabled:
                print("[ROLL] " + ", ".join(f"{self.game.players[p].name}:{rolls[p]}" for p in rolls))
            if len(winners)==1:
                return winners[0], rolls
            if self.logging_enabled:
                print("[ROLL][TIE] Re-rolling...")

    def set_starter(self, starter_pid: int):
        self.game.active_player = starter_pid
        self.skip_first_draw_player = starter_pid
        self.skip_first_draw_used = False
        self.first_player_decided = True
        # Opening hand draw after small delay (UI can call draw_opening_hands immediately or via QTimer)
        self.draw_opening_hands()

    def draw_opening_hands(self):
        if self.opening_hands_drawn: return
        for pl in self.game.players:
            pl.hand = getattr(pl,'hand', [])
            while len(pl.hand) < 7 and pl.library:
                pl.hand.append(pl.library.pop(0))
        self.opening_hands_drawn = True
        if self.logging_enabled:
            print("[START] Opening hands drawn.")
        self.log_phase()

    # ---------- Phase control ----------
    # PHASE LOGIC REMOVED: advance_phase, advance_step, _execute_step_hooks, etc.
    # These are now imported from engine.phase_hooks and should be called via those functions.

    # Provide properties for UI consistency (phase = current_phase; step = current_step)
    @property
    def phase(self):  # ADDED
        return self.current_phase

    @property
    def step(self):  # ADDED
        return self.current_step

    @property
    def active_player(self):
        return self._active_player

    @property
    def active_player_name(self):
        if self.game.players and 0 <= self._active_player < len(self.game.players):
            return self.game.players[self._active_player].name
        return "—"

    # ---------- Deck / Opponent helpers ----------
    def ensure_ai_opponent(self, build_game_fn):
        """
        build_game_fn: callable(specs)->(new_game, ai_ids) (delegates to existing new_game)
        """
        if len(self.game.players) != 1:
            return False
        p0 = self.game.players[0]
        p0_path = getattr(p0,'source_path', None)
        decks_dir = os.path.join('data','decks')
        deck_files = sorted([os.path.join(decks_dir,f) for f in os.listdir(decks_dir)
                             if f.lower().endswith('.txt')])
        ai_path = None
        for cand in deck_files:
            if p0_path and os.path.abspath(cand) == os.path.abspath(p0_path):
                continue
            ai_path = cand
            break
        if not ai_path:
            ai_path = os.path.join(decks_dir,'missing_ai_deck.txt')
        specs = [
            (p0.name, p0_path, False),
            ("AI", ai_path, True)
        ]
        try:
            new_state, ai_ids = build_game_fn(specs, ai_enabled=True)
        except Exception as ex:
            if self.logging_enabled:
                print(f"[AI-AUTO][ERR] {ex}")
            return False
        self.game = new_state
        self.ai_controllers = {pid: BasicAI(pid=pid) for pid in ai_ids}
        enhance_ai_controllers(self.game, self.ai_controllers)
        # reset flow
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        if self.logging_enabled:
            print("[AI-AUTO] Added AI opponent automatically.")
        return True

    def reload_player0(self, new_game_fn, path: str):
        """
        Rebuild game preserving other players' deck paths where possible.
        new_game_fn(specs, ai_enabled)->(game, ai_ids)
        """
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        specs = []
        for p in self.game.players:
            deck_path = path if p.player_id == 0 else getattr(p,'source_path', None)
            specs.append((p.name, deck_path, p.player_id in self.ai_controllers))
        new_state, ai_ids = new_game_fn(specs, ai_enabled=True)
        self.game = new_state
        self.ai_controllers = {pid: BasicAI(pid=pid) for pid in ai_ids}
        enhance_ai_controllers(self.game, self.ai_controllers)
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        return self.game

    def toggle_attacker(self, card):
        perm = self._find_perm(card.id)
        if perm:
            self.game.combat.toggle_attacker(0, perm)

    def has_attackers(self):
        return bool(getattr(self.game.combat.state, "attackers", []))

    def commit_attackers(self):
        self.game.combat.attackers_committed()
        advance_step(self)

    def commit_blockers(self):
        advance_step(self)
        try:
            self.game.combat.assign_and_deal_damage()
        except Exception:
            pass
        advance_step(self)

    def advance_to_phase(self, phase_name):
        set_phase(self, phase_name)

    def play_land(self, card):
        self.game.play_land(0, card)

    def cast_spell(self, card):
        # ...autotap and cast logic as previously in game_app_api...
        ps = self.game.players[0]
        if not hasattr(ps, 'mana_pool'):
            from engine.mana import ManaPool
            ps.mana_pool = ManaPool()
        pool = ps.mana_pool
        from engine.mana import parse_mana_cost
        cost_dict = parse_mana_cost(getattr(card, 'mana_cost_str', None))
        if not cost_dict:
            generic_need = card.mana_cost if isinstance(card.mana_cost, int) else 0
            if generic_need:
                cost_dict = {'G': generic_need}
        colored_needs = {c: n for c, n in cost_dict.items() if c in ('W', 'U', 'B', 'R', 'G') and n > 0}
        def land_color(perm):
            n = perm.card.name.lower()
            for t, c in [('plains', 'W'), ('island', 'U'), ('swamp', 'B'), ('mountain', 'R'), ('forest', 'G')]:
                if t in n:
                    return c
            return 'G'
        untapped = [perm for perm in ps.battlefield if 'Land' in perm.card.types and not perm.tapped]
        for color, need in list(colored_needs.items()):
            while need > 0:
                found = next((l for l in untapped if land_color(l) == color), None)
                if not found:
                    break
                self.game.tap_for_mana(0, found)
                pool.add(color, 1)
                untapped.remove(found)
                need -= 1
            colored_needs[color] = need
        remaining = cost_dict.get('G', 0) + sum(rem for rem in colored_needs.values() if rem > 0)
        for land in list(untapped):
            if remaining <= 0:
                break
            sym = land_color(land)
            self.game.tap_for_mana(0, land)
            pool.add(sym, 1)
            remaining -= 1
        if not pool.can_pay(cost_dict):
            return
        pool.pay(cost_dict)
        self.game.cast_spell(0, card)

    def _find_perm(self, card_id):
        for p in self.game.players:
            for perm in p.battlefield:
                if getattr(perm.card, 'id', None) == card_id:
                    return perm
        return None

    # ---------- Strict Stack Mechanics ----------
    def __init__(self, game: GameState, ai_ids: Iterable[int], *, logging_enabled: bool):
        self.game = game
        if not hasattr(self.game, 'turn_manager'):
            try:
                self.game.turn_manager = TurnManager(self.game)
            except Exception:
                pass
        self.logging_enabled = logging_enabled
        self.ai_controllers: Dict[int, BasicAI] = {pid: BasicAI(pid=pid) for pid in ai_ids}
        enhance_ai_controllers(self.game, self.ai_controllers)  # CHANGED

        # Flow state
        self.in_game = False
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        self._game_flow_started = False

        # Turn structure state
        self.current_phase: str = PHASE_SEQUENCE[0]
        self.current_step: str = first_step_of_phase(self.current_phase)
        self.visited_phases: set[str] = set()  # phases fully completed this turn

        # ---------- Strict Stack Mechanics ----------
        self.stack = []  # Strict stack: list of stack objects (LIFO)
        self._stack_id_counter = 1  # Unique id for stack objects

    def add_to_stack(self, obj, obj_type: str, controller_id: int, targets=None, info=None):
        """
        Add a spell or ability to the stack.
        obj_type: 'spell' | 'activated' | 'triggered'
        obj: Card or Ability object
        controller_id: player id who controls the object
        targets: list of targets (optional)
        info: dict for extra metadata (optional)
        Returns stack object id.
        """
        stack_obj = {
            "id": self._stack_id_counter,
            "type": obj_type,
            "obj": obj,
            "controller_id": controller_id,
            "targets": targets or [],
            "info": info or {},
        }
        self._stack_id_counter += 1
        self.stack.append(stack_obj)
        if self.logging_enabled:
            print(f"[STACK] + {obj_type.upper()} ({getattr(obj, 'name', getattr(obj, 'raw_text', repr(obj)))}) by P{controller_id} (targets: {targets})")
        return stack_obj["id"]

    def can_add_to_stack(self, obj, obj_type: str, controller_id: int, targets=None, info=None):
        """
        Check if the object can be legally added to the stack (timing, legality, etc).
        For now, always returns True (expand for strict rules).
        """
        # TODO: Implement strict timing, priority, and legality checks.
        return True

    def can_resolve(self):
        """Return True if the stack is non-empty and the top object is resolvable."""
        return bool(self.stack)

    def resolve_top(self, game=None):
        """
        Resolve the top object on the stack (LIFO).
        Handles spells, activated abilities, triggered abilities.
        """
        if not self.stack:
            return None
        stack_obj = self.stack.pop()
        obj_type = stack_obj["type"]
        obj = stack_obj["obj"]
        controller_id = stack_obj["controller_id"]
        targets = stack_obj["targets"]
        info = stack_obj["info"]
        if self.logging_enabled:
            print(f"[STACK] - Resolving {obj_type.upper()} ({getattr(obj, 'name', getattr(obj, 'raw_text', repr(obj)))}) by P{controller_id}")
        # Dispatch to appropriate resolver
        if obj_type == "spell":
            self._resolve_spell(obj, controller_id, targets, info)
        elif obj_type == "activated":
            self._resolve_activated_ability(obj, controller_id, targets, info)
        elif obj_type == "triggered":
            self._resolve_triggered_ability(obj, controller_id, targets, info)
        else:
            if self.logging_enabled:
                print(f"[STACK][WARN] Unknown stack object type: {obj_type}")
        # After resolution, check for state-based actions, triggers, etc.
        self._after_stack_resolution()
        return stack_obj

    def _resolve_spell(self, card, controller_id, targets, info):
        # Example: move spell to graveyard, apply effect, etc.
        if hasattr(card, "resolve"):
            card.resolve(self.game, controller_id, targets, info)
        else:
            # Default: move to graveyard
            if hasattr(self.game, "move_to_graveyard"):
                self.game.move_to_graveyard(card, controller_id)
        if self.logging_enabled:
            print(f"[STACK][SPELL] {getattr(card, 'name', repr(card))} resolved.")

    def _resolve_activated_ability(self, ability, controller_id, targets, info):
        # ability: ActivatedAbility object
        if hasattr(ability, "resolve"):
            ability.resolve(self.game, controller_id, targets, info)
        if self.logging_enabled:
            print(f"[STACK][ACTIVATED] {getattr(ability, 'raw_text', repr(ability))} resolved.")

    def _resolve_triggered_ability(self, ability, controller_id, targets, info):
        # ability: TriggeredAbility object
        if hasattr(ability, "resolve"):
            ability.resolve(self.game, controller_id, targets, info)
        if self.logging_enabled:
            print(f"[STACK][TRIGGERED] {getattr(ability, 'raw_text', repr(ability))} resolved.")

    def _after_stack_resolution(self):
        """
        After a stack object resolves, check for state-based actions, triggers, etc.
        """
        # Example: check for lethal damage, empty library, etc.
        # This is a stub for integration with rules engine.
        if hasattr(self.game, "check_state_based_actions"):
            self.game.check_state_based_actions()
        # Check for new triggers and add to stack if needed
        if hasattr(self.game, "check_triggers"):
            triggers = self.game.check_triggers()
            for trig in triggers:
                self.add_to_stack(trig["ability"], "triggered", trig["controller_id"], trig.get("targets"), trig.get("info"))

    def stack_size(self):
        return len(self.stack)

    def stack_top(self):
        return self.stack[-1] if self.stack else None

    def clear_stack(self):
        """Empty the stack (for game reset or debugging)."""
        self.stack.clear()
        if self.logging_enabled:
            print("[STACK] Cleared.")

    def pass_priority(self, player_id: int):
        """
        Strict stack: player passes priority. If all players pass in succession, resolve top of stack or end phase.
        """
        # Advanced: Track priority for all players (APNAP order)
        if not hasattr(self, "_priority_passes"):
            self._priority_passes = set()
        self._priority_passes.add(player_id)
        if len(self._priority_passes) >= len(self.game.players):
            self._priority_passes.clear()
            if self.can_resolve():
                self.resolve_top()
            else:
                # No stack: phase/step ends (handled by phase logic)
                if self.logging_enabled:
                    print("[STACK] All players passed, phase/step ends.")
                advance_phase(self)
        else:
            if self.logging_enabled:
                print(f"[STACK] Player {player_id} passed priority.")
            self._priority_passes = set()
        self._priority_passes.add(player_id)
        if len(self._priority_passes) >= len(self.game.players):
            self._priority_passes.clear()
            if self.can_resolve():
                self.resolve_top()
            else:
                # No stack: phase/step ends (handled by phase logic)
                if self.logging_enabled:
                    print("[STACK] All players passed, phase/step ends.")
                advance_phase(self)
        else:
            if self.logging_enabled:
                print(f"[STACK] Player {player_id} passed priority.")
            ability.resolve(self.game, controller_id, targets, info)
        if self.logging_enabled:
            print(f"[STACK][TRIGGERED] {getattr(ability, 'raw_text', repr(ability))} resolved.")

    def _after_stack_resolution(self):
        """
        After a stack object resolves, check for state-based actions, triggers, etc.
        """
        # Example: check for lethal damage, empty library, etc.
        # This is a stub for integration with rules engine.
        if hasattr(self.game, "check_state_based_actions"):
            self.game.check_state_based_actions()
        # Check for new triggers and add to stack if needed
        if hasattr(self.game, "check_triggers"):
            triggers = self.game.check_triggers()
            for trig in triggers:
                self.add_to_stack(trig["ability"], "triggered", trig["controller_id"], trig.get("targets"), trig.get("info"))

    def stack_size(self):
        return len(self.stack)

    def stack_top(self):
        return self.stack[-1] if self.stack else None

    def clear_stack(self):
        """Empty the stack (for game reset or debugging)."""
        self.stack.clear()
        if self.logging_enabled:
            print("[STACK] Cleared.")

    def pass_priority(self, player_id: int):
        """
        Strict stack: player passes priority. If all players pass in succession, resolve top of stack or end phase.
        """
        # For multiplayer, track priority order and pass count.
        # For now, assume two-player and resolve immediately if both pass.
        # TODO: Implement strict APNAP priority and multiplayer.
        if self.can_resolve():
            self.resolve_top()
        else:
            # No stack: phase/step ends (handled by phase logic)
            if self.logging_enabled:
                print("[STACK] All players passed, phase/step ends.")
        if self.can_resolve():
            self.resolve_top()
        else:
            # No stack: phase/step ends (handled by phase logic)
            if self.logging_enabled:
                print("[STACK] All players passed, phase/step ends.")
