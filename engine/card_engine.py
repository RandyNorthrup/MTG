from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Card:
    id: str
    name: str
    types: List[str]
    mana_cost: int
    power: Optional[int] = None
    toughness: Optional[int] = None
    text: str = ""
    is_commander: bool = False
    color_identity: List[str] = field(default_factory=list)
    owner_id: int = -1
    controller_id: int = -1
    
    #def __hash__(self) -> int:
        #return hash(self.id)

    def is_type(self, t):
        return t in self.types

@dataclass
class Permanent:
    card: Card
    summoning_sick: bool = True
    tapped: bool = False

class Zones:
    LIBRARY = "library"
    HAND = "hand"
    BATTLEFIELD = "battlefield"
    GRAVEYARD = "graveyard"
    EXILE = "exile"
    COMMAND = "command"

class ActionResult:
    OK = "OK"
    ILLEGAL = "ILLEGAL"
