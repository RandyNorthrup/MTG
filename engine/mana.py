import re
from collections import defaultdict
from typing import Dict

MANA_SYMBOL_RE = re.compile(r'\{([^}]+)\}')

COLOR_SYMBOLS = {'W','U','B','R','G'}
GENERIC_KEY = 'C'   # use 'C' bucket for generic/colorless pool
ALL_KEYS = COLOR_SYMBOLS | {GENERIC_KEY}

def parse_mana_cost(cost_str: str | None) -> Dict[str,int]:
    """
    Parse a Scryfall style mana cost string like '{2}{G}{G}' into a dict:
      {'generic':2,'G':2}  (we store generic under key GENERIC_KEY)
    Hybrid / phyrexian are simplified: each symbol counts as 1 of either involved color
    and is returned under a tuple-key placeholder we treat as generic fallback.
    If cost_str is None/empty returns {}.
    """
    if not cost_str:
        return {}
    result: Dict[str,int] = defaultdict(int)
    for sym in MANA_SYMBOL_RE.findall(cost_str):
        up = sym.upper()
        if up.isdigit():
            result[GENERIC_KEY] += int(up)
        elif up in COLOR_SYMBOLS:
            result[up] += 1
        elif up in ('X','Y','Z'):
            # variable cost: ignore (player pays 0 by default in this prototype)
            pass
        else:
            # Hybrid / phyrexian / snow etc -> treat as generic 1 for now
            result[GENERIC_KEY] += 1
    return dict(result)

class ManaPool:
    """
    Simple mana pool tracking colored & generic (colorless) mana.
    No phase auto-empty logic here (caller responsible).
    Advanced: tracks sources, handles land tapping, and supports strict payment for spells/abilities.
    """
    def __init__(self):
        self.pool: Dict[str,int] = {k:0 for k in ALL_KEYS}
        self.sources: Dict[str, list] = {k: [] for k in ALL_KEYS}  # Track which permanents produced mana

    def add(self, symbol: str, amount: int = 1, source=None):
        symbol = symbol.upper()
        if symbol not in ALL_KEYS:
            symbol = GENERIC_KEY
        self.pool[symbol] += amount
        if source:
            self.sources[symbol].extend([source] * amount)

    def can_pay(self, cost: Dict[str,int]) -> bool:
        # Check colored first; generic checked after computing surplus
        for c in COLOR_SYMBOLS:
            need = cost.get(c,0)
            if need and self.pool.get(c,0) < need:
                return False
        # Generic requirement
        generic_need = cost.get(GENERIC_KEY,0)
        if generic_need:
            total_generic_available = self.pool.get(GENERIC_KEY,0)
            # Surplus colored mana can cover generic
            surplus = 0
            for c in COLOR_SYMBOLS:
                have = self.pool.get(c,0)
                need = cost.get(c,0)
                if have > need:
                    surplus += have - need
            if total_generic_available + surplus < generic_need:
                return False
        return True

    def pay(self, cost: Dict[str,int]) -> bool:
        if not self.can_pay(cost):
            return False
        # Deduct colored
        for c in COLOR_SYMBOLS:
            need = cost.get(c,0)
            if need:
                self.pool[c] -= need
                # Remove sources for paid mana
                self.sources[c] = self.sources[c][need:]
        # Deduct generic: use generic first then surplus colored (arbitrary order)
        generic_need = cost.get(GENERIC_KEY,0)
        if generic_need:
            use = min(generic_need, self.pool[GENERIC_KEY])
            self.pool[GENERIC_KEY] -= use
            self.sources[GENERIC_KEY] = self.sources[GENERIC_KEY][use:]
            generic_need -= use
            if generic_need:
                # consume surplus colored
                for c in COLOR_SYMBOLS:
                    if generic_need <= 0: break
                    avail = self.pool[c]
                    take = min(avail, generic_need)
                    self.pool[c] -= take
                    self.sources[c] = self.sources[c][take:]
                    generic_need -= take
        return True

    def clear(self):
        """Empty the mana pool completely."""
        for k in self.pool:
            self.pool[k] = 0
            self.sources[k] = []
    
    def empty_pool(self):
        """Empty mana pool per CR 106.4 - happens at end of each step and phase."""
        # In a real implementation, this would trigger mana burn in older rules
        # Current rules: mana simply disappears
        if any(self.pool[k] > 0 for k in self.pool):
            self.clear()

    def tap_land_for_mana(self, land_perm, symbol: str):
        """
        Tap a land permanent for mana of the given symbol.
        Handles summoning sickness, checks if already tapped, and marks as tapped.
        Returns True if successful, False if not.
        """
        if getattr(land_perm, "tapped", False):
            return False
        # Optionally: check for summoning sickness, land type, etc.
        land_perm.tapped = True
        self.add(symbol, 1, source=land_perm)
        return True

    def autotap_for_cost(self, battlefield, cost: Dict[str,int]) -> bool:
        """
        Attempt to tap lands on the battlefield to produce the required mana for cost.
        Returns True if successful, False if not.
        """
        needed = cost.copy()
        # Tap colored first
        for color in COLOR_SYMBOLS:
            n = needed.get(color, 0)
            while n > 0:
                found = next((perm for perm in battlefield if hasattr(perm, "card") and
                              "Land" in getattr(perm.card, "types", []) and not getattr(perm, "tapped", False)
                              and color in perm.card.text), None)
                if not found:
                    break
                self.tap_land_for_mana(found, color)
                n -= 1
            needed[color] = n
        # Tap for generic
        generic = needed.get(GENERIC_KEY, 0)
        while generic > 0:
            found = next((perm for perm in battlefield if hasattr(perm, "card") and
                          "Land" in getattr(perm.card, "types", []) and not getattr(perm, "tapped", False)), None)
            if not found:
                break
            # Heuristic: try to tap for any color, prefer generic
            produced = None
            for color in COLOR_SYMBOLS:
                if color in found.card.text:
                    produced = color
                    break
            if not produced:
                produced = GENERIC_KEY
            self.tap_land_for_mana(found, produced)
            generic -= 1
        # After autotap, check if pool can pay
        return self.can_pay(cost)

    def cast_with_pool_and_lands(self, cost: Dict[str,int], battlefield) -> bool:
        """
        Try to pay cost using current pool, autotapping lands as needed.
        Returns True if successful, False if not.
        """
        if self.can_pay(cost):
            return self.pay(cost)
        # Try to autotap lands to fill pool
        if not self.autotap_for_cost(battlefield, cost):
            return False
        return self.pay(cost)

    def untap_all(self, battlefield):
        """
        Untap all permanents on battlefield (typically at start of turn).
        """
        for perm in battlefield:
            if hasattr(perm, "tapped"):
                perm.tapped = False

    def __repr__(self):
        return f"ManaPool({{ {', '.join(f'{k}:{v}' for k,v in self.pool.items() if v)}}})"
