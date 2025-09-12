import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .card_engine import Card, Permanent, ActionResult
from .stack import Stack, StackItem
from .rules_engine import CommanderTracker
from .mana import ManaPool

# MTG Comprehensive Rules 500 - Turn Structure
# Proper phases and steps according to CR 500.1
PHASES = [
    # Beginning Phase (CR 502)
    "UNTAP", "UPKEEP", "DRAW",
    # First Main Phase (CR 505)
    "PRECOMBAT_MAIN",
    # Combat Phase (CR 506)
    "BEGIN_COMBAT", "DECLARE_ATTACKERS", "DECLARE_BLOCKERS", "COMBAT_DAMAGE", "END_COMBAT",
    # Second Main Phase (CR 505)
    "POSTCOMBAT_MAIN",
    # Ending Phase (CR 512)
    "END", "CLEANUP"
]

# Steps that don't use the stack (CR 117.3a)
_NO_PRIORITY_STEPS = {"UNTAP", "CLEANUP"}
# Steps where players receive priority
_PRIORITY_STEPS = {"UPKEEP", "DRAW", "PRECOMBAT_MAIN", "BEGIN_COMBAT", "DECLARE_ATTACKERS", 
                   "DECLARE_BLOCKERS", "COMBAT_DAMAGE", "END_COMBAT", "POSTCOMBAT_MAIN", "END"}


# ---------------- Player State ----------------
@dataclass
class PlayerState:
    player_id: int
    name: str
    life: int = 40
    # Note: Simple mana counter for backwards compatibility - proper mana pool in mana_pool attribute
    library: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    battlefield: List[Permanent] = field(default_factory=list)
    graveyard: List[Card] = field(default_factory=list)
    exile: List[Card] = field(default_factory=list)
    command: List[Card] = field(default_factory=list)
    commander: Optional[Card] = None
    commander_tracker: CommanderTracker = field(default_factory=CommanderTracker)
    mana_pool: ManaPool = field(default_factory=ManaPool)

    def draw(self, n: int = 1):
        # Debug: Track if hands are unexpectedly empty
        if hasattr(self, '_debug_expected_hand_size'):
            expected = getattr(self, '_debug_expected_hand_size', 0)
            if len(self.hand) != expected:
                # Hand size debug check (debug print removed)
                pass
        
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def add_mana(self, amount: int):
        """Backwards compatibility - adds generic mana to pool."""
        self.mana_pool.add('C', amount)  # Add to generic colorless mana
        # Keep simple counter for backwards compatibility
        self.mana += amount

    def reset_mana(self):
        """Reset both simple mana counter and mana pool."""
        self.mana_pool.clear()
        self.mana = 0
    
    @property
    def total_mana(self) -> int:
        """Total mana available (for backwards compatibility)."""
        return sum(self.mana_pool.pool.values())

    def find_playable(self) -> List[Card]:
        playable: List[Card] = []
        for c in self.hand:
            if "Land" in c.types:
                playable.append(c)
            else:
                cost = c.mana_cost
                if c.is_commander:
                    cost += self.commander_tracker.tax_for(c.id)
                if cost <= self.mana:
                    playable.append(c)
        return playable


# ---------------- Game State ----------------
@dataclass
class GameState:
    players: List[PlayerState]
    active_player: int = 0
    phase_index: int = 0
    turn: int = 1
    stack: Stack = field(default_factory=Stack)
    land_played_this_turn: Dict[int, bool] = field(default_factory=dict)

    def __post_init__(self):
        if getattr(self.stack, "game", None) is None:
            self.stack.game = self

    # ---- Setup / Helpers ----
    def other_player(self, pid: int) -> int:
        return 1 - pid  # two-player assumption

    def setup(self):
        for p in self.players:
            random.shuffle(p.library)
            if p.commander:
                p.command.append(p.commander)
                p.commander.is_commander = True
            # Don't draw opening hands here - let the controller handle it at proper timing
            self.land_played_this_turn[p.player_id] = False

    @property
    def phase(self) -> str:
        return PHASES[self.phase_index]

    # ---- Turn / Phase Management ----
    def _start_new_turn(self):
        self.turn += 1
        self.active_player = self.other_player(self.active_player)
        for p in self.players:
            for perm in p.battlefield:
                perm.summoning_sick = False
            self.land_played_this_turn[p.player_id] = False

    def _perform_phase_actions(self, phase: str):
        if phase == "UNTAP":
            for perm in self.players[self.active_player].battlefield:
                perm.tapped = False
            self.players[self.active_player].reset_mana()
        elif phase == "UPKEEP":
            pass
        elif phase == "DRAW":
            self.players[self.active_player].draw(1)
        elif phase == "COMBAT_DAMAGE":
            # Damage already applied at declare (simplified model)
            pass
        elif phase == "CLEANUP":
            for p in self.players:
                for perm in p.battlefield:
                    if hasattr(perm, "damage"):
                        perm.damage = 0
                p.reset_mana()

    def next_phase(self):
        """
        Advance to next phase; automatically chain through non‑priority steps.
        Implements proper mana pool emptying per CR 106.4.
        """
        # Empty mana pools at end of current step/phase (CR 106.4)
        self._empty_all_mana_pools()
        
        while True:
            self.phase_index = (self.phase_index + 1) % len(PHASES)
            if self.phase_index == 0:
                self._start_new_turn()
            phase = self.phase
            self._perform_phase_actions(phase)
            # Continue through steps that don't use priority (CR 117.3a)
            if phase in _NO_PRIORITY_STEPS:
                continue
            break
    
    def _empty_all_mana_pools(self):
        """Empty all players' mana pools (CR 106.4)."""
        for player in self.players:
            player.mana_pool.empty_pool()

    def ensure_progress(self):
        if self.phase in _NO_PRIORITY_STEPS:
            self.next_phase()

    # ---- Core Actions ----
    def play_land(self, pid: int, card: Card) -> ActionResult:
        if self.land_played_this_turn.get(pid, False):
            return ActionResult.ILLEGAL
        if "Land" not in card.types:
            return ActionResult.ILLEGAL
        ps = self.players[pid]
        if card not in ps.hand:
            return ActionResult.ILLEGAL
        ps.hand.remove(card)
        ps.battlefield.append(Permanent(card=card, summoning_sick=False))
        self.land_played_this_turn[pid] = True
        return ActionResult.OK

    def tap_for_mana(self, pid: int, perm: Permanent):
        if "Land" in perm.card.types and not perm.tapped:
            perm.tapped = True
            self.players[pid].add_mana(1)

    def _pay_and_move_to_battlefield(self, ps: PlayerState, card: Card, total_cost: int) -> ActionResult:
        if total_cost > ps.mana:
            return ActionResult.ILLEGAL
        ps.mana -= total_cost
        ps.battlefield.append(Permanent(card=card))
        return ActionResult.OK

    def cast_spell(self, pid: int, card: Card) -> ActionResult:
        ps = self.players[pid]

        # Commander from command zone
        if card.is_commander and card in ps.command:
            total_cost = card.mana_cost + ps.commander_tracker.tax_for(card.id)
            res = self._pay_and_move_to_battlefield(ps, card, total_cost)
            if res == ActionResult.OK:
                ps.command.remove(card)
                ps.commander_tracker.note_cast(card.id)
            return res

        if card not in ps.hand or "Land" in card.types:
            return ActionResult.ILLEGAL

        if "Creature" in card.types:
            return (self._pay_and_move_to_battlefield(ps, card, card.mana_cost)
                    if card.mana_cost <= ps.mana else ActionResult.ILLEGAL)

        if "Sorcery" in card.types:
            if card.mana_cost > ps.mana:
                return ActionResult.ILLEGAL
            ps.mana -= card.mana_cost
            ps.hand.remove(card)

            def effect(game: GameState, item: StackItem):
                if "Draw 2" in card.text:
                    ps.draw(2)
                if "Deal 3" in card.text:
                    opp = game.players[game.other_player(pid)]
                    opp.life -= 3
                ps.graveyard.append(card)

            self.stack.push(StackItem(source_card=card, effect=effect, controller_id=pid))
            return ActionResult.OK

        return ActionResult.ILLEGAL

    def declare_attackers(self, pid: int):
        """
        Simplified combat: all eligible creatures attack; total damage applied immediately.
        """
        ps = self.players[pid]
        attackers: List[Permanent] = [
            perm for perm in ps.battlefield
            if "Creature" in perm.card.types and not perm.tapped and not perm.summoning_sick
        ]
        if not attackers:
            return
        defender = self.players[self.other_player(pid)]
        total = 0
        for perm in attackers:
            power = max(0, perm.card.power or 0)
            total += power
            if perm.card.is_commander and power > 0:
                ps.commander_tracker.add_damage(defender.player_id, ps.player_id, power)
            perm.tapped = True
        defender.life -= total

    def check_game_over(self) -> bool:
        if any(p.life <= 0 for p in self.players):
            return True
        for defender in self.players:
            attacker_owner = self.other_player(defender.player_id)
            if self.players[attacker_owner].commander_tracker.lethal_from(defender.player_id, attacker_owner):
                return True
        return False
