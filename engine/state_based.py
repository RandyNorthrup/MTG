from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game_state import GameState

class StateBasedActionEngine:
    def __init__(self, game: 'GameState'):
        self.game = game

    def check(self) -> bool:
        changed = False
        # Lethal damage / 0 toughness
        for pl in self.game.players:
            new_bf = []
            for perm in getattr(pl, 'battlefield', []):
                card = getattr(perm, 'card', perm)
                if getattr(perm, 'damage', 0) >= getattr(card, 'toughness', 999999):
                    self._to_grave(pl, perm); changed = True; continue
                if getattr(card, 'toughness', 1) <= 0:
                    self._to_grave(pl, perm); changed = True; continue
                new_bf.append(perm)
            pl.battlefield = new_bf
            if pl.life <= 0 and not getattr(self.game, 'winner', None):
                self.game.winner = next((o for o in self.game.players if o is not pl), None)
                changed = True
        return changed

    def cleanup_eot(self):
        for pl in self.game.players:
            for perm in getattr(pl, 'battlefield', []):
                if hasattr(perm, 'damage'):
                    perm.damage = 0

    def _to_grave(self, player, perm):
        if hasattr(player, 'graveyard'):
            player.graveyard.append(getattr(perm, 'card', perm))
