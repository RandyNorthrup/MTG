from typing import Dict
from .ability import StaticBuffAbility

class ContinuousEngine:
    """
    Applies simplified continuous effects (currently only StaticBuffAbility).
    Recompute after zone changes or at periodic ticks.
    """
    def __init__(self, game):
        self.game = game

    def recompute(self):
        # Clear previous effective stats
        for p in self.game.players:
            for perm in p.battlefield:
                card = getattr(perm, 'card', perm)
                if hasattr(card, 'eff_power'):
                    delattr(card, 'eff_power')
                if hasattr(card, 'eff_toughness'):
                    delattr(card, 'eff_toughness')

        # Collect buffs by source
        for p in self.game.players:
            for perm in p.battlefield:
                card = perm.card
                for ab in getattr(card, 'oracle_abilities', []) or []:
                    if isinstance(ab, StaticBuffAbility):
                        self._apply_buff(card, ab)

    def _apply_buff(self, source_card, buff: StaticBuffAbility):
        controller = source_card.controller_id
        for p in self.game.players:
            for perm in p.battlefield:
                c = perm.card
                if c.controller_id != controller:
                    continue
                if 'Creature' not in c.types:
                    continue
                if buff.other_only and c.id == source_card.id:
                    continue
                base_p = c.power if c.power is not None else 0
                base_t = c.toughness if c.toughness is not None else 0
                eff_p = getattr(c, 'eff_power', base_p)
                eff_t = getattr(c, 'eff_toughness', base_t)
                setattr(c, 'eff_power', eff_p + buff.power)
                setattr(c, 'eff_toughness', eff_t + buff.toughness)

def attach_continuous(game):
    if hasattr(game, 'continuous'):
        return game.continuous
    game.continuous = ContinuousEngine(game)
    game.continuous.recompute()
    return game.continuous
