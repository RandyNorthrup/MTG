from typing import Set
from .ability import StaticKeywordAbility

# Canonical lowercase keyword names used in combat logic
_COMBAT_KEYWORDS = {
    'flying','reach','trample','deathtouch','lifelink','vigilance','haste','menace',
    'first strike','double strike'
}

def card_keywords(card) -> Set[str]:
    """
    Returns a lowercase set of keywords parsed for the card.
    (StaticKeywordAbility added during oracle parsing.)
    """
    kws: Set[str] = set()
    for ab in getattr(card, 'oracle_abilities', []) or []:
        if isinstance(ab, StaticKeywordAbility):
            k = ab.keyword.lower()
            if k in _COMBAT_KEYWORDS:
                kws.add(k)
    return kws
