from __future__ import annotations
from collections import defaultdict
from typing import Callable, Dict, List, Tuple

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
