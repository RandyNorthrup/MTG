from __future__ import annotations
from collections import defaultdict
from typing import Callable, Dict, List, Tuple, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from .game_state import GameState

class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable[..., None]]] = defaultdict(list)
        self._queue: List[Tuple[str, dict]] = []

    def subscribe(self, event: str, cb: Callable[..., None]):
        self._subs[event].append(cb)

    def emit(self, event: str, **payload):
        self._queue.append((event, payload))

    def process(self, limit: int = 256):
        count = 0
        while self._queue and count < limit:
            evt, data = self._queue.pop(0)
            for cb in list(self._subs.get(evt, [])):
                try:
                    cb(**data)
                except Exception as ex:
                    print(f"[EVENT][{evt}][ERR] {ex}")
            count += 1

    # --- Advanced event helpers ---

    def emit_zone_change(self, card, from_zone: str, to_zone: str, player=None, info=None):
        """Emit a zone change event (e.g., for ETB, LTB, graveyard, exile, etc)."""
        self.emit("zone_change", card=card, from_zone=from_zone, to_zone=to_zone, player=player, info=info or {})
        # ETB/LTB triggers
        if to_zone == "battlefield":
            self.emit("etb", card=card, player=player, info=info or {})
        if from_zone == "battlefield":
            self.emit("ltb", card=card, player=player, info=info or {})

    def emit_card_flip(self, card, face_up: bool, player=None, info=None):
        """Emit a card flip event (for double-faced, morph, manifest, etc)."""
        self.emit("card_flip", card=card, face_up=face_up, player=player, info=info or {})
        # Optionally, trigger special logic for flip/transform
        if face_up:
            self.emit("card_face_up", card=card, player=player, info=info or {})
        else:
            self.emit("card_face_down", card=card, player=player, info=info or {})

    def emit_trigger(self, trigger_type: str, **kwargs):
        """Emit a generic trigger event (e.g., for abilities, custom triggers)."""
        self.emit(f"trigger_{trigger_type}", **kwargs)

    def subscribe_etb(self, cb: Callable[..., None]):
        """Subscribe to ETB (enters-the-battlefield) triggers."""
        self.subscribe("etb", cb)

    def subscribe_ltb(self, cb: Callable[..., None]):
        """Subscribe to LTB (leaves-the-battlefield) triggers."""
        self.subscribe("ltb", cb)

    def subscribe_zone_change(self, cb: Callable[..., None]):
        """Subscribe to any zone change event."""
        self.subscribe("zone_change", cb)

    def subscribe_card_flip(self, cb: Callable[..., None]):
        """Subscribe to card flip/transform events."""
        self.subscribe("card_flip", cb)

    def subscribe_trigger(self, trigger_type: str, cb: Callable[..., None]):
        """Subscribe to a custom trigger event."""
        self.subscribe(f"trigger_{trigger_type}", cb)

    # --- State-based actions (merged from state_based.py) ---
    @staticmethod
    def run_state_based(game: 'GameState'):
        """
        Minimal state-based action processor:
          - Players with life <= 0 lose
          - Player forced to draw from empty library loses
          - (Stub) Commander damage check hook
        """
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
                for p in list(game.battlefield):
                    if getattr(p, "destroy_me", False):
                        game.move_to_graveyard(p)
                    if getattr(p, "toughness", None) is not None and getattr(p, "damage", 0) >= p.toughness:
                        game.move_to_graveyard(p)

    def _to_grave(self, player, perm):
        if hasattr(player, 'graveyard'):
            player.graveyard.append(getattr(perm, 'card', perm))

    # --- Utility: clear all subscriptions (for test/reset) ---
    def clear(self):
        self._subs.clear()
        self._queue.clear()
