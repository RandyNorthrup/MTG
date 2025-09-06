import random

class BasicAI:
    def __init__(self, pid: int):
        self.pid = pid

    def take_turn(self, game, ui=None):
        ps = game.players[self.pid]

        land = next((c for c in ps.hand if "Land" in c.types), None)
        if land and not game.land_played_this_turn.get(self.pid, False):
            game.play_land(self.pid, land)

        for perm in ps.battlefield:
            if "Land" in perm.card.types and not perm.tapped:
                game.tap_for_mana(self.pid, perm)

        if ps.commander in [p.card for p in ps.battlefield]:
            pass
        else:
            if ps.commander in ps.command:
                game.cast_spell(self.pid, ps.commander)

        creatures = [c for c in ps.hand if "Creature" in c.types]
        creatures.sort(key=lambda c: (c.power or 0) + (c.toughness or 0), reverse=True)
        for c in creatures:
            if c.mana_cost <= ps.mana:
                game.cast_spell(self.pid, c)
                break

        sorcs = [c for c in ps.hand if "Sorcery" in c.types and c.mana_cost <= ps.mana]
        if sorcs:
            game.cast_spell(self.pid, random.choice(sorcs))

        if not game.check_game_over():
            game.declare_attackers(self.pid)
