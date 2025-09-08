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

class StackEngine:
    def __init__(self, game, logging_enabled=False):
        self.game = game
        self.logging_enabled = logging_enabled
        self.stack = []  # Strict stack: list of stack objects (LIFO)
        self._stack_id_counter = 1  # Unique id for stack objects

    def add_to_stack(self, obj, obj_type: str, controller_id: int, targets=None, info=None):
        stack_obj = {
            "id": self._stack_id_counter,
            "type": obj_type,
            "obj": obj,
            "controller_id": controller_id,
            "targets": targets or [],
            "info": info or {},
        }
        self._stack_id_counter += 1
        self.stack.append(stack_obj)
        if self.logging_enabled:
            print(f"[STACK] + {obj_type.upper()} ({getattr(obj, 'name', getattr(obj, 'raw_text', repr(obj)))}) by P{controller_id} (targets: {targets})")
        return stack_obj["id"]

    def can_add_to_stack(self, obj, obj_type: str, controller_id: int, targets=None, info=None):
        # TODO: Implement strict timing, priority, and legality checks.
        return True

    def can_resolve(self):
        return bool(self.stack)

    def resolve_top(self):
        if not self.stack:
            return None
        stack_obj = self.stack.pop()
        obj_type = stack_obj["type"]
        obj = stack_obj["obj"]
        controller_id = stack_obj["controller_id"]
        targets = stack_obj["targets"]
        info = stack_obj["info"]
        if self.logging_enabled:
            print(f"[STACK] - Resolving {obj_type.upper()} ({getattr(obj, 'name', getattr(obj, 'raw_text', repr(obj)))}) by P{controller_id}")
        if obj_type == "spell":
            self._resolve_spell(obj, controller_id, targets, info)
        elif obj_type == "activated":
            self._resolve_activated_ability(obj, controller_id, targets, info)
        elif obj_type == "triggered":
            self._resolve_triggered_ability(obj, controller_id, targets, info)
        else:
            if self.logging_enabled:
                print(f"[STACK][WARN] Unknown stack object type: {obj_type}")
        self._after_stack_resolution()
        return stack_obj

    def _resolve_spell(self, card, controller_id, targets, info):
        if hasattr(card, "resolve"):
            card.resolve(self.game, controller_id, targets, info)
        else:
            if hasattr(self.game, "move_to_graveyard"):
                self.game.move_to_graveyard(card, controller_id)
        if self.logging_enabled:
            print(f"[STACK][SPELL] {getattr(card, 'name', repr(card))} resolved.")

    def _resolve_activated_ability(self, ability, controller_id, targets, info):
        if hasattr(ability, "resolve"):
            ability.resolve(self.game, controller_id, targets, info)
        if self.logging_enabled:
            print(f"[STACK][ACTIVATED] {getattr(ability, 'raw_text', repr(ability))} resolved.")

    def _resolve_triggered_ability(self, ability, controller_id, targets, info):
        if hasattr(ability, "resolve"):
            ability.resolve(self.game, controller_id, targets, info)
        if self.logging_enabled:
            print(f"[STACK][TRIGGERED] {getattr(ability, 'raw_text', repr(ability))} resolved.")

    def _after_stack_resolution(self):
        if hasattr(self.game, "check_state_based_actions"):
            self.game.check_state_based_actions()
        if hasattr(self.game, "check_triggers"):
            triggers = self.game.check_triggers()
            for trig in triggers:
                self.add_to_stack(trig["ability"], "triggered", trig["controller_id"], trig.get("targets"), trig.get("info"))

    def stack_size(self):
        return len(self.stack)

    def stack_top(self):
        return self.stack[-1] if self.stack else None

    def clear_stack(self):
        self.stack.clear()
        if self.logging_enabled:
            print("[STACK] Cleared.")

    def pass_priority(self, player_id: int):
        # For multiplayer, track priority order and pass count.
        # For now, assume two-player and resolve immediately if both pass.
        # TODO: Implement strict APNAP priority and multiplayer.
        if self.can_resolve():
            self.resolve_top()
        else:
            if self.logging_enabled:
                print("[STACK] All players passed, phase/step ends.")
