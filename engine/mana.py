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
    """
    def __init__(self):
        self.pool: Dict[str,int] = {k:0 for k in ALL_KEYS}

    def add(self, symbol: str, amount: int = 1):
        symbol = symbol.upper()
        if symbol not in ALL_KEYS:
            symbol = GENERIC_KEY
        self.pool[symbol] += amount

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
        # Deduct generic: use generic first then surplus colored (arbitrary order)
        generic_need = cost.get(GENERIC_KEY,0)
        if generic_need:
            use = min(generic_need, self.pool[GENERIC_KEY])
            self.pool[GENERIC_KEY] -= use
            generic_need -= use
            if generic_need:
                # consume surplus colored
                for c in COLOR_SYMBOLS:
                    if generic_need <= 0: break
                    avail = self.pool[c]
                    if avail > 0:
                        take = min(avail, generic_need)
                        self.pool[c] -= take
                        generic_need -= take
        return True

    def clear(self):
        for k in self.pool:
            self.pool[k] = 0

    def __repr__(self):
        return f"ManaPool({{ {', '.join(f'{k}:{v}' for k,v in self.pool.items() if v)}}})"
