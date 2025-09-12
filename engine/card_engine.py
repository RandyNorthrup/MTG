from dataclasses import dataclass, field
from typing import List, Optional, Dict
import re

@dataclass
class Card:
    id: str
    name: str
    types: List[str]
    mana_cost: int
    power: Optional[int] = None
    toughness: Optional[int] = None
    text: str = ""
    mana_cost_str: str = ""  # ADDED: string representation of mana cost
    is_commander: bool = False
    color_identity: List[str] = field(default_factory=list)
    owner_id: int = -1
    controller_id: int = -1
    # Note: Only permanents can be tapped per CR 400.3 - tap state moved to Permanent class
    orientation: int = 0  # UI rotation (0 = untapped, 45 = tapped, 90 = untapped)

    #def __hash__(self) -> int:
        #return hash(self.id)

    def is_type(self, t):
        return t in self.types

    def set_orientation(self, degrees: int):
        """Set UI orientation for visual feedback only."""
        self.orientation = degrees

@dataclass
class Permanent:
    """Represents a permanent on the battlefield (CR 110.1)"""
    card: Card
    summoning_sick: bool = True  # CR 302.6 - creatures have summoning sickness
    tapped: bool = False  # CR 106.8 - only permanents can be tapped
    damage_marked: int = 0  # CR 120.3 - damage marked on permanent
    
    def tap(self):
        """Tap this permanent (CR 701.21a)."""
        if self.can_be_tapped():
            self.tapped = True
            self.card.set_orientation(45)  # UI feedback

    def untap(self):
        """Untap this permanent (CR 701.21b)."""
        self.tapped = False
        self.card.set_orientation(0)  # UI feedback

    def is_tapped(self):
        """Return True if this permanent is tapped."""
        return self.tapped
    
    def can_be_tapped(self):
        """Return True if this permanent can be tapped."""
        return not self.tapped
    
    def can_tap_for_mana(self):
        """Return True if this land can be tapped for mana."""
        return (self.card.is_type("Land") and 
                not self.tapped and 
                not (self.summoning_sick and not self.card.is_type("Land")))
    
    def can_attack(self):
        """Return True if this creature can attack (CR 508.1)."""
        return (self.card.is_type("Creature") and 
                not self.tapped and 
                not self.summoning_sick)

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

# --- Advanced mana cost and card logic ---

MANA_SYMBOL_RE = re.compile(r"\{([WUBRGX0-9/PSC]+)\}")

def parse_mana_cost_str(cost_str: str) -> Dict[str, int]:
    """
    Parse a mana cost string like '{2}{U}{U/P}{R/W}' into a dict of symbol->count.
    Supports hybrid, phyrexian, snow, X, etc.
    """
    cost = {}
    if not cost_str:
        return cost
    for sym in MANA_SYMBOL_RE.findall(cost_str):
        sym = sym.upper()
        cost[sym] = cost.get(sym, 0) + 1
    return cost

def mana_cost_to_cmc(cost_str: str) -> int:
    """
    Compute converted mana cost (CMC, now called mana value) from a cost string.
    """
    total = 0
    for sym in MANA_SYMBOL_RE.findall(cost_str):
        if sym.isdigit():
            total += int(sym)
        elif sym == "X":
            # X is 0 except on stack (handled elsewhere)
            total += 0
        else:
            total += 1
    return total

def can_pay_mana_cost(pool: Dict[str, int], cost: Dict[str, int]) -> bool:
    """
    Check if the given mana pool can pay the cost dict.
    Supports hybrid, phyrexian, snow, etc.
    """
    pool = pool.copy()
    for sym, need in cost.items():
        if sym in ("W", "U", "B", "R", "G", "C", "S"):
            if pool.get(sym, 0) < need:
                return False
            pool[sym] -= need
        elif sym.isdigit():
            # generic
            avail = sum(pool.values())
            if avail < int(sym):
                return False
            # Remove generic from any available
            n = int(sym)
            for k in list(pool.keys()):
                take = min(pool[k], n)
                pool[k] -= take
                n -= take
                if n == 0:
                    break
        elif "/" in sym:
            # hybrid or phyrexian
            opts = sym.split("/")
            paid = False
            for o in opts:
                if pool.get(o, 0) > 0:
                    pool[o] -= 1
                    paid = True
                    break
            if not paid:
                # For phyrexian, allow life payment (not modeled here)
                if "P" in opts:
                    paid = True  # Assume can pay life
            if not paid:
                return False
        elif sym == "X":
            # X must be set by caller
            continue
        else:
            # Unknown symbol
            return False
    return True

def pay_mana_cost(pool: Dict[str, int], cost: Dict[str, int]) -> bool:
    """
    Remove mana from pool to pay cost. Returns True if successful, else False.
    """
    if not can_pay_mana_cost(pool, cost):
        return False
    # Actually remove mana (same logic as can_pay_mana_cost)
    pool = pool.copy()
    for sym, need in cost.items():
        if sym in ("W", "U", "B", "R", "G", "C", "S"):
            pool[sym] -= need
        elif sym.isdigit():
            n = int(sym)
            for k in list(pool.keys()):
                take = min(pool[k], n)
                pool[k] -= take
                n -= take
                if n == 0:
                    break
        elif "/" in sym:
            opts = sym.split("/")
            paid = False
            for o in opts:
                if pool.get(o, 0) > 0:
                    pool[o] -= 1
                    paid = True
                    break
            if not paid and "P" in opts:
                paid = True  # Assume can pay life
            if not paid:
                return False
        elif sym == "X":
            continue
        else:
            return False
    return True

def get_color_identity(card: "Card") -> List[str]:
    """
    Compute the color identity of a card (for Commander).
    Includes all mana symbols in cost and rules text.
    """
    colors = set()
    # Mana cost
    if hasattr(card, "mana_cost_str"):
        for sym in MANA_SYMBOL_RE.findall(card.mana_cost_str):
            for c in sym:
                if c in "WUBRG":
                    colors.add(c)
    # Oracle text
    for sym in MANA_SYMBOL_RE.findall(card.text):
        for c in sym:
            if c in "WUBRG":
                colors.add(c)
    # Color indicator (if present)
    if hasattr(card, "color_indicator"):
        for c in card.color_indicator:
            if c in "WUBRG":
                colors.add(c)
    return sorted(colors)

def is_type(card: "Card", type_name: str) -> bool:
    """Check if card is of a given type (case-insensitive)."""
    return any(type_name.lower() == t.lower() for t in card.types)

def has_supertype(card: "Card", supertype: str) -> bool:
    """Check if card has a given supertype (e.g. 'Legendary')."""
    # Supertypes are not always in types, but may be stored elsewhere
    if hasattr(card, "supertypes"):
        return supertype.lower() in (s.lower() for s in card.supertypes)
    # Fallback: check types for known supertypes
    return supertype.lower() in (t.lower() for t in card.types)

def is_permanent(card: "Card") -> bool:
    """Return True if card is a permanent type."""
    return any(t in ("Creature", "Artifact", "Enchantment", "Land", "Planeswalker", "Battle") for t in card.types)

def is_spell(card: "Card") -> bool:
    """Return True if card is a spell type (not permanent)."""
    return any(t in ("Instant", "Sorcery") for t in card.types)

def is_legendary(card: "Card") -> bool:
    """Return True if card is legendary."""
    return has_supertype(card, "Legendary")

def is_basic_land(card: "Card") -> bool:
    """Return True if card is a basic land."""
    return has_supertype(card, "Basic") and is_type(card, "Land")

def has_etb_trigger(card: "Card") -> bool:
    """
    Returns True if the card has an "enters the battlefield" triggered ability.
    """
    text = getattr(card, "text", "").lower()
    # Common ETB patterns
    return (
        "when" in text and "enters the battlefield" in text
        or "whenever" in text and "enters the battlefield" in text
        or "at the beginning of" in text and "enters the battlefield" in text
        or "as" in text and "enters the battlefield" in text
    )

def get_etb_triggers(card: "Card") -> list:
    """
    Returns a list of ETB triggered ability text blocks for the card.
    """
    import re
    text = getattr(card, "text", "")
    # Simple regex for ETB triggers
    etb_triggers = []
    pattern = re.compile(r"(When(?:ever)? [^\.]*enters the battlefield[^\.]*\.)", re.IGNORECASE)
    for match in pattern.findall(text):
        etb_triggers.append(match.strip())
    return etb_triggers

def get_triggered_abilities(card: "Card") -> list:
    """
    Returns a list of all triggered ability text blocks for the card.
    """
    import re
    text = getattr(card, "text", "")
    triggers = []
    # Match "When", "Whenever", or "At" triggers (not perfect, but covers most)
    pattern = re.compile(r"((When(?:ever)?|At) [^\.]+?\.)", re.IGNORECASE)
    for match in pattern.findall(text):
        triggers.append(match[0].strip())
    return triggers

def has_triggered_ability(card: "Card", trigger_keyword: str = None) -> bool:
    """
    Returns True if the card has any triggered ability, or one matching a keyword.
    """
    triggers = get_triggered_abilities(card)
    if not trigger_keyword:
        return bool(triggers)
    trigger_keyword = trigger_keyword.lower()
    return any(trigger_keyword in trig.lower() for trig in triggers)

def untap_all_for_player(player):
    """
    Untap all permanents for the given player at the beginning of their untap step.
    """
    for perm in getattr(player, "battlefield", []):
        if hasattr(perm, "untap"):
            perm.untap()
        elif hasattr(perm, "card") and hasattr(perm.card, "untap"):
            perm.card.untap()
