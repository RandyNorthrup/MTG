from dataclasses import dataclass
import re

# --- Canonical MTG ability keywords (static/keyword abilities) ---
MTG_KEYWORD_ABILITIES = [
    # Evergreen
    "Flying", "First Strike", "Double Strike", "Deathtouch", "Defender", "Haste", "Hexproof",
    "Indestructible", "Lifelink", "Menace", "Prowess", "Reach", "Trample", "Vigilance", "Ward",
    # Deciduous/recurring
    "Flash", "Protection", "Shroud", "Fear", "Intimidate", "Landwalk", "Rampage", "Flanking",
    "Bushido", "Horsemanship", "Shadow", "Banding", "Cumulative Upkeep", "Echo", "Fading",
    "Phasing", "Vanishing", "Persist", "Undying", "Wither", "Infect", "Modular", "Graft",
    "Provoke", "Buyback", "Cycling", "Madness", "Morph", "Megamorph", "Bestow", "Dash",
    "Afterlife", "Afflict", "Affinity", "Amplify", "Annihilator", "Ascend", "Assist", "Awaken",
    "Backup", "Battalion", "Bloodthirst", "Boast", "Cascade", "Champion", "Changeling",
    "Cipher", "Convoke", "Crew", "Dethrone", "Devour", "Disturb", "Double Agenda", "Encore",
    "Entwine", "Epic", "Evolve", "Evoke", "Exploit", "Extort", "Fabricate", "Fateful Hour",
    "Ferocious", "Flashback", "Forecast", "Fortify", "Frenzy", "Goad", "Gravestorm", "Haunt",
    "Hellbent", "Heroic", "Hideaway", "Improvise", "Incubate", "Jump-Start", "Kicker",
    "Landfall", "Level Up", "Living Weapon", "Madness", "Miracle", "Modular", "Monstrosity",
    "Mutate", "Ninjutsu", "Offering", "Overload", "Persist", "Poisonous", "Proliferate",
    "Prototype", "Prowl", "Rally", "Rebound", "Recover", "Reinforce", "Renown", "Replicate",
    "Retrace", "Ripple", "Scavenge", "Scry", "Shadow", "Soulbond", "Spectacle", "Split Second",
    "Storm", "Sunburst", "Surveil", "Suspend", "Totem Armor", "Transfigure", "Transmute",
    "Undying", "Unearth", "Unleash", "Vigilance", "Wither", "Adventure", "Companion",
    "Escape", "Foretell", "Mutate", "Partner", "Encore", "Daybound", "Nightbound", "Ward",
    "Disturb", "Cleave", "Training", "Read Ahead", "Enlist", "Casualty", "Blitz", "Backup",
    "Incubate", "Bargain", "Craft", "Finality", "Toxic", "Corrupted", "Battle Cry", "Myriad",
    "Surge", "Support", "Escalate", "Emerge", "Fabricate", "Revolt", "Aftermath", "Embalm",
    "Eternalize", "Ascend", "Assist", "Jump-Start", "Mentor", "Spectacle", "Afterlife",
    "Amass", "Proliferate", "Mutate", "Companion", "Escape", "Foretell", "Boast", "Encore",
    "Demonstrate", "Daybound", "Nightbound", "Cleave", "Training", "Read Ahead", "Enlist",
    "Casualty", "Blitz", "Backup", "Incubate", "Bargain", "Craft", "Finality", "Toxic",
    "Corrupted", "Bargain", "Discover", "Map", "Role", "Celebration", "Descend", "Fateful Hour",
    "Ferocious", "Formidable", "Parley", "Tempting Offer", "Undaunted", "Will of the Council",
    # Planeswalker/other
    "Loyalty", "Saga", "Transform", "Flip", "Adventure", "Companion", "Mutate", "Daybound", "Nightbound",
    # Un-sets and silver-bordered (optional, for completeness)
    "Augment", "Host", "Contraption", "Assemble", "Unstable", "Dice Rolling", "Sticker", "Attraction"
]

# --- Canonical triggered ability templates (for parsing/validation) ---
MTG_TRIGGERED_ABILITY_TEMPLATES = [
    "When", "Whenever", "At",  # e.g. "When this enters...", "Whenever you cast...", "At the beginning of..."
    # Common triggers:
    "ETB", "LEAVE_BATTLEFIELD", "ATTACK", "BLOCK", "DAMAGE", "DEATH", "UPKEEP", "DRAW", "DISCARD",
    "CAST", "CYCLE", "SACRIFICE", "DESTROYED", "EXILE", "COUNTER", "MILL", "GAIN_LIFE", "LOSE_LIFE",
    "PAY_LIFE", "LIFE_TOTAL", "WIN", "LOSE", "CREATE_TOKEN", "MOVE_ZONE", "REVEAL", "SCRY", "SURVEIL",
    "PROLIFERATE", "TRANSFORM", "MUTATE", "ADVENTURE", "COMPANION", "ESCAPE", "FORETELL", "BOAST",
    "ENCORE", "DAYBOUND", "NIGHTBOUND", "ROLE", "CELEBRATION", "DESCEND", "FATEFUL_HOUR", "FEROCIOUS",
    "FORMIDABLE", "PARLEY", "TEMPTING_OFFER", "UNDAUNTED", "WILL_OF_COUNCIL"
]

# --- Canonical activated ability cost symbols (for parsing/validation) ---
MTG_ACTIVATED_ABILITY_COSTS = [
    "{T}", "{Q}", "{C}", "{E}", "{S}", "{W}", "{U}", "{B}", "{R}", "{G}", "{X}", "{P}", "{2/W}", "{2/U}", "{2/B}", "{2/R}", "{2/G}",
    # Hybrid, Phyrexian, snow, etc.
]

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

# --- Advanced ability logic ---

def is_keyword_ability(text: str) -> bool:
    """Check if the text matches a canonical keyword ability."""
    return text.strip().split(" ", 1)[0].capitalize() in MTG_KEYWORD_ABILITIES

def is_static_ability(text: str) -> bool:
    """Heuristic: static abilities are statements, not triggers or activations."""
    t = text.strip()
    return (
        not is_triggered_ability(t)
        and not is_activated_ability(t)
        and not t.lower().startswith("as long as")  # handled as static but not a keyword
        and not t.lower().startswith("when")
        and not t.lower().startswith("whenever")
        and not t.lower().startswith("at")
    )

def is_triggered_ability(text: str) -> bool:
    """Check if the text starts with a triggered template."""
    t = text.strip().lower()
    return any(t.startswith(x.lower()) for x in MTG_TRIGGERED_ABILITY_TEMPLATES)

def is_activated_ability(text: str) -> bool:
    """Check if the text looks like an activated ability (cost: effect)."""
    return ':' in text and (text.strip().startswith('{') or text.strip().split(':', 1)[0].strip().endswith('}'))

def parse_activated_cost(cost_text: str):
    """Parse the cost part of an activated ability."""
    # Example: "{1}{G}, {T}, Discard a card:"
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
    """
    Parse a raw ability text into the appropriate Ability dataclass.
    Returns an Ability instance or None if not recognized.
    """
    t = text.strip()
    # Keyword/static
    if is_keyword_ability(t):
        return StaticKeywordAbility(kind='static', raw_text=t, keyword=t.split(" ", 1)[0].capitalize())
    # Triggered
    if is_triggered_ability(t):
        # Try to extract trigger and effect
        m = re.match(r'^(When|Whenever|At)\b([^,]*),\s*(.+)$', t, re.IGNORECASE)
        if m:
            trigger = m.group(2).strip().upper() if m.group(2) else m.group(1).upper()
            effect = m.group(3).strip()
        else:
            trigger = t.split(",")[0].strip().upper()
            effect = t[len(trigger):].strip()
        return TriggeredAbility(kind='triggered', raw_text=t, trigger=trigger, effect_text=effect)
    # Activated
    if is_activated_ability(t):
        cost, effect = t.split(':', 1)
        mana_cost, tap_cost = parse_activated_cost(cost)
        # Heuristic: needs_target if "target" in effect
        needs_target = "target" in effect.lower()
        # Heuristic: target_hint
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
    # Static (fallback)
    if is_static_ability(t):
        return Ability(kind='static', raw_text=t)
    return None

def match_ability_keyword(text: str):
    """Return the canonical keyword if present, else None."""
    t = text.strip().split(" ", 1)[0].capitalize()
    return t if t in MTG_KEYWORD_ABILITIES else None

def match_triggered_template(text: str):
    """Return the canonical trigger template if present, else None."""
    t = text.strip().lower()
    for trig in MTG_TRIGGERED_ABILITY_TEMPLATES:
        if t.startswith(trig.lower()):
            return trig
    return None

# --- Ability handler registry for custom/complex logic ---
ABILITY_HANDLER_REGISTRY = {}

def register_ability_handler(keyword: str, handler_fn):
    """Register a custom handler for a keyword or ability name."""
    ABILITY_HANDLER_REGISTRY[keyword.lower()] = handler_fn

def get_ability_handler(keyword: str):
    """Get a registered handler for a keyword or ability name."""
    return ABILITY_HANDLER_REGISTRY.get(keyword.lower())
