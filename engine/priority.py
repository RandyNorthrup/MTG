from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game_state import GameState


class PriorityManager:
    def __init__(self, game: 'GameState'):
        self.game = game

    def auto_pass_if_ai(self):
        # Placeholder: no full priority cycle; extend later
        pass
