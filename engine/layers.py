"""
MTG Layers System Implementation
Following Comprehensive Rules 613 - Interaction of Continuous Effects

This module implements the layers system that determines how multiple effects
that modify characteristics interact with each other.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import weakref

class Layer(Enum):
    """
    The seven layers of continuous effects (CR 613.1)
    """
    COPY_EFFECTS = 1          # Layer 1: Copy effects
    CONTROL_EFFECTS = 2       # Layer 2: Control-changing effects  
    TEXT_EFFECTS = 3          # Layer 3: Text-changing effects
    TYPE_EFFECTS = 4          # Layer 4: Type-changing effects
    COLOR_EFFECTS = 5         # Layer 5: Color-changing effects
    ABILITY_EFFECTS = 6       # Layer 6: Ability-adding/removing effects
    POWER_TOUGHNESS = 7       # Layer 7: Power/toughness-changing effects

class PTLayer(Enum):
    """
    Sublayers within Layer 7 for power/toughness effects (CR 613.3)
    """
    CHARACTERISTIC_DEFINING = 7.1   # 7a: Characteristic-defining abilities
    SET_PT = 7.2                    # 7b: Effects that set power/toughness
    MODIFY_PT = 7.3                 # 7c: Effects that modify power/toughness
    COUNTERS = 7.4                  # 7d: Changes from counters
    SWITCH_PT = 7.5                 # 7e: Effects that switch power/toughness

@dataclass
class ContinuousEffect:
    """
    Represents a single continuous effect that can modify characteristics
    """
    source_id: str                    # ID of the source (card, ability, etc.)
    layer: Layer                      # Which layer this effect applies in
    sublayer: Optional[float] = None  # Sublayer for Layer 7 effects
    timestamp: float = 0.0            # When this effect was created
    dependency: Optional[str] = None  # ID of effect this depends on
    
    # Effect application functions
    apply_to_card: Optional[callable] = None
    affects_card: Optional[callable] = None  # Function to check if effect applies
    
    # Power/Toughness specific data
    pt_modification: Optional[Tuple[Optional[int], Optional[int]]] = None  # (+X, +Y)
    pt_setting: Optional[Tuple[Optional[int], Optional[int]]] = None       # Set to (X, Y)
    is_switch_pt: bool = False
    
    # Other characteristic modifications
    type_changes: List[str] = None
    ability_grants: List[str] = None
    color_changes: List[str] = None

@dataclass
class CharacteristicState:
    """
    Represents the current state of a card's characteristics
    """
    card_id: str
    base_power: Optional[int] = None
    base_toughness: Optional[int] = None
    current_power: Optional[int] = None  
    current_toughness: Optional[int] = None
    
    # Other characteristics
    types: Set[str] = None
    colors: Set[str] = None
    abilities: Set[str] = None
    
    # Counters
    plus_one_counters: int = 0
    minus_one_counters: int = 0
    
    def __post_init__(self):
        if self.types is None:
            self.types = set()
        if self.colors is None:
            self.colors = set()
        if self.abilities is None:
            self.abilities = set()

class LayersEngine:
    """
    Manages the application of continuous effects through the layers system
    """
    
    def __init__(self):
        self.effects: List[ContinuousEffect] = []
        self.characteristic_states: Dict[str, CharacteristicState] = {}
        self.timestamp_counter: float = 0.0
        
    def add_effect(self, effect: ContinuousEffect) -> None:
        """Add a continuous effect to the engine"""
        if effect.timestamp == 0.0:
            self.timestamp_counter += 1.0
            effect.timestamp = self.timestamp_counter
        self.effects.append(effect)
        
    def remove_effect(self, source_id: str) -> None:
        """Remove all effects from a given source"""
        self.effects = [e for e in self.effects if e.source_id != source_id]
        
    def get_characteristic_state(self, card) -> CharacteristicState:
        """
        Calculate the current characteristic state of a card after applying
        all continuous effects through the layers system
        """
        card_id = card.id
        
        # Initialize base state from card
        state = CharacteristicState(
            card_id=card_id,
            base_power=card.power,
            base_toughness=card.toughness,
            current_power=card.power,
            current_toughness=card.toughness,
            types=set(card.types) if hasattr(card, 'types') else set(),
            colors=set(card.color_identity) if hasattr(card, 'color_identity') else set()
        )
        
        # Apply effects layer by layer
        self._apply_layer_effects(state, card)
        
        return state
    
    def _apply_layer_effects(self, state: CharacteristicState, card) -> None:
        """Apply all continuous effects in proper layer order"""
        
        # Get effects that apply to this card
        applicable_effects = [e for e in self.effects 
                            if self._effect_applies_to_card(e, card)]
        
        # Sort effects by layer, then sublayer, then timestamp
        applicable_effects.sort(key=lambda e: (
            e.layer.value,
            e.sublayer or 0,
            e.timestamp
        ))
        
        # Apply each layer in order
        for layer in Layer:
            layer_effects = [e for e in applicable_effects if e.layer == layer]
            
            if layer == Layer.POWER_TOUGHNESS:
                self._apply_power_toughness_layer(state, layer_effects, card)
            else:
                self._apply_other_layer(state, layer_effects, card, layer)
    
    def _apply_power_toughness_layer(self, state: CharacteristicState, 
                                   effects: List[ContinuousEffect], card) -> None:
        """Apply Layer 7 (Power/Toughness) effects with proper sublayers"""
        
        # Group by sublayer
        sublayer_effects = {}
        for effect in effects:
            sublayer = effect.sublayer or PTLayer.MODIFY_PT.value
            if sublayer not in sublayer_effects:
                sublayer_effects[sublayer] = []
            sublayer_effects[sublayer].append(effect)
        
        # Apply sublayers in order
        for sublayer_value in sorted(sublayer_effects.keys()):
            sublayer_effects_list = sublayer_effects[sublayer_value]
            
            if sublayer_value == PTLayer.CHARACTERISTIC_DEFINING.value:
                self._apply_characteristic_defining_abilities(state, sublayer_effects_list)
            elif sublayer_value == PTLayer.SET_PT.value:
                self._apply_set_pt_effects(state, sublayer_effects_list)
            elif sublayer_value == PTLayer.MODIFY_PT.value:
                self._apply_modify_pt_effects(state, sublayer_effects_list)
            elif sublayer_value == PTLayer.COUNTERS.value:
                self._apply_counter_effects(state, sublayer_effects_list)
            elif sublayer_value == PTLayer.SWITCH_PT.value:
                self._apply_switch_pt_effects(state, sublayer_effects_list)
    
    def _apply_characteristic_defining_abilities(self, state: CharacteristicState,
                                               effects: List[ContinuousEffect]) -> None:
        """Apply sublayer 7a - Characteristic-defining abilities"""
        for effect in effects:
            if effect.pt_setting:
                power, toughness = effect.pt_setting
                if power is not None:
                    state.current_power = power
                if toughness is not None:
                    state.current_toughness = toughness
    
    def _apply_set_pt_effects(self, state: CharacteristicState,
                            effects: List[ContinuousEffect]) -> None:
        """Apply sublayer 7b - Effects that set power/toughness"""
        for effect in effects:
            if effect.pt_setting:
                power, toughness = effect.pt_setting
                if power is not None:
                    state.current_power = power
                if toughness is not None:
                    state.current_toughness = toughness
    
    def _apply_modify_pt_effects(self, state: CharacteristicState,
                               effects: List[ContinuousEffect]) -> None:
        """Apply sublayer 7c - Effects that modify power/toughness"""
        for effect in effects:
            if effect.pt_modification:
                power_mod, toughness_mod = effect.pt_modification
                if power_mod is not None and state.current_power is not None:
                    state.current_power += power_mod
                if toughness_mod is not None and state.current_toughness is not None:
                    state.current_toughness += toughness_mod
    
    def _apply_counter_effects(self, state: CharacteristicState,
                             effects: List[ContinuousEffect]) -> None:
        """Apply sublayer 7d - Changes from counters"""
        # +1/+1 and -1/-1 counters
        if state.current_power is not None:
            state.current_power += state.plus_one_counters - state.minus_one_counters
        if state.current_toughness is not None:
            state.current_toughness += state.plus_one_counters - state.minus_one_counters
    
    def _apply_switch_pt_effects(self, state: CharacteristicState,
                               effects: List[ContinuousEffect]) -> None:
        """Apply sublayer 7e - Effects that switch power/toughness"""
        # Count number of switch effects (odd number means switched)
        switch_count = len([e for e in effects if e.is_switch_pt])
        if switch_count % 2 == 1:  # Odd number of switches
            state.current_power, state.current_toughness = (
                state.current_toughness, state.current_power
            )
    
    def _apply_other_layer(self, state: CharacteristicState, 
                         effects: List[ContinuousEffect], card, layer: Layer) -> None:
        """Apply non-power/toughness layers"""
        # Sort by timestamp within layer
        effects.sort(key=lambda e: e.timestamp)
        
        for effect in effects:
            if effect.apply_to_card:
                effect.apply_to_card(state, card)
    
    def _effect_applies_to_card(self, effect: ContinuousEffect, card) -> bool:
        """Check if a continuous effect applies to the given card"""
        if effect.affects_card:
            return effect.affects_card(card)
        return True  # Default: effect applies to all cards
    
    def update_counters(self, card_id: str, plus_one_delta: int = 0, minus_one_delta: int = 0):
        """Update +1/+1 and -1/-1 counters on a card"""
        if card_id not in self.characteristic_states:
            self.characteristic_states[card_id] = CharacteristicState(card_id=card_id)
        
        state = self.characteristic_states[card_id]
        state.plus_one_counters += plus_one_delta
        state.minus_one_counters += minus_one_delta
        
        # Handle +1/+1 and -1/-1 counter annihilation (CR 121.3)
        if state.plus_one_counters > 0 and state.minus_one_counters > 0:
            annihilate = min(state.plus_one_counters, state.minus_one_counters)
            state.plus_one_counters -= annihilate
            state.minus_one_counters -= annihilate

# Helper functions for creating common effects

def create_static_buff_effect(source_id: str, power: int, toughness: int,
                            affects_card_func: callable = None) -> ContinuousEffect:
    """Create a static power/toughness modification effect"""
    return ContinuousEffect(
        source_id=source_id,
        layer=Layer.POWER_TOUGHNESS,
        sublayer=PTLayer.MODIFY_PT.value,
        pt_modification=(power, toughness),
        affects_card=affects_card_func
    )

def create_set_pt_effect(source_id: str, power: Optional[int], toughness: Optional[int],
                        affects_card_func: callable = None) -> ContinuousEffect:
    """Create an effect that sets power/toughness to specific values"""
    return ContinuousEffect(
        source_id=source_id,
        layer=Layer.POWER_TOUGHNESS,
        sublayer=PTLayer.SET_PT.value,
        pt_setting=(power, toughness),
        affects_card=affects_card_func
    )

def create_switch_pt_effect(source_id: str, affects_card_func: callable = None) -> ContinuousEffect:
    """Create an effect that switches power and toughness"""
    return ContinuousEffect(
        source_id=source_id,
        layer=Layer.POWER_TOUGHNESS,
        sublayer=PTLayer.SWITCH_PT.value,
        is_switch_pt=True,
        affects_card=affects_card_func
    )

def create_characteristic_defining_effect(source_id: str, power: Optional[int], 
                                        toughness: Optional[int],
                                        affects_card_func: callable = None) -> ContinuousEffect:
    """Create a characteristic-defining ability effect"""
    return ContinuousEffect(
        source_id=source_id,
        layer=Layer.POWER_TOUGHNESS,
        sublayer=PTLayer.CHARACTERISTIC_DEFINING.value,
        pt_setting=(power, toughness),
        affects_card=affects_card_func
    )
