"""
MTG Token and Copy Generation System
Handles creating tokens and copies according to comprehensive rules
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable
import copy as python_copy
from engine.card_engine import Card, Permanent
from enum import Enum

class CopyType(Enum):
    """Types of copying effects"""
    EXACT_COPY = "exact"           # Copy exactly as printed
    TOKEN_COPY = "token_copy"      # Token copy of permanent
    SPELL_COPY = "spell_copy"      # Copy of spell on stack
    MODIFIED_COPY = "modified"     # Copy with modifications

@dataclass
class TokenDefinition:
    """Definition for creating tokens"""
    name: str
    types: List[str]
    power: Optional[int] = None
    toughness: Optional[int] = None
    colors: List[str] = field(default_factory=list)
    mana_cost: int = 0
    mana_cost_str: str = ""
    text: str = ""
    keywords: List[str] = field(default_factory=list)
    subtypes: List[str] = field(default_factory=list)
    is_token: bool = True
    
    # Additional properties for special tokens
    enters_tapped: bool = False
    has_haste: bool = False
    sacrifice_at_end: bool = False
    temporary_duration: Optional[str] = None  # "end of turn", "end of combat", etc.

@dataclass
class CopyEffect:
    """Represents a copying effect"""
    source_id: str                          # ID of the source creating the copy
    copy_type: CopyType
    original_card: Optional[Card] = None    # Original card being copied
    modifications: Dict[str, Any] = field(default_factory=dict)
    layer_modifications: List[Any] = field(default_factory=list)  # Continuous effects
    except_characteristics: Set[str] = field(default_factory=set)  # Don't copy these
    
    # Token-specific properties
    token_definition: Optional[TokenDefinition] = None
    quantity: int = 1
    controller_id: int = 0

class TokenAndCopyEngine:
    """Manages token creation and copying effects"""
    
    def __init__(self, layers_engine=None):
        self.layers_engine = layers_engine
        self.token_definitions = self._build_common_token_definitions()
        self.active_copies = {}  # card_id -> CopyEffect
        self.token_counter = 0
        
    def _build_common_token_definitions(self) -> Dict[str, TokenDefinition]:
        """Build database of common token types"""
        return {
            # Generic creature tokens
            "1/1_white_soldier": TokenDefinition(
                name="Soldier Token",
                types=["Creature", "Token"],
                subtypes=["Soldier"],
                power=1, toughness=1,
                colors=["W"]
            ),
            "2/2_white_knight": TokenDefinition(
                name="Knight Token", 
                types=["Creature", "Token"],
                subtypes=["Knight"],
                power=2, toughness=2,
                colors=["W"]
            ),
            "1/1_green_saproling": TokenDefinition(
                name="Saproling Token",
                types=["Creature", "Token"],
                subtypes=["Saproling"],
                power=1, toughness=1,
                colors=["G"]
            ),
            "2/2_green_bear": TokenDefinition(
                name="Bear Token",
                types=["Creature", "Token"], 
                subtypes=["Bear"],
                power=2, toughness=2,
                colors=["G"]
            ),
            "1/1_blue_bird_flying": TokenDefinition(
                name="Bird Token",
                types=["Creature", "Token"],
                subtypes=["Bird"],
                power=1, toughness=1,
                colors=["U"],
                keywords=["Flying"]
            ),
            "1/1_red_goblin": TokenDefinition(
                name="Goblin Token",
                types=["Creature", "Token"],
                subtypes=["Goblin"],
                power=1, toughness=1,
                colors=["R"]
            ),
            "2/2_black_zombie": TokenDefinition(
                name="Zombie Token",
                types=["Creature", "Token"],
                subtypes=["Zombie"],
                power=2, toughness=2,
                colors=["B"]
            ),
            
            # Artifact tokens
            "treasure": TokenDefinition(
                name="Treasure Token",
                types=["Artifact", "Token"],
                subtypes=["Treasure"],
                text="{T}, Sacrifice this artifact: Add one mana of any color.",
                colors=[]
            ),
            "food": TokenDefinition(
                name="Food Token",
                types=["Artifact", "Token"],
                subtypes=["Food"],
                text="{2}, {T}, Sacrifice this artifact: You gain 3 life.",
                colors=[]
            ),
            "clue": TokenDefinition(
                name="Clue Token",
                types=["Artifact", "Token"],
                subtypes=["Clue"],
                text="{2}, Sacrifice this artifact: Draw a card.",
                colors=[]
            ),
            "blood": TokenDefinition(
                name="Blood Token",
                types=["Artifact", "Token"],
                subtypes=["Blood"],
                text="{1}, {T}, Discard a card, Sacrifice this artifact: Draw a card.",
                colors=[]
            ),
            
            # Special tokens
            "0/1_white_goat": TokenDefinition(
                name="Goat Token",
                types=["Creature", "Token"],
                subtypes=["Goat"],
                power=0, toughness=1,
                colors=["W"]
            ),
            "4/4_angel_flying": TokenDefinition(
                name="Angel Token",
                types=["Creature", "Token"],
                subtypes=["Angel"],
                power=4, toughness=4,
                colors=["W"],
                keywords=["Flying"]
            )
        }
    
    def create_token(self, token_key: str, controller_id: int, quantity: int = 1,
                    modifications: Dict[str, Any] = None) -> List[Card]:
        """Create token cards based on predefined token types"""
        if token_key not in self.token_definitions:
            raise ValueError(f"Unknown token type: {token_key}")
        
        token_def = self.token_definitions[token_key]
        tokens = []
        
        for i in range(quantity):
            self.token_counter += 1
            token_id = f"token_{token_key}_{self.token_counter}"
            
            # Create base token
            token_card = Card(
                id=token_id,
                name=token_def.name,
                types=token_def.types.copy(),
                mana_cost=token_def.mana_cost,
                mana_cost_str=token_def.mana_cost_str,
                power=token_def.power,
                toughness=token_def.toughness,
                text=token_def.text,
                color_identity=token_def.colors.copy(),
                owner_id=controller_id,
                controller_id=controller_id
            )
            
            # Add token-specific properties
            token_card.is_token = True
            token_card.subtypes = token_def.subtypes.copy()
            
            # Apply modifications if provided
            if modifications:
                self._apply_token_modifications(token_card, modifications)
            
            # Add keywords to text if needed
            if token_def.keywords:
                keyword_text = ", ".join(token_def.keywords)
                if token_card.text:
                    token_card.text = f"{keyword_text}\n{token_card.text}"
                else:
                    token_card.text = keyword_text
            
            # Associate with layers engine if available
            if self.layers_engine:
                token_card.set_layers_engine(self.layers_engine)
            
            tokens.append(token_card)
        
        return tokens
    
    def create_custom_token(self, token_def: TokenDefinition, controller_id: int,
                          quantity: int = 1) -> List[Card]:
        """Create tokens from a custom TokenDefinition"""
        tokens = []
        
        for i in range(quantity):
            self.token_counter += 1
            token_id = f"custom_token_{self.token_counter}"
            
            token_card = Card(
                id=token_id,
                name=token_def.name,
                types=token_def.types.copy(),
                mana_cost=token_def.mana_cost,
                mana_cost_str=token_def.mana_cost_str,
                power=token_def.power,
                toughness=token_def.toughness,
                text=token_def.text,
                color_identity=token_def.colors.copy(),
                owner_id=controller_id,
                controller_id=controller_id
            )
            
            # Token properties
            token_card.is_token = True
            token_card.subtypes = token_def.subtypes.copy()
            token_card.enters_tapped = token_def.enters_tapped
            token_card.sacrifice_at_end = token_def.sacrifice_at_end
            
            # Add temporary duration tracking
            if token_def.temporary_duration:
                token_card.temporary_duration = token_def.temporary_duration
            
            # Associate with layers engine
            if self.layers_engine:
                token_card.set_layers_engine(self.layers_engine)
            
            tokens.append(token_card)
        
        return tokens
    
    def create_token_copy(self, original: Card, controller_id: int, 
                         modifications: Dict[str, Any] = None) -> Card:
        """Create a token copy of an existing card"""
        self.token_counter += 1
        copy_id = f"token_copy_{original.id}_{self.token_counter}"
        
        # Create exact copy first
        token_copy = self._create_exact_copy(original, copy_id, controller_id)
        
        # Make it a token
        token_copy.is_token = True
        if "Token" not in token_copy.types:
            token_copy.types.append("Token")
        
        # Apply modifications
        if modifications:
            self._apply_copy_modifications(token_copy, modifications)
        
        # Store copy effect for tracking
        copy_effect = CopyEffect(
            source_id=copy_id,
            copy_type=CopyType.TOKEN_COPY,
            original_card=original,
            modifications=modifications or {},
            controller_id=controller_id
        )
        self.active_copies[copy_id] = copy_effect
        
        return token_copy
    
    def create_exact_copy(self, original: Card, controller_id: Optional[int] = None) -> Card:
        """Create an exact copy of a card (not a token)"""
        self.token_counter += 1
        copy_id = f"copy_{original.id}_{self.token_counter}"
        
        if controller_id is None:
            controller_id = original.controller_id
        
        copy_card = self._create_exact_copy(original, copy_id, controller_id)
        
        # Store copy effect
        copy_effect = CopyEffect(
            source_id=copy_id,
            copy_type=CopyType.EXACT_COPY,
            original_card=original,
            controller_id=controller_id
        )
        self.active_copies[copy_id] = copy_effect
        
        return copy_card
    
    def _create_exact_copy(self, original: Card, new_id: str, controller_id: int) -> Card:
        """Create an exact copy following CR 707.2"""
        # Copy all copiable characteristics (CR 707.2)
        copy_card = Card(
            id=new_id,
            name=original.name,
            types=original.types.copy(),
            mana_cost=original.mana_cost,
            mana_cost_str=original.mana_cost_str,
            power=original.power,
            toughness=original.toughness,
            text=original.text,
            color_identity=original.color_identity.copy(),
            owner_id=controller_id,  # Owner becomes the controller
            controller_id=controller_id
        )
        
        # Copy additional properties that are copiable
        if hasattr(original, 'subtypes'):
            copy_card.subtypes = original.subtypes.copy()
        if hasattr(original, 'keywords'):
            copy_card.keywords = python_copy.deepcopy(original.keywords)
        if hasattr(original, 'loyalty'):
            copy_card.loyalty = original.loyalty
        
        # Associate with layers engine
        if self.layers_engine:
            copy_card.set_layers_engine(self.layers_engine)
        
        return copy_card
    
    def create_modified_copy(self, original: Card, controller_id: int,
                           modifications: Dict[str, Any]) -> Card:
        """Create a copy with specific modifications"""
        copy_card = self.create_exact_copy(original, controller_id)
        self._apply_copy_modifications(copy_card, modifications)
        
        # Update the copy effect
        if copy_card.id in self.active_copies:
            self.active_copies[copy_card.id].copy_type = CopyType.MODIFIED_COPY
            self.active_copies[copy_card.id].modifications = modifications
        
        return copy_card
    
    def _apply_token_modifications(self, token: Card, modifications: Dict[str, Any]):
        """Apply modifications to a token during creation"""
        for key, value in modifications.items():
            if key == "power" and value is not None:
                token.power = value
            elif key == "toughness" and value is not None:
                token.toughness = value
            elif key == "types" and isinstance(value, list):
                token.types = value.copy()
            elif key == "colors" and isinstance(value, list):
                token.color_identity = value.copy()
            elif key == "text":
                token.text = str(value)
            elif key == "name":
                token.name = str(value)
            elif key == "add_types" and isinstance(value, list):
                token.types.extend(t for t in value if t not in token.types)
            elif key == "add_keywords" and isinstance(value, list):
                keyword_text = ", ".join(value)
                if token.text:
                    token.text = f"{keyword_text}\n{token.text}"
                else:
                    token.text = keyword_text
    
    def _apply_copy_modifications(self, copy_card: Card, modifications: Dict[str, Any]):
        """Apply modifications to a copy"""
        # Same as token modifications for now
        self._apply_token_modifications(copy_card, modifications)
    
    def remove_copy_effects(self, card_id: str):
        """Remove copy effects when a copy is removed from the game"""
        if card_id in self.active_copies:
            del self.active_copies[card_id]
    
    def is_copy(self, card: Card) -> bool:
        """Check if a card is a copy"""
        return card.id in self.active_copies
    
    def is_token(self, card: Card) -> bool:
        """Check if a card is a token"""
        return getattr(card, 'is_token', False) or "Token" in getattr(card, 'types', [])
    
    def get_copy_effect(self, card: Card) -> Optional[CopyEffect]:
        """Get the copy effect for a card if it's a copy"""
        return self.active_copies.get(card.id)
    
    def cleanup_temporary_tokens(self, timing: str):
        """Clean up tokens with temporary durations"""
        # This would be called by the game engine at appropriate times
        # e.g., cleanup_temporary_tokens("end_of_turn")
        tokens_to_remove = []
        
        for copy_id, copy_effect in self.active_copies.items():
            if (copy_effect.token_definition and 
                copy_effect.token_definition.temporary_duration == timing):
                tokens_to_remove.append(copy_id)
        
        for token_id in tokens_to_remove:
            self.remove_copy_effects(token_id)
        
        return tokens_to_remove

# Utility functions for common token operations

def create_creature_token(power: int, toughness: int, colors: List[str], 
                         subtypes: List[str] = None, keywords: List[str] = None,
                         name: str = None) -> TokenDefinition:
    """Create a custom creature token definition"""
    if not name:
        color_text = "/".join(colors) if colors else "Colorless"
        subtype_text = " ".join(subtypes) if subtypes else "Creature"
        name = f"{power}/{toughness} {color_text} {subtype_text} Token"
    
    return TokenDefinition(
        name=name,
        types=["Creature", "Token"],
        subtypes=subtypes or [],
        power=power,
        toughness=toughness,
        colors=colors,
        keywords=keywords or []
    )

def create_artifact_token(name: str, text: str = "", subtypes: List[str] = None) -> TokenDefinition:
    """Create a custom artifact token definition"""
    return TokenDefinition(
        name=name,
        types=["Artifact", "Token"],
        subtypes=subtypes or [],
        text=text,
        colors=[]
    )

# Global token engine instance
token_engine = None  # Will be initialized by the game controller

def get_token_engine():
    """Get the global token engine instance"""
    return token_engine

def set_token_engine(engine: TokenAndCopyEngine):
    """Set the global token engine instance"""
    global token_engine
    token_engine = engine
