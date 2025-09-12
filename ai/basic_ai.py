"""Basic AI Player for MTG Commander Game.

Simple AI that makes fundamental gameplay decisions:
- Play lands when available
- Tap lands for mana
- Cast commander and creatures
- Play sorceries randomly
- Attack with all available creatures
"""

import random


class BasicAI:
    """Basic AI player implementation for MTG Commander.
    
    Provides simple but functional AI behavior for testing
    and single-player games. Makes decisions based on
    straightforward heuristics.
    """
    
    def __init__(self, pid: int):
        """Initialize AI player.
        
        Args:
            pid: Player ID this AI controls
        """
        self.pid = pid

    def take_turn(self, game, ui=None):
        """Execute AI turn with basic strategy.
        
        Strategy:
        1. Play a land if available and not played this turn
        2. Tap all untapped lands for mana
        3. Cast commander if in command zone
        4. Cast strongest creature available
        5. Cast random sorcery if available
        6. Attack with all creatures
        
        Args:
            game: GameState instance
            ui: Optional UI reference (unused)
        """
        player = game.players[self.pid]

        # 1. Play a land if available
        land = next((card for card in player.hand if "Land" in card.types), None)
        if land and not game.land_played_this_turn.get(self.pid, False):
            game.play_land(self.pid, land)

        # 2. Tap all available lands for mana
        for permanent in player.battlefield:
            if "Land" in permanent.card.types and not permanent.tapped:
                game.tap_for_mana(self.pid, permanent)

        # 3. Cast commander if available and not on battlefield
        commander_on_battlefield = player.commander in [
            perm.card for perm in player.battlefield
        ]
        if not commander_on_battlefield and player.commander in player.command:
            game.cast_spell(self.pid, player.commander)

        # 4. Cast strongest affordable creature
        affordable_creatures = [
            card for card in player.hand 
            if "Creature" in card.types and card.mana_cost <= player.mana
        ]
        if affordable_creatures:
            # Sort by power + toughness (descending)
            affordable_creatures.sort(
                key=lambda c: (c.power or 0) + (c.toughness or 0), 
                reverse=True
            )
            game.cast_spell(self.pid, affordable_creatures[0])

        # 5. Cast a random affordable sorcery
        affordable_sorceries = [
            card for card in player.hand 
            if "Sorcery" in card.types and card.mana_cost <= player.mana
        ]
        if affordable_sorceries:
            chosen_sorcery = random.choice(affordable_sorceries)
            game.cast_spell(self.pid, chosen_sorcery)

        # 6. Attack with all available creatures
        if not game.check_game_over():
            game.declare_attackers(self.pid)
