# rules/commander_validator.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set

@dataclass
class DeckIssue:
    code: str
    message: str
    card_names: Optional[List[str]] = None

@dataclass
class DeckReport:
    legal: bool
    issues: List[DeckIssue]
    commander_identity: Set[str]

BANNED_CARDS: Set[str] = {
    # From your CCMDR ruleset banned list (sample; extend as needed)
    "Ancestral Recall","Balance","Biorhythm","Black Lotus","Channel","Emrakul, the Aeons Torn",
    "Erayo, Soratami Ascendant","Fastbond","Gleemox","Griselbrand","Iona, Shield of Emeria","Karakas",
    "Leovold, Emissary of Trest","Library of Alexandria","Limited Resources","Mox Emerald","Mox Jet",
    "Mox Pearl","Mox Ruby","Mox Sapphire","Paradox Engine","Primeval Titan","Prophet of Kruphix",
    "Recurring Nightmare","Rofellos, Llanowar Emissary","Sundering Titan","Sylvan Primordial",
    "Time Vault","Time Walk","Tinker","Tolarian Academy","Trade Secrets","Upheaval","Golos, Tireless Pilgrim",
    "Yawgmoth's Bargain","Lutri, the Spellchaser","Flash","Distant Memories","Cleanse","Crusade",
    "Invoke Prejudice","Imprison","Jihad","Pradesh Gypsies","Stone-Throwing Devils","Hullbreacher",
    "Dockside Extortionist","Mana Crypt","Jeweled Lotus","Nadu, Winged Wisdom"
}

BASIC_NAMES = {"Plains","Island","Swamp","Mountain","Forest","Wastes"}

def color_identity_from_card(c: dict) -> Set[str]:
    return set(c.get("color_identity", []))

def is_basic_land(c: dict) -> bool:
    return "Land" in c.get("types", []) and c.get("name") in BASIC_NAMES

def is_legendary_commander_candidate(c: dict) -> bool:
    # Minimal implementation: legendary creature OR has explicit commander flag from DB
    types = set(c.get("types", []))
    if c.get("is_legendary") or "Legendary" in c.get("supertypes", []):
        if "Creature" in types:
            return True
    return bool(c.get("can_be_used_as_commander"))

def validate_commander_deck(deck_cards: List[dict], commander_cards: List[dict]) -> DeckReport:
    issues: List[DeckIssue] = []

    # — Deck size: exactly 100 including commander — CR 903.5a
    total_count = len(deck_cards) + len(commander_cards)
    if total_count != 100:
        issues.append(DeckIssue("SIZE", f"Commander decks must contain exactly 100 cards including commander(s); found {total_count}."))

    # — Commander presence & validity — CR 903.6, CCMDR schema “Must be legendary creature or can be used as commander”
    if not commander_cards:
        issues.append(DeckIssue("NO_COMMANDER", "A commander is required."))
        return DeckReport(False, issues, set())

    for cmd in commander_cards:
        if not is_legendary_commander_candidate(cmd):
            issues.append(DeckIssue("INVALID_COMMANDER", f"Commander must be a legendary creature or an allowed commander: {cmd.get('name')}"))

    # Commander color identity — CR 903.5c
    identity: Set[str] = set()
    for cmd in commander_cards:
        identity |= color_identity_from_card(cmd)

    # Singleton rule (except basics) — CR 903.5b
    name_counts: Dict[str, int] = {}
    for c in deck_cards:
        nm = c.get("name")
        if not is_basic_land(c):
            name_counts[nm] = name_counts.get(nm, 0) + 1
    dups = [n for (n, ct) in name_counts.items() if ct > 1]
    if dups:
        issues.append(DeckIssue("SINGLETON", "Deck must be singleton except basic lands.", dups))

    # Color identity subset & basic land types — CR 903.5c / 903.5d
    invalid_by_ci: List[str] = []
    for c in deck_cards:
        ci = color_identity_from_card(c)
        if not ci.issubset(identity):
            invalid_by_ci.append(c.get("name"))
    if invalid_by_ci:
        issues.append(DeckIssue("COLOR_IDENTITY", "Cards must be within commander color identity.", invalid_by_ci))

    # Banned list (from CCMDR) — show as not legal
    banned_present = [c.get("name") for c in deck_cards + commander_cards if c.get("name") in BANNED_CARDS]
    if banned_present:
        issues.append(DeckIssue("BANNED", "Deck contains cards banned in Commander.", banned_present))

    legal = len(issues) == 0
    return DeckReport(legal, issues, identity)
