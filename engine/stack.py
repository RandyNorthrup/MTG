from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState  # forward ref

@dataclass
class StackItem:
    # Unified / compatible fields
    source: Any = None
    source_card: Any = None          # legacy name used in game_state.cast_spell
    controller: Optional[int] = None
    controller_id: Optional[int] = None  # legacy
    label: str = ""
    resolve_fn: Optional[Callable[['GameState', 'StackItem'], None]] = None
    effect: Optional[Callable[['GameState', 'StackItem'], None]] = None  # legacy
    targets: list[Any] = field(default_factory=list)

    def describe(self) -> str:
        src = self.source or self.source_card
        return f"{self.label or 'Item'} ({getattr(src,'name', type(src).__name__)})"

    def resolve(self, game: 'GameState'):
        fn = self.resolve_fn or self.effect
        if not fn:
            return
        fn(game, self)

class GameStack:
    def __init__(self, game: 'GameState' = None):  # CHANGED (game now optional)
        self.game = game
        self._items: List[StackItem] = []

    def push(self, item: StackItem):
        self._items.append(item)

    def can_resolve(self) -> bool:
        return bool(self._items)

    def resolve_top(self, game: 'GameState'):
        if not self._items:
            return
        item = self._items.pop()
        try:
            item.resolve(game)
        except Exception as ex:
            print(f"[STACK][ERR] {item.describe()} :: {ex}")

    def peek(self) -> Optional[StackItem]:
        return self._items[-1] if self._items else None

    def items(self) -> list[StackItem]:
        return list(self._items)

    def auto_resolve_if_trivial(self):
        if len(self._items) == 1 and self.game is not None:  # GUARD
            self.resolve_top(self.game)

# Backwards compatibility alias expected by existing GameState
Stack = GameStack
