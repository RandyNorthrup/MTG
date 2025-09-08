from typing import Set
from dataclasses import dataclass
import re

# --- Canonical MTG ability keywords (static/keyword abilities) ---
MTG_KEYWORD_ABILITIES = [
    "Flying", "First Strike", "Double Strike", "Deathtouch", "Defender", "Haste", "Hexproof",
    "Indestructible", "Lifelink", "Menace", "Prowess", "Reach", "Trample", "Vigilance", "Ward",
    "Augment", "Host", "Contraption", "Assemble", "Unstable", "Dice Rolling", "Sticker", "Attraction"
]

MTG_TRIGGERED_ABILITY_TEMPLATES = [
    "When", "Whenever", "At",
]

MTG_ACTIVATED_ABILITY_COSTS = [
    "{T}", "{Q}", "{C}", "{E}", "{S}", "{W}", "{U}", "{B}", "{R}", "{G}", "{X}", "{P}", "{2/W}", "{2/U}", "{2/B}", "{2/R}", "{2/G}",
]

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

@dataclass
class Ability:
    kind: str          # 'triggered' | 'static'
    raw_text: str

@dataclass
class TriggeredAbility(Ability):
    trigger: str       # e.g. 'ETB', 'ATTACK', 'CREATURE_ETB_YOU', 'DEATH'
    effect_text: str

@dataclass
class StaticKeywordAbility(Ability):
    keyword: str       # e.g. 'Flying','Trample','Deathtouch'

@dataclass
class ActivatedAbility(Ability):
    raw_cost: str              # original cost string before ':'
    mana_cost: dict            # parsed mana symbols dict
    tap_cost: bool             # requires {T}
    effect_text: str
    needs_target: bool
    target_hint: str | None    # e.g. 'creature', 'player', None

@dataclass
class StaticBuffAbility(Ability):
    other_only: bool
    power: int
    toughness: int

@dataclass
class TriggerEvent:
    source_card_id: str
    ability: Ability
    context: dict  # event related data (e.g. {'zone_from':'BATTLEFIELD'})

def is_keyword_ability(text: str) -> bool:
    return text.strip().split(" ", 1)[0].capitalize() in MTG_KEYWORD_ABILITIES

def is_static_ability(text: str) -> bool:
    t = text.strip()
    return (
        not is_triggered_ability(t)
        and not is_activated_ability(t)
        and not t.lower().startswith("as long as")
        and not t.lower().startswith("when")
        and not t.lower().startswith("whenever")
        and not t.lower().startswith("at")
    )

def is_triggered_ability(text: str) -> bool:
    t = text.strip().lower()
    return any(t.startswith(x.lower()) for x in MTG_TRIGGERED_ABILITY_TEMPLATES)

def is_activated_ability(text: str) -> bool:
    return ':' in text and (text.strip().startswith('{') or text.strip().split(':', 1)[0].strip().endswith('}'))

def parse_activated_cost(cost_text: str):
    mana_cost = {}
    tap_cost = False
    cost_parts = [c.strip() for c in cost_text.split(',')]
    for part in cost_parts:
        if '{T}' in part:
            tap_cost = True
        mana = re.findall(r'\{[WUBRG0-9X/]+\}', part)
        for m in mana:
            mana_cost[m.strip('{}')] = mana_cost.get(m.strip('{}'), 0) + 1
    return mana_cost, tap_cost

def parse_ability(text: str):
    t = text.strip()
    if is_keyword_ability(t):
        return StaticKeywordAbility(kind='static', raw_text=t, keyword=t.split(" ", 1)[0].capitalize())
    if is_triggered_ability(t):
        m = re.match(r'^(When|Whenever|At)\b([^,]*),\s*(.+)$', t, re.IGNORECASE)
        if m:
            trigger = m.group(2).strip().upper() if m.group(2) else m.group(1).upper()
            effect = m.group(3).strip()
        else:
            trigger = t.split(",")[0].strip().upper()
            effect = t[len(trigger):].strip()
        return TriggeredAbility(kind='triggered', raw_text=t, trigger=trigger, effect_text=effect)
    if is_activated_ability(t):
        cost, effect = t.split(':', 1)
        mana_cost, tap_cost = parse_activated_cost(cost)
        needs_target = "target" in effect.lower()
        target_hint = None
        m = re.search(r'target (\w+)', effect, re.IGNORECASE)
        if m:
            target_hint = m.group(1).lower()
        return ActivatedAbility(
            kind='activated',
            raw_text=t,
            raw_cost=cost.strip(),
            mana_cost=mana_cost,
            tap_cost=tap_cost,
            effect_text=effect.strip(),
            needs_target=needs_target,
            target_hint=target_hint
        )
    if is_static_ability(t):
        return Ability(kind='static', raw_text=t)
    return None

def match_ability_keyword(text: str):
    t = text.strip().split(" ", 1)[0].capitalize()
    return t if t in MTG_KEYWORD_ABILITIES else None

def match_triggered_template(text: str):
    t = text.strip().lower()
    for trig in MTG_TRIGGERED_ABILITY_TEMPLATES:
        if t.startswith(trig.lower()):
            return trig
    return None

ABILITY_HANDLER_REGISTRY = {}

def register_ability_handler(keyword: str, handler_fn):
    ABILITY_HANDLER_REGISTRY[keyword.lower()] = handler_fn

def get_ability_handler(keyword: str):
    return ABILITY_HANDLER_REGISTRY.get(keyword.lower())
