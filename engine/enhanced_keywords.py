"""
Enhanced MTG Keywords and Ability Recognition System
Provides comprehensive support for all MTG keywords and their interactions
"""

from dataclasses import dataclass
from typing import Set, Dict, List, Optional, Tuple, Callable
from enum import Enum
import re

class KeywordCategory(Enum):
    """Categories of keyword abilities"""
    EVERGREEN = "evergreen"          # Always in Standard (Flying, Trample, etc.)
    DECIDUOUS = "deciduous"          # Appears occasionally (Scry, Mill, etc.)
    MECHANICS = "mechanics"          # Set-specific mechanics
    STATIC = "static"                # Static abilities
    TRIGGERED = "triggered"          # Triggered abilities
    ACTIVATED = "activated"          # Activated abilities

@dataclass
class KeywordDefinition:
    """Complete definition of a keyword ability"""
    name: str
    category: KeywordCategory
    reminder_text: str
    rules_text: str
    interaction_rules: Dict[str, str] = None
    parameter_type: Optional[str] = None  # For keywords with costs/numbers
    combat_relevant: bool = False
    stackable: bool = False  # Can multiple instances stack?

# Comprehensive MTG Keyword Database
MTG_KEYWORDS: Dict[str, KeywordDefinition] = {
    # Evergreen Keywords
    "flying": KeywordDefinition(
        name="Flying",
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature can't be blocked except by creatures with flying or reach.",
        rules_text="A creature with flying can't be blocked except by creatures with flying and/or reach.",
        combat_relevant=True,
        interaction_rules={"reach": "Creatures with reach can block creatures with flying."}
    ),
    "first strike": KeywordDefinition(
        name="First Strike", 
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature deals combat damage before creatures without first strike.",
        rules_text="A creature with first strike deals combat damage before creatures without first strike.",
        combat_relevant=True,
        interaction_rules={"double strike": "Double strike includes first strike."}
    ),
    "double strike": KeywordDefinition(
        name="Double Strike",
        category=KeywordCategory.EVERGREEN, 
        reminder_text="This creature deals first strike and regular combat damage.",
        rules_text="A creature with double strike deals both first-strike and regular combat damage.",
        combat_relevant=True,
        interaction_rules={"first strike": "Double strike includes first strike."}
    ),
    "deathtouch": KeywordDefinition(
        name="Deathtouch",
        category=KeywordCategory.EVERGREEN,
        reminder_text="Any amount of damage this deals to a creature is enough to destroy it.",
        rules_text="Any amount of damage a source with deathtouch deals to a creature is lethal damage.",
        combat_relevant=True,
        interaction_rules={"indestructible": "Deathtouch damage doesn't destroy indestructible creatures."}
    ),
    "defender": KeywordDefinition(
        name="Defender",
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature can't attack.",
        rules_text="A creature with defender can't attack.",
        combat_relevant=True
    ),
    "haste": KeywordDefinition(
        name="Haste",
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature can attack and tap as soon as it comes under your control.",
        rules_text="A creature with haste can attack even if it hasn't been under its controller's control since their most recent turn began.",
        combat_relevant=True
    ),
    "hexproof": KeywordDefinition(
        name="Hexproof",
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature can't be the target of spells or abilities your opponents control.",
        rules_text="A permanent or player with hexproof can't be the target of spells or abilities controlled by that permanent's or player's opponents."
    ),
    "indestructible": KeywordDefinition(
        name="Indestructible",
        category=KeywordCategory.EVERGREEN,
        reminder_text="Effects that say 'destroy' don't destroy this creature.",
        rules_text="A permanent with indestructible can't be destroyed by effects that say 'destroy' or by lethal damage.",
        interaction_rules={"deathtouch": "Deathtouch damage doesn't destroy indestructible permanents."}
    ),
    "lifelink": KeywordDefinition(
        name="Lifelink", 
        category=KeywordCategory.EVERGREEN,
        reminder_text="Damage dealt by this creature also causes you to gain that much life.",
        rules_text="Damage dealt by a source with lifelink causes that source's controller to gain that much life.",
        combat_relevant=True,
        stackable=True
    ),
    "menace": KeywordDefinition(
        name="Menace",
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature can't be blocked except by two or more creatures.",
        rules_text="A creature with menace can't be blocked except by two or more creatures.",
        combat_relevant=True
    ),
    "prowess": KeywordDefinition(
        name="Prowess",
        category=KeywordCategory.EVERGREEN,
        reminder_text="Whenever you cast a noncreature spell, this creature gets +1/+1 until end of turn.",
        rules_text="Whenever you cast a noncreature spell, this creature gets +1/+1 until end of turn.",
        stackable=True
    ),
    "reach": KeywordDefinition(
        name="Reach",
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature can block creatures with flying.",
        rules_text="A creature with reach can block creatures with flying.",
        combat_relevant=True,
        interaction_rules={"flying": "Creatures with reach can block creatures with flying."}
    ),
    "trample": KeywordDefinition(
        name="Trample",
        category=KeywordCategory.EVERGREEN,
        reminder_text="This creature can deal excess combat damage to the player or planeswalker it's attacking.",
        rules_text="Trample damage is assigned to defending player if blocking creatures are assigned lethal damage.",
        combat_relevant=True
    ),
    "vigilance": KeywordDefinition(
        name="Vigilance",
        category=KeywordCategory.EVERGREEN,
        reminder_text="Attacking doesn't cause this creature to tap.",
        rules_text="Attacking doesn't cause a creature with vigilance to tap.",
        combat_relevant=True
    ),
    "ward": KeywordDefinition(
        name="Ward",
        category=KeywordCategory.EVERGREEN,
        reminder_text="Whenever this creature becomes the target of a spell or ability an opponent controls, counter it unless that player pays the ward cost.",
        rules_text="Whenever a permanent with ward becomes the target of a spell or ability an opponent controls, counter that spell or ability unless its controller pays the ward cost.",
        parameter_type="cost"
    ),
    
    # Deciduous Keywords  
    "flash": KeywordDefinition(
        name="Flash",
        category=KeywordCategory.DECIDUOUS,
        reminder_text="You may cast this spell any time you could cast an instant.",
        rules_text="A spell with flash may be cast any time you could cast an instant."
    ),
    "protection": KeywordDefinition(
        name="Protection",
        category=KeywordCategory.DECIDUOUS,
        reminder_text="This creature can't be blocked, targeted, dealt damage, enchanted, or equipped by anything with the stated quality.",
        rules_text="Protection from X means this permanent can't be blocked, targeted, dealt damage, enchanted, or equipped by anything that is X.",
        parameter_type="quality",
        combat_relevant=True
    ),
    "shroud": KeywordDefinition(
        name="Shroud",
        category=KeywordCategory.DECIDUOUS,
        reminder_text="This creature can't be the target of spells or abilities.",
        rules_text="A permanent or player with shroud can't be the target of spells or abilities."
    ),
    
    # Common Mechanics
    "scry": KeywordDefinition(
        name="Scry",
        category=KeywordCategory.MECHANICS,
        reminder_text="Look at the top N cards of your library, then put any number of them on the bottom of your library and the rest on top in any order.",
        rules_text="To scry N, look at the top N cards of your library, then put any number of them on the bottom of your library and the rest on top in any order.",
        parameter_type="number"
    ),
    "mill": KeywordDefinition(
        name="Mill",
        category=KeywordCategory.MECHANICS,
        reminder_text="Put the top N cards of your library into your graveyard.",
        rules_text="To mill N cards, a player puts the top N cards of their library into their graveyard.",
        parameter_type="number"
    ),
    "convoke": KeywordDefinition(
        name="Convoke",
        category=KeywordCategory.MECHANICS,
        reminder_text="Each creature you tap while casting this spell pays for {1} or one mana of that creature's color.",
        rules_text="For each creature you tap while casting a spell with convoke, you pay {1} less or one mana of that creature's color."
    ),
    "delve": KeywordDefinition(
        name="Delve", 
        category=KeywordCategory.MECHANICS,
        reminder_text="Each card you exile from your graveyard while casting this spell pays for {1}.",
        rules_text="For each card you exile from your graveyard while casting a spell with delve, you pay {1} less."
    ),
    "flashback": KeywordDefinition(
        name="Flashback",
        category=KeywordCategory.MECHANICS,
        reminder_text="You may cast this card from your graveyard for its flashback cost. Then exile it.",
        rules_text="A spell with flashback may be cast from its owner's graveyard for its flashback cost, then is exiled.",
        parameter_type="cost"
    ),
    "kicker": KeywordDefinition(
        name="Kicker",
        category=KeywordCategory.MECHANICS,
        reminder_text="You may pay an additional cost as you cast this spell.",
        rules_text="Kicker is an additional cost. If a spell was kicked, it has additional or alternative effects.",
        parameter_type="cost"
    ),
    "cycling": KeywordDefinition(
        name="Cycling",
        category=KeywordCategory.MECHANICS,
        reminder_text="Pay the cycling cost, discard this card: Draw a card.",
        rules_text="Cycling is an activated ability that functions only in the player's hand.",
        parameter_type="cost"
    ),
    "morph": KeywordDefinition(
        name="Morph",
        category=KeywordCategory.MECHANICS,
        reminder_text="You may cast this card face down as a 2/2 creature for {3}. Turn it face up any time for its morph cost.",
        rules_text="A permanent with morph may be cast face down as a 2/2 colorless creature with no abilities for {3}.",
        parameter_type="cost"
    ),
    "infect": KeywordDefinition(
        name="Infect",
        category=KeywordCategory.MECHANICS,
        reminder_text="This creature deals damage to creatures in the form of -1/-1 counters and to players in the form of poison counters.",
        rules_text="A source with infect deals damage to creatures in the form of -1/-1 counters and to players in the form of poison counters.",
        combat_relevant=True
    ),
    "annihilator": KeywordDefinition(
        name="Annihilator",
        category=KeywordCategory.MECHANICS,
        reminder_text="Whenever this creature attacks, defending player sacrifices N permanents.",
        rules_text="Whenever a creature with annihilator attacks, defending player sacrifices that many permanents.",
        parameter_type="number",
        combat_relevant=True
    ),
    "landfall": KeywordDefinition(
        name="Landfall",
        category=KeywordCategory.MECHANICS,
        reminder_text="Whenever a land enters the battlefield under your control, this ability triggers.",
        rules_text="Landfall abilities trigger whenever a land enters the battlefield under the ability's controller's control."
    ),
}

class KeywordProcessor:
    """Processes and manages keyword abilities on cards"""
    
    def __init__(self):
        self.keyword_patterns = self._build_keyword_patterns()
        self.interaction_handlers = self._build_interaction_handlers()
    
    def _build_keyword_patterns(self) -> Dict[str, re.Pattern]:
        """Build regex patterns for detecting keywords in card text"""
        patterns = {}
        
        for keyword, definition in MTG_KEYWORDS.items():
            # Basic keyword detection
            if definition.parameter_type:
                # Keywords with parameters (e.g., "Ward {2}", "Scry 1", "Protection from red")
                if definition.parameter_type == "cost":
                    patterns[keyword] = re.compile(rf'{definition.name}\s+(\{{[^}}]+\}}|\d+)', re.IGNORECASE)
                elif definition.parameter_type == "number":
                    patterns[keyword] = re.compile(rf'{definition.name}\s+(\d+)', re.IGNORECASE)
                elif definition.parameter_type == "quality":
                    patterns[keyword] = re.compile(rf'{definition.name}\s+from\s+([\w\s,]+)', re.IGNORECASE)
            else:
                # Simple keyword detection
                patterns[keyword] = re.compile(rf'\b{definition.name}\b', re.IGNORECASE)
        
        return patterns
    
    def _build_interaction_handlers(self) -> Dict[str, Callable]:
        """Build handlers for keyword interactions"""
        handlers = {}
        
        # Deathtouch interaction handler
        def handle_deathtouch_damage(damage_source, damage_target, damage_amount):
            """Handle deathtouch damage - any amount is lethal"""
            if self.has_keyword(damage_source, "deathtouch") and damage_amount > 0:
                if not self.has_keyword(damage_target, "indestructible"):
                    return True  # Mark for destruction
            return False
        
        handlers["deathtouch_damage"] = handle_deathtouch_damage
        
        # First strike / double strike combat handler
        def handle_first_strike_combat(attacker, blocker):
            """Handle first strike combat timing"""
            attacker_first = (self.has_keyword(attacker, "first strike") or 
                            self.has_keyword(attacker, "double strike"))
            blocker_first = (self.has_keyword(blocker, "first strike") or 
                           self.has_keyword(blocker, "double strike"))
            
            if attacker_first and not blocker_first:
                return "attacker_first"
            elif blocker_first and not attacker_first:
                return "blocker_first"
            else:
                return "simultaneous"
        
        handlers["first_strike_combat"] = handle_first_strike_combat
        
        # Flying/reach blocking handler
        def can_block_flying(blocker, attacker):
            """Check if blocker can block flying attacker"""
            if self.has_keyword(attacker, "flying"):
                return (self.has_keyword(blocker, "flying") or 
                       self.has_keyword(blocker, "reach"))
            return True
        
        handlers["can_block_flying"] = can_block_flying
        
        return handlers
    
    def extract_keywords(self, card_text: str) -> Dict[str, Optional[str]]:
        """Extract all keywords from card text with their parameters"""
        found_keywords = {}
        
        for keyword, pattern in self.keyword_patterns.items():
            matches = pattern.findall(card_text)
            if matches:
                if MTG_KEYWORDS[keyword].parameter_type:
                    # Store parameter value
                    found_keywords[keyword] = matches[0] if matches else None
                else:
                    # Simple presence
                    found_keywords[keyword] = None
        
        return found_keywords
    
    def has_keyword(self, card, keyword: str) -> bool:
        """Check if a card has a specific keyword"""
        if hasattr(card, 'keywords'):
            return keyword.lower() in [k.lower() for k in card.keywords.keys()]
        
        # Fallback: search in card text
        card_text = getattr(card, 'text', '')
        keywords = self.extract_keywords(card_text)
        return keyword.lower() in [k.lower() for k in keywords.keys()]
    
    def get_keyword_parameter(self, card, keyword: str) -> Optional[str]:
        """Get the parameter value for a parameterized keyword"""
        if hasattr(card, 'keywords') and keyword.lower() in card.keywords:
            return card.keywords[keyword.lower()]
        
        # Fallback: extract from text
        card_text = getattr(card, 'text', '')
        keywords = self.extract_keywords(card_text)
        return keywords.get(keyword.lower())
    
    def get_combat_keywords(self, card) -> Set[str]:
        """Get all combat-relevant keywords for a card"""
        combat_keywords = set()
        
        if hasattr(card, 'keywords'):
            keywords = card.keywords
        else:
            card_text = getattr(card, 'text', '')
            keywords = self.extract_keywords(card_text)
        
        for keyword in keywords:
            if keyword.lower() in MTG_KEYWORDS and MTG_KEYWORDS[keyword.lower()].combat_relevant:
                combat_keywords.add(keyword.lower())
        
        return combat_keywords
    
    def apply_keyword_interactions(self, situation: str, *args) -> any:
        """Apply keyword interaction rules for a given situation"""
        if situation in self.interaction_handlers:
            return self.interaction_handlers[situation](*args)
        return None
    
    def get_keyword_definition(self, keyword: str) -> Optional[KeywordDefinition]:
        """Get the complete definition for a keyword"""
        return MTG_KEYWORDS.get(keyword.lower())
    
    def validate_keywords(self, card_text: str) -> List[str]:
        """Validate that all keywords in text are recognized"""
        # Simple validation - look for unrecognized ability words
        words = re.findall(r'\b[A-Z][a-z]+\b', card_text)
        unrecognized = []
        
        for word in words:
            if (word.lower() not in MTG_KEYWORDS and 
                word not in ['When', 'Whenever', 'As', 'If', 'At'] and
                not word.isdigit()):
                unrecognized.append(word)
        
        return unrecognized

# Global keyword processor instance
keyword_processor = KeywordProcessor()

# Utility functions for easy access
def extract_card_keywords(card_text: str) -> Dict[str, Optional[str]]:
    """Extract keywords from card text"""
    return keyword_processor.extract_keywords(card_text)

def has_keyword(card, keyword: str) -> bool:
    """Check if card has keyword"""
    return keyword_processor.has_keyword(card, keyword)

def get_combat_keywords(card) -> Set[str]:
    """Get combat-relevant keywords"""
    return keyword_processor.get_combat_keywords(card)

def can_block(blocker, attacker) -> bool:
    """Check if blocker can block attacker based on keywords"""
    # Handle flying/reach
    if not keyword_processor.apply_keyword_interactions("can_block_flying", blocker, attacker):
        return False
    
    # Handle protection
    if has_keyword(attacker, "protection"):
        protection_from = keyword_processor.get_keyword_parameter(attacker, "protection")
        if protection_from:
            # Simple implementation - would need more complex logic for full protection rules
            blocker_colors = getattr(blocker, 'color_identity', [])
            if any(color in protection_from.lower() for color in blocker_colors):
                return False
    
    return True
