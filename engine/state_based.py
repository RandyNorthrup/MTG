from __future__ import annotations
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from .game_state import GameState

class StateBasedActionEngine:
    """
    Minimal state-based action processor:
      - Players with life <= 0 lose
      - Player forced to draw from empty library loses
      - (Stub) Commander damage check hook
    """
    @staticmethod
    def run(game: 'GameState'):
        to_eliminate: List[int] = []
        for pl in list(game.players):
            try:
                if pl.life <= 0:
                    to_eliminate.append(pl.player_id)
                if getattr(pl, '_drew_from_empty', False):
                    to_eliminate.append(pl.player_id)
                # Commander damage rule placeholder (903.10) – integrate when tracking implemented
            except Exception:
                continue
        if to_eliminate:
            for pid in sorted(set(to_eliminate), reverse=True):
                try:
                    game.player_lost(pid, reason="STATE_BASED")
                except Exception:
                    pass
                if hasattr(perm, 'damage'):
                    perm.damage = 0

    def _to_grave(self, player, perm):
        if hasattr(player, 'graveyard'):
            player.graveyard.append(getattr(perm, 'card', perm))
