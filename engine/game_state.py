from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .card_engine import Card, Permanent, Zones, ActionResult
from .stack import Stack, StackItem
from .commander_rules import CommanderTracker

PHASES = [
    "UNTAP", "UPKEEP", "DRAW",
    "MAIN1",
    "COMBAT_DECLARE", "COMBAT_DAMAGE",
    "MAIN2",
    "END"
]

@dataclass
class PlayerState:
    player_id: int
    name: str
    life: int = 40
    mana: int = 0

    library: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    battlefield: List[Permanent] = field(default_factory=list)
    graveyard: List[Card] = field(default_factory=list)
    exile: List[Card] = field(default_factory=list)

    command: List[Card] = field(default_factory=list)
    commander: Optional[Card] = None
    commander_tracker: CommanderTracker = field(default_factory=CommanderTracker)

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def add_mana(self, amount: int):
        self.mana += amount

    def reset_mana(self):
        self.mana = 0

    def find_playable(self) -> List[Card]:
        playable: List[Card] = []
        for c in self.hand:
            if "Land" in c.types:
                playable.append(c)
            else:
                total_cost = c.mana_cost
                if c.is_commander:
                    total_cost += self.commander_tracker.tax_for(c.id)  # id is str
                if total_cost <= self.mana:
                    playable.append(c)
        return playable


@dataclass
class GameState:
    players: List[PlayerState]
    active_player: int = 0
    phase_index: int = 0
    turn: int = 1
    stack: Stack = field(default_factory=Stack)
    land_played_this_turn: Dict[int, bool] = field(default_factory=dict)

    def other_player(self, pid: int) -> int:
        return 1 - pid

    def setup(self):
        for p in self.players:
            random.shuffle(p.library)
            if p.commander:
                p.command.append(p.commander)
                p.commander.is_commander = True
            p.draw(7)
            self.land_played_this_turn[p.player_id] = False

    @property
    def phase(self) -> str:
        return PHASES[self.phase_index]

    def next_phase(self):
        self.phase_index = (self.phase_index + 1) % len(PHASES)
        if self.phase_index == 0:
            self.turn += 1
            self.active_player = self.other_player(self.active_player)
            for p in self.players:
                for perm in p.battlefield:
                    perm.summoning_sick = False
                self.land_played_this_turn[p.player_id] = False

        if self.phase == "UNTAP":
            for perm in self.players[self.active_player].battlefield:
                perm.tapped = False
            self.players[self.active_player].reset_mana()
        elif self.phase == "DRAW":
            self.players[self.active_player].draw(1)

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

        # Cast commander from command zone
        if card.is_commander and card in ps.command:
            total_cost = card.mana_cost + ps.commander_tracker.tax_for(card.id)
            result = self._pay_and_move_to_battlefield(ps, card, total_cost)
            if result == ActionResult.OK:
                ps.command.remove(card)
                ps.commander_tracker.note_cast(card.id)
            return result

        # Regular spells from hand only
        if card not in ps.hand:
            return ActionResult.ILLEGAL

        if "Land" in card.types:
            return ActionResult.ILLEGAL  # lands are played, not cast

        if "Creature" in card.types:
            return self._pay_and_move_to_battlefield(ps, card, card.mana_cost) if card.mana_cost <= ps.mana else ActionResult.ILLEGAL

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
        ps = self.players[pid]
        attackers: List[Permanent] = []
        for perm in ps.battlefield:
            if "Creature" in perm.card.types and not perm.tapped and not perm.summoning_sick:
                attackers.append(perm)

        if attackers:
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
            attacker_owner_id = self.other_player(defender.player_id)
            if self.players[attacker_owner_id].commander_tracker.lethal_from(defender.player_id, attacker_owner_id):
                return True
        return False
