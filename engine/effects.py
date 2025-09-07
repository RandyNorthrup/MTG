from __future__ import annotations
from typing import List, Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from .game_state import GameState

class ContinuousEffect:
    def __init__(self, layer: int, fn, duration: str | None = None):
        self.layer = layer
        self.fn = fn
        self.duration = duration
        self.active = True

class EffectLayerSystem:
    def __init__(self, game: 'GameState'):
        self.game = game
        self.effects: list[ContinuousEffect] = []

    def add(self, eff: ContinuousEffect):
        self.effects.append(eff)

    def recompute(self):
        for eff in sorted([e for e in self.effects if e.active], key=lambda e: e.layer):
            try:
                eff.fn(self.game)
            except Exception as ex:
                print(f"[EFFECT][ERR] {ex}")

    def prune_eot(self):
        self.effects = [e for e in self.effects if not (e.duration == 'eot')]
