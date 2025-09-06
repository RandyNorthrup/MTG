from dataclasses import dataclass, field
from typing import Dict, Tuple

@dataclass
class CommanderTracker:
    # Track casts per commander by the CARD'S STRING ID (UUID)
    cast_counts: Dict[str, int] = field(default_factory=dict)
    # Track commander combat damage by (defender_pid, commander_owner_pid)
    damage: Dict[Tuple[int, int], int] = field(default_factory=dict)

    def tax_for(self, commander_card_id: str) -> int:
        """+2 generic per previous cast of THIS commander from the command zone."""
        return 2 * self.cast_counts.get(commander_card_id, 0)

    def note_cast(self, commander_card_id: str) -> None:
        self.cast_counts[commander_card_id] = self.cast_counts.get(commander_card_id, 0) + 1

    def add_damage(self, defender_pid: int, commander_owner_id: int, amount: int) -> None:
        k = (defender_pid, commander_owner_id)
        self.damage[k] = self.damage.get(k, 0) + amount

    def lethal_from(self, defender_pid: int, commander_owner_id: int) -> bool:
        # 21+ combat damage from the same commander
        return self.damage.get((defender_pid, commander_owner_id), 0) >= 21
