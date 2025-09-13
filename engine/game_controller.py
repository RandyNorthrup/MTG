"""MTG Game Controller - Core game flow and state management."""

import os
import random
from typing import Dict, Iterable

from ai.basic_ai import BasicAI
from ai_players.ai_player_simple import enhance_ai_controllers
from engine.game_state import GameState
from engine.mana import ManaPool, parse_mana_cost
from engine.phase_hooks import (
    advance_step,
    get_current_phase,
    get_current_step,
    init_turn_phase_state,
    set_phase,
)
from engine.stack import StackEngine

class GameController:
    """Core game controller that manages MTG game flow and state.
    
    Separates game logic from UI, handling:
    - Game initialization and flow control
    - Turn/phase management
    - Player actions (casting, land plays, combat)
    - AI opponent coordination
    - Stack and priority management
    
    UI components should call enter_match() to start games and delegate
    key actions like phase advancement through this controller.
    """
    
    def __init__(self, game: GameState, ai_ids: Iterable[int], *, logging_enabled: bool):
        """Initialize game controller.
        
        Args:
            game: The GameState instance to control
            ai_ids: Player IDs that should be controlled by AI
            logging_enabled: Whether to enable debug logging
        """
        self.game = game
        self.logging_enabled = logging_enabled
        
        # Initialize AI controllers
        self.ai_controllers: Dict[int, BasicAI] = {
            pid: BasicAI(pid=pid) for pid in ai_ids
        }
        enhance_ai_controllers(self.game, self.ai_controllers)

        # Game flow state
        self.in_game = False
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        self._game_flow_started = False

        # Initialize phase management
        init_turn_phase_state(self)
        
        # Initialize stack engine for spell/ability resolution
        self.stack_engine = StackEngine(self.game, logging_enabled=logging_enabled)

    def log_phase(self):
        """Log phase changes for debugging purposes."""
        if not self.logging_enabled:
            return
        try:
            active_player = self.game.active_player
            player_name = self.game.players[active_player].name
            current_phase = getattr(self.game, 'phase', '?')
            
            # Only log if phase actually changed since last log
            if not hasattr(self, "_last_logged_phase"):
                self._last_logged_phase = None
            current_state = (player_name, current_phase)
            if self._last_logged_phase != current_state:
                self._last_logged_phase = current_state
        except Exception:
            # Silently ignore logging errors
            pass

    def enter_match(self):
        """Start a new game match."""
        self.in_game = True
        self._begin_game_flow()
        self._init_turn_structure()

    def start_new_turn(self):
        """Begin a new turn for the active player."""
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

    def _init_turn_structure(self):
        """Initialize/reset turn-structure state for a new game or turn using phase_hooks."""
        init_turn_phase_state(self)

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
            if len(winners)==1:
                return winners[0], rolls

    def set_starter(self, starter_pid: int):
        self.game.active_player = starter_pid
        self.skip_first_draw_player = starter_pid
        self.skip_first_draw_used = False
        self.first_player_decided = True
        # Opening hands will be drawn by the API after this method completes

    def draw_opening_hands(self):
        """Draw opening hands according to official MTG rules.
        
        Official MTG Rules (CR 103.4):
        - All players draw 7 cards for their opening hand
        - Turn order advantage comes from the first draw step, not opening hands
        """
        if self.opening_hands_drawn: return
        
        for pl in self.game.players:
            pl.hand = getattr(pl,'hand', [])
            
            # MTG Rules: ALL players draw exactly 7 cards for opening hand
            opening_hand_size = 7
            print(f"🃏 Drawing {opening_hand_size} cards for {pl.name} (opening hand)")
            
            # Clear existing hand and draw 7 cards
            pl.hand.clear()
            while len(pl.hand) < opening_hand_size and pl.library:
                pl.hand.append(pl.library.pop(0))
                
        self.opening_hands_drawn = True
        self.log_phase()

    # ---------- Phase control ----------
    # PHASE LOGIC REMOVED: advance_phase, advance_step, _execute_step_hooks, etc.
    # These are now imported from engine.phase_hooks and should be called via those functions.

    # Provide properties for UI consistency (phase = current_phase; step = current_step)
    @property
    def phase(self):
        # Always query from phase_hooks (canonical)
        return get_current_phase(self)

    @property
    def step(self):
        return get_current_step(self)

    @property
    def active_player(self):
        return getattr(self.game, 'active_player', 0)

    @property
    def active_player_name(self):
        active_id = getattr(self.game, 'active_player', 0)
        if self.game.players and 0 <= active_id < len(self.game.players):
            return self.game.players[active_id].name
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
        
        # If p0_path is None or doesn't exist, use first available deck
        if not p0_path or not os.path.exists(p0_path):
            if deck_files:
                p0_path = deck_files[0]  # Use first available deck
                
        specs = [
            (p0.name, p0_path, False),
            ("AI", ai_path, True)
        ]
        
        try:
            new_state, ai_ids = build_game_fn(specs, ai_enabled=True)
        except Exception as ex:
            return False
        self.game = new_state
        self.ai_controllers = {pid: BasicAI(pid=pid) for pid in ai_ids}
        enhance_ai_controllers(self.game, self.ai_controllers)
        # reset flow
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
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

    # Remove all stack logic from here; expose as proxy if needed for legacy:
    @property
    def stack(self):
        return self.stack_engine.stack

    def add_to_stack(self, *args, **kwargs):
        return self.stack_engine.add_to_stack(*args, **kwargs)

    def can_add_to_stack(self, *args, **kwargs):
        return self.stack_engine.can_add_to_stack(*args, **kwargs)

    def can_resolve(self):
        return self.stack_engine.can_resolve()

    def resolve_top(self, *args, **kwargs):
        return self.stack_engine.resolve_top(*args, **kwargs)

    def stack_size(self):
        return self.stack_engine.stack_size()

    def stack_top(self):
        return self.stack_engine.stack_top()

    def clear_stack(self):
        return self.stack_engine.clear_stack()

    def pass_priority(self, player_id: int):
        return self.stack_engine.pass_priority(player_id)

    def sync_phase_state(self):
        """
        Sync between controller phase system and game state phase system.
        Called when phases change, not on a timer.
        """
        if not self.in_game or not self.first_player_decided:
            return
            
        try:
            controller_phase = get_current_phase(self)
            if controller_phase:
                # Map controller phase names to game state phase names if needed
                phase_mapping = {
                    'precombat_main': 'MAIN1',
                    'postcombat_main': 'MAIN2',
                    'declare_attackers': 'COMBAT_DECLARE',
                    'declare_blockers': 'COMBAT_BLOCK',
                    'combat_damage': 'COMBAT_DAMAGE',
                    'draw': 'DRAW',
                    'untap': 'UNTAP',
                    'upkeep': 'UPKEEP',
                    'end': 'END',
                    'cleanup': 'CLEANUP'
                }
                game_phase = phase_mapping.get(controller_phase.lower(), controller_phase.upper())
                
                # Find the corresponding phase index in the game state
                from engine.game_state import PHASES
                if game_phase in PHASES:
                    new_index = PHASES.index(game_phase)
                    if new_index != self.game.phase_index:
                        old_phase = self.game.phase
                        self.game.phase_index = new_index
                        new_phase = self.game.phase
                        # Trigger phase actions when phase changes
                        if old_phase != new_phase:
                            # Execute controller phase actions (this handles draw, untap, etc.)
                            from engine.phase_hooks import _execute_phase_actions
                            _execute_phase_actions(self, controller_phase)
                            
                            # Force UI refresh after phase actions
                            if hasattr(self, '_api_ref') and self._api_ref:
                                self._api_ref._force_immediate_ui_refresh()
        except Exception:
            pass
