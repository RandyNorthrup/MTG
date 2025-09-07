from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game_state import GameState

from .stack import GameStack
from .events import EventBus
from .state_based import StateBasedActionEngine
from .effects import EffectLayerSystem
from .priority import PriorityManager

class TurnManager:
    """
    Minimal orchestrator; does NOT mutate game.phase directly (avoids read-only issues).
    Extend with phase progression once underlying engine exposes safe API.
    """
    def __init__(self, game: 'GameState'):
        self.game = game
        if not hasattr(game, 'stack'):
            game.stack = GameStack(game)
        if not hasattr(game, 'events'):
            game.events = EventBus()
        if not hasattr(game, 'sba'):
            game.sba = StateBasedActionEngine(game)
        if not hasattr(game, 'layers'):
            game.layers = EffectLayerSystem(game)
        if not hasattr(game, 'priority'):
            game.priority = PriorityManager(game)

    def tick(self):
        try:
            self.game.sba.check()
        except Exception:
            pass
        try:
            self.game.events.process()
        except Exception:
            pass
        try:
            self.game.layers.recompute()
        except Exception:
            pass
        try:
            self.game.priority.auto_pass_if_ai()
        except Exception:
            pass
        try:
            if self.game.stack.can_resolve():
                self.game.stack.auto_resolve_if_trivial()
        except Exception:
            pass
