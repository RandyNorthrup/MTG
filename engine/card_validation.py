"""
MTG Card Data Validation and Normalization System
Ensures all card data matches official Oracle properties and maintains consistency
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set, Tuple, Any
import re
import logging
from enum import Enum

class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"          # Critical issues that break gameplay
    WARNING = "warning"      # Issues that may cause problems
    INFO = "info"           # Minor inconsistencies

@dataclass
class ValidationResult:
    """Result of validating a card"""
    card_name: str
    is_valid: bool = True
    errors: List[str] = None
    warnings: List[str] = None
    info: List[str] = None
    normalized_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.info is None:
            self.info = []

class CardValidator:
    """Validates and normalizes MTG card data for Oracle accuracy"""
    
    def __init__(self):
        self.known_types = self._build_known_types()
        self.known_supertypes = self._build_known_supertypes()
        self.known_subtypes = self._build_known_subtypes()
        self.mana_symbol_patterns = self._build_mana_patterns()
        self.ability_patterns = self._build_ability_patterns()
        
    def _build_known_types(self) -> Set[str]:
        """Build set of known card types"""
        return {
            # Permanent types
            "Artifact", "Creature", "Enchantment", "Land", "Planeswalker", "Battle",
            # Non-permanent types
            "Instant", "Sorcery",
            # Historical/special types
            "Tribal", "Plane", "Phenomenon", "Scheme", "Vanguard", "Conspiracy", "Dungeon"
        }
    
    def _build_known_supertypes(self) -> Set[str]:
        """Build set of known supertypes"""
        return {
            "Basic", "Legendary", "Snow", "World", "Ongoing", "Elite", "Host"
        }
    
    def _build_known_subtypes(self) -> Dict[str, Set[str]]:
        """Build dictionary of known subtypes by card type"""
        return {
            "Creature": {
                "Human", "Wizard", "Soldier", "Knight", "Elf", "Goblin", "Vampire", "Zombie",
                "Dragon", "Angel", "Demon", "Beast", "Bird", "Fish", "Insect", "Spider",
                "Artifact", "Wall", "Golem", "Construct", "Equipment", "Vehicle",
                "Advisor", "Ally", "Archer", "Artificer", "Assassin", "Barbarian", "Bard",
                "Berserker", "Cleric", "Druid", "Monk", "Ninja", "Pirate", "Rogue", "Samurai",
                "Scout", "Shaman", "Warlock", "Warrior", "Peasant", "Citizen", "Noble"
                # Note: This is a subset - full list is much longer
            },
            "Artifact": {
                "Equipment", "Fortification", "Vehicle", "Contraption", "Food", "Treasure",
                "Clue", "Gold", "Blood", "Powerstone"
            },
            "Enchantment": {
                "Aura", "Cartouche", "Curse", "Rune", "Saga", "Shard", "Shrine", "Class", "Case"
            },
            "Land": {
                "Plains", "Island", "Swamp", "Mountain", "Forest", "Desert", "Gate", "Lair",
                "Locus", "Mine", "Power-Plant", "Tower", "Urza's"
            },
            "Planeswalker": {
                "Ajani", "Chandra", "Garruk", "Jace", "Liliana", "Nissa", "Elspeth", "Gideon",
                "Karn", "Sorin", "Tezzeret", "Vraska", "Ashiok", "Domri", "Kiora", "Narset",
                "Teferi", "Ugin", "Vivien", "Wrenn"
                # Note: This is a subset - includes most planeswalker types
            },
            "Instant": set(),  # Instants don't have subtypes typically
            "Sorcery": set()   # Sorceries don't have subtypes typically
        }
    
    def _build_mana_patterns(self) -> Dict[str, re.Pattern]:
        """Build regex patterns for mana cost validation"""
        return {
            "mana_symbol": re.compile(r"\{([WUBRGCXYZSPET]|[0-9]+|[WUBRG]/[WUBRGP]|2/[WUBRG]|[WUBRG]/P|H[WUBRG])\}"),
            "hybrid_mana": re.compile(r"\{([WUBRG])/([WUBRGP])\}"),
            "phyrexian_mana": re.compile(r"\{([WUBRG])/P\}"),
            "monocolored_hybrid": re.compile(r"\{2/([WUBRG])\}"),
            "complete_cost": re.compile(r"^(\{[^}]+\})*$")
        }
    
    def _build_ability_patterns(self) -> Dict[str, re.Pattern]:
        """Build regex patterns for ability text validation"""
        return {
            "reminder_text": re.compile(r"\([^)]+\)"),
            "mana_cost_in_text": re.compile(r"\{[^}]+\}"),
            "activated_ability": re.compile(r"^[^:]+:[^.]+\."),
            "triggered_ability": re.compile(r"^(When|Whenever|At)\s[^.]+\."),
            "static_ability": re.compile(r"^[A-Z][^.]*\.$")
        }
    
    def validate_card(self, card_data: Dict[str, Any]) -> ValidationResult:
        """Perform comprehensive validation of card data"""
        result = ValidationResult(card_name=card_data.get("name", "Unknown"))
        
        # Validate required fields
        self._validate_required_fields(card_data, result)
        
        # Validate card types
        self._validate_types(card_data, result)
        
        # Validate mana cost
        self._validate_mana_cost(card_data, result)
        
        # Validate power/toughness
        self._validate_power_toughness(card_data, result)
        
        # Validate ability text
        self._validate_ability_text(card_data, result)
        
        # Validate color identity
        self._validate_color_identity(card_data, result)
        
        # Create normalized data
        result.normalized_data = self._normalize_card_data(card_data, result)
        
        # Set overall validation status
        result.is_valid = len(result.errors) == 0
        
        return result
    
    def _validate_required_fields(self, card_data: Dict[str, Any], result: ValidationResult):
        """Validate that required fields are present"""
        required_fields = ["name", "types", "mana_cost"]
        
        for field in required_fields:
            if field not in card_data or card_data[field] is None:
                result.errors.append(f"Missing required field: {field}")
        
        # Validate name format
        if "name" in card_data:
            name = card_data["name"]
            if not isinstance(name, str) or not name.strip():
                result.errors.append("Card name must be a non-empty string")
            elif len(name) > 100:  # Reasonable length limit
                result.warnings.append("Card name is unusually long")
    
    def _validate_types(self, card_data: Dict[str, Any], result: ValidationResult):
        """Validate card type line"""
        if "types" not in card_data:
            return
        
        types = card_data["types"]
        if not isinstance(types, list):
            result.errors.append("Types must be a list")
            return
        
        if not types:
            result.errors.append("Card must have at least one type")
            return
        
        # Check for known types
        main_types = []
        supertypes = []
        subtypes = []
        
        for type_word in types:
            if type_word in self.known_supertypes:
                supertypes.append(type_word)
            elif type_word in self.known_types:
                main_types.append(type_word)
            else:
                # Could be subtype or unknown
                subtypes.append(type_word)
        
        # Validate type combinations
        if not main_types:
            result.errors.append("Card must have at least one main type")
        
        # Check for impossible type combinations
        permanent_types = {"Artifact", "Creature", "Enchantment", "Land", "Planeswalker", "Battle"}
        spell_types = {"Instant", "Sorcery"}
        
        has_permanent = any(t in permanent_types for t in main_types)
        has_spell = any(t in spell_types for t in main_types)
        
        if has_permanent and has_spell:
            result.errors.append("Card cannot be both a permanent and a spell type")
        
        # Validate subtypes for main types
        self._validate_subtypes(main_types, subtypes, result)
    
    def _validate_subtypes(self, main_types: List[str], subtypes: List[str], result: ValidationResult):
        """Validate that subtypes are appropriate for the main types"""
        for main_type in main_types:
            if main_type in self.known_subtypes:
                valid_subtypes = self.known_subtypes[main_type]
                for subtype in subtypes:
                    if subtype not in valid_subtypes and subtype not in self.known_types:
                        result.warnings.append(f"'{subtype}' may not be a valid subtype for {main_type}")
    
    def _validate_mana_cost(self, card_data: Dict[str, Any], result: ValidationResult):
        """Validate mana cost format and consistency"""
        mana_cost_str = card_data.get("mana_cost_str", "")
        mana_cost_int = card_data.get("mana_cost", 0)
        
        # Validate mana cost string format
        if mana_cost_str:
            if not self.mana_symbol_patterns["complete_cost"].match(mana_cost_str):
                result.errors.append(f"Invalid mana cost format: {mana_cost_str}")
                return
            
            # Calculate CMC from string and compare to stored value
            calculated_cmc = self._calculate_cmc(mana_cost_str)
            if calculated_cmc != mana_cost_int:
                result.warnings.append(f"Mana cost mismatch: string '{mana_cost_str}' = {calculated_cmc}, but stored value is {mana_cost_int}")
        
        # Validate mana cost constraints for card types
        types = card_data.get("types", [])
        if "Land" in types and mana_cost_int > 0:
            result.warnings.append("Lands typically have mana cost 0")
    
    def _calculate_cmc(self, mana_cost_str: str) -> int:
        """Calculate converted mana cost from mana cost string"""
        if not mana_cost_str:
            return 0
        
        total = 0
        symbols = self.mana_symbol_patterns["mana_symbol"].findall(mana_cost_str)
        
        for symbol in symbols:
            if symbol.isdigit():
                total += int(symbol)
            elif symbol in "WUBRGCSP":
                total += 1
            elif "/" in symbol:  # Hybrid or Phyrexian
                total += 1
            elif symbol == "X":
                total += 0  # X = 0 except when cast
        
        return total
    
    def _validate_power_toughness(self, card_data: Dict[str, Any], result: ValidationResult):
        """Validate power and toughness values"""
        types = card_data.get("types", [])
        power = card_data.get("power")
        toughness = card_data.get("toughness")
        
        is_creature = "Creature" in types
        is_vehicle = "Vehicle" in (card_data.get("subtypes", []) or [])
        
        # Creatures and vehicles should have power/toughness
        if is_creature or is_vehicle:
            if power is None:
                result.warnings.append("Creature cards should have power defined")
            if toughness is None:
                result.warnings.append("Creature cards should have toughness defined")
                
            # Validate power/toughness values
            for stat, name in [(power, "power"), (toughness, "toughness")]:
                if stat is not None:
                    if not isinstance(stat, int):
                        result.errors.append(f"{name.capitalize()} must be an integer or null")
                    elif stat < 0:
                        result.warnings.append(f"Negative {name} ({stat}) is unusual")
        else:
            # Non-creatures should not have power/toughness
            if power is not None or toughness is not None:
                result.warnings.append("Non-creature cards should not have power/toughness")
    
    def _validate_ability_text(self, card_data: Dict[str, Any], result: ValidationResult):
        """Validate ability text format and content"""
        text = card_data.get("text", "")
        if not text:
            return  # Empty text is valid
        
        # Check for valid ability format
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        for sentence in sentences:
            # Skip reminder text
            if sentence.startswith('(') and sentence.endswith(')'):
                continue
            
            # Check for properly formatted abilities
            if not (self.ability_patterns["activated_ability"].match(sentence + '.') or
                    self.ability_patterns["triggered_ability"].match(sentence + '.') or
                    self.ability_patterns["static_ability"].match(sentence + '.')):
                result.info.append(f"Unusual ability format: '{sentence}'")
        
        # Check for mana symbols in text
        mana_symbols = self.mana_symbol_patterns["mana_symbol"].findall(text)
        for symbol in mana_symbols:
            if not symbol:  # Invalid symbol
                result.warnings.append(f"Invalid mana symbol in text: {symbol}")
    
    def _validate_color_identity(self, card_data: Dict[str, Any], result: ValidationResult):
        """Validate color identity consistency"""
        color_identity = set(card_data.get("color_identity", []))
        mana_cost_str = card_data.get("mana_cost_str", "")
        text = card_data.get("text", "")
        
        # Extract colors from mana cost
        cost_colors = set()
        cost_symbols = self.mana_symbol_patterns["mana_symbol"].findall(mana_cost_str)
        for symbol in cost_symbols:
            if symbol in "WUBRG":
                cost_colors.add(symbol)
            elif "/" in symbol:  # Hybrid
                for color in symbol.split("/"):
                    if color in "WUBRG":
                        cost_colors.add(color)
        
        # Extract colors from text
        text_colors = set()
        text_symbols = self.mana_symbol_patterns["mana_symbol"].findall(text)
        for symbol in text_symbols:
            if symbol in "WUBRG":
                text_colors.add(symbol)
            elif "/" in symbol:  # Hybrid
                for color in symbol.split("/"):
                    if color in "WUBRG":
                        text_colors.add(color)
        
        # Combine all colors that should be in identity
        expected_colors = cost_colors | text_colors
        
        # Check consistency
        if expected_colors != color_identity:
            missing = expected_colors - color_identity
            extra = color_identity - expected_colors
            
            if missing:
                result.warnings.append(f"Color identity missing colors: {', '.join(missing)}")
            if extra:
                result.warnings.append(f"Color identity has extra colors: {', '.join(extra)}")
    
    def _normalize_card_data(self, card_data: Dict[str, Any], result: ValidationResult) -> Dict[str, Any]:
        """Create normalized version of card data"""
        normalized = card_data.copy()
        
        # Normalize name
        if "name" in normalized:
            normalized["name"] = normalized["name"].strip()
        
        # Normalize types
        if "types" in normalized:
            normalized["types"] = [t.strip().title() for t in normalized["types"]]
        
        # Normalize mana cost
        if "mana_cost_str" in normalized:
            # Clean up mana cost string
            cost_str = normalized["mana_cost_str"]
            # Remove spaces and normalize case
            cost_str = re.sub(r'\s+', '', cost_str)
            normalized["mana_cost_str"] = cost_str
            
            # Recalculate CMC if needed
            if "mana_cost" not in normalized or normalized["mana_cost"] != self._calculate_cmc(cost_str):
                normalized["mana_cost"] = self._calculate_cmc(cost_str)
        
        # Normalize text
        if "text" in normalized:
            # Clean up spacing and formatting
            text = normalized["text"]
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = text.strip()
            normalized["text"] = text
        
        # Normalize color identity
        if "color_identity" in normalized:
            normalized["color_identity"] = sorted(list(set(normalized["color_identity"])))
        
        return normalized
    
    def validate_deck_cards(self, cards: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """Validate all cards in a deck"""
        results = {}
        
        for card_data in cards:
            card_name = card_data.get("name", "Unknown")
            results[card_name] = self.validate_card(card_data)
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, int]:
        """Get summary statistics for validation results"""
        summary = {
            "total_cards": len(results),
            "valid_cards": 0,
            "cards_with_errors": 0,
            "cards_with_warnings": 0,
            "total_errors": 0,
            "total_warnings": 0,
            "total_info": 0
        }
        
        for result in results.values():
            if result.is_valid:
                summary["valid_cards"] += 1
            if result.errors:
                summary["cards_with_errors"] += 1
                summary["total_errors"] += len(result.errors)
            if result.warnings:
                summary["cards_with_warnings"] += 1
                summary["total_warnings"] += len(result.warnings)
            summary["total_info"] += len(result.info)
        
        return summary

# Global validator instance
card_validator = CardValidator()

def validate_card_data(card_data: Dict[str, Any]) -> ValidationResult:
    """Validate a single card's data"""
    return card_validator.validate_card(card_data)

def normalize_card_data(card_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize card data to standard format"""
    result = card_validator.validate_card(card_data)
    return result.normalized_data if result.normalized_data else card_data

def validate_deck_cards(cards: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
    """Validate all cards in a deck"""
    return card_validator.validate_deck_cards(cards)
