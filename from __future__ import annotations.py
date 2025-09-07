from __future__ import annotations
from typing import TYPE_CHECKING, List, Set
if TYPE_CHECKING:
    from .game_state import GameState

class StateBasedActionEngine:
    """
    Minimal SBA processor:
      - Players at life <= 0 lose.
      - Player flagged _drew_from_empty loses (set where draw-from-empty occurred).
      - Cleans up dead creatures (toughness <=0) and destroys if lethal damage marked.
    Extend as engine grows (poison, commander damage, etc.).
    """
    @staticmethod
    def run(game: 'GameState'):
        eliminated: Set[int] = set()
        # Player checks
        for pl in list(game.players):
            try:
                if pl.life <= 0 or getattr(pl, '_drew_from_empty', False):
                    eliminated.add(pl.player_id)
            except Exception:
                continue
        for pid in sorted(eliminated):
            try:
                game.player_lost(pid, reason="STATE_BASED")
            except Exception:
                pass
        # Permanent / creature lethality
        try:
            battlefield = []
            for p in game.players:
                battlefield.extend(getattr(p, 'battlefield', []))
            to_grave = []
            for perm in battlefield:
                card = getattr(perm, 'card', None)
                if not card:
                    continue
                # damage lethal
                dmg = getattr(perm, 'damage', 0)
                tou = getattr(card, 'toughness', None)
                if isinstance(tou, int):
                    if tou <= 0:
                        to_grave.append(perm)
                        continue
                    if dmg >= tou:
                        to_grave.append(perm)
            for perm in to_grave:
                try:
                    game.destroy_permanent(perm)
                except Exception:
                    pass
        except Exception:
            pass
