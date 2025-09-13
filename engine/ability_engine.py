"""
MTG Ability Engine - Comprehensive Static, Triggered, and Activated Ability System

This module implements a complete ability system according to MTG Comprehensive Rules:
- CR 112: Spells (including abilities on the stack)
- CR 113: Abilities (static, triggered, activated)
- CR 114: Targets
- CR 115: Special actions
- CR 608: Resolving spells and abilities
- CR 609: Effects
- CR 610: One-shot effects
- CR 611: Continuous effects
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Callable, Any, Union
from enum import Enum
import re
from collections import defaultdict, deque

from .keywords import (
    Ability, TriggeredAbility, ActivatedAbility, StaticKeywordAbility,
    parse_ability, is_triggered_ability, is_activated_ability, is_static_ability
)
from .enhanced_keywords import KeywordProcessor, extract_card_keywords


class AbilityType(Enum):
    """Types of abilities per CR 113.1"""
    STATIC = "static"           # CR 113.3
    TRIGGERED = "triggered"     # CR 113.2  
    ACTIVATED = "activated"     # CR 113.1
    SPELL = "spell"            # Spells on stack
    KEYWORD = "keyword"        # Keyword abilities


class TriggerCondition(Enum):
    """Common trigger conditions for triggered abilities"""
    # Zone change triggers (CR 603.6)
    ENTERS_BATTLEFIELD = "etb"
    LEAVES_BATTLEFIELD = "ltb"
    
    # Combat triggers (CR 506-511)
    ATTACKS = "attacks"
    BLOCKS = "blocks"
    BECOMES_BLOCKED = "becomes_blocked"
    DEALS_COMBAT_DAMAGE = "deals_combat_damage"
    
    # Damage triggers
    DEALS_DAMAGE = "deals_damage"
    TAKES_DAMAGE = "takes_damage"
    
    # State-based triggers
    DIES = "dies"
    DESTROYED = "destroyed"
    
    # Turn/phase triggers
    BEGINNING_OF_UPKEEP = "beginning_of_upkeep"
    END_OF_TURN = "end_of_turn"
    
    # Spell triggers
    CAST_SPELL = "cast_spell"
    SPELL_RESOLVES = "spell_resolves"
    
    # Counter triggers
    COUNTER_ADDED = "counter_added"
    COUNTER_REMOVED = "counter_removed"
    
    # Custom/other
    OTHER = "other"


@dataclass
class TriggerEvent:
    """Represents a game event that can trigger abilities"""
    condition: TriggerCondition
    source: Any = None          # What caused the event
    affected: Any = None        # What was affected by the event
    controller: int = -1        # Which player controls the source
    data: Dict[str, Any] = field(default_factory=dict)  # Additional event data
    timestamp: float = 0.0      # When the event occurred


@dataclass 
class AbilityInstance:
    """A specific instance of an ability on the stack or in effect"""
    source_card: Any = None             # Card that has this ability
    ability_def: Ability = None         # The ability definition
    controller: int = -1                # Player who controls the ability
    targets: List[Any] = field(default_factory=list)  # Chosen targets
    modes: List[str] = field(default_factory=list)    # Chosen modes (for modal spells)
    x_value: int = 0                    # Value of X if applicable
    additional_costs_paid: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0              # When this instance was created
    resolved: bool = False              # Whether this has resolved


class AbilityEngine:
    """Core engine for managing all ability types"""
    
    def __init__(self, game_state):
        self.game = game_state
        self.keyword_processor = KeywordProcessor()
        
        # Ability tracking
        self.static_abilities: Dict[str, List[AbilityInstance]] = defaultdict(list)  # card_id -> abilities
        self.triggered_abilities: Dict[str, List[AbilityInstance]] = defaultdict(list)
        self.activated_abilities: Dict[str, List[AbilityInstance]] = defaultdict(list)
        
        # Event system
        self.trigger_listeners: Dict[TriggerCondition, List[Callable]] = defaultdict(list)
        self.pending_events: deque = deque()
        self.triggered_queue: List[AbilityInstance] = []
        
        # Stack for triggered/activated abilities (separate from spell stack)
        self.ability_stack: List[AbilityInstance] = []
        
        # State tracking
        self.continuous_effects: List[AbilityInstance] = []
        self.replacement_effects: List[AbilityInstance] = []
        self.prevention_effects: List[AbilityInstance] = []
        
        # Ability handlers
        self.ability_handlers: Dict[str, Callable] = {}
        self.effect_handlers: Dict[str, Callable] = {}
        
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default handlers for common abilities"""
        
        # ETB trigger handler
        def handle_etb_trigger(instance: AbilityInstance, event: TriggerEvent):
            effect_text = instance.ability_def.effect_text.lower()
            
            # Common ETB effects
            if "draw" in effect_text and "card" in effect_text:
                num_match = re.search(r'draw (\d+)', effect_text)
                if num_match:
                    cards_to_draw = int(num_match.group(1))
                    self._draw_cards(instance.controller, cards_to_draw)
                else:
                    self._draw_cards(instance.controller, 1)
            
            if "gain" in effect_text and "life" in effect_text:
                life_match = re.search(r'gain (\d+) life', effect_text)
                if life_match:
                    life_to_gain = int(life_match.group(1))
                    self._gain_life(instance.controller, life_to_gain)
            
            if "deal" in effect_text and "damage" in effect_text:
                damage_match = re.search(r'deal (\d+) damage', effect_text)
                if damage_match:
                    damage_amount = int(damage_match.group(1))
                    # Would need target selection for actual implementation
                    self._deal_damage(instance.source_card, None, damage_amount)
        
        self.ability_handlers["etb"] = handle_etb_trigger
        
        # Activated ability handler
        def handle_activated_ability(instance: AbilityInstance):
            effect_text = instance.ability_def.effect_text.lower()
            
            # Tap for mana abilities
            if "add" in effect_text and any(color in effect_text for color in ['w', 'u', 'b', 'r', 'g', 'c']):
                mana_match = re.search(r'add \{([wubrg])\}', effect_text)
                if mana_match:
                    color = mana_match.group(1).upper()
                    self._add_mana(instance.controller, color, 1)
            
            # Simple damage abilities
            if "deal" in effect_text and "damage" in effect_text:
                damage_match = re.search(r'deal (\d+) damage', effect_text)
                if damage_match and instance.targets:
                    damage_amount = int(damage_match.group(1))
                    self._deal_damage(instance.source_card, instance.targets[0], damage_amount)
        
        self.ability_handlers["activated"] = handle_activated_ability
    
    def register_card(self, card) -> bool:
        """Register a card and parse all its abilities"""
        if not hasattr(card, 'text') or not card.text:
            return False
        
        # Parse abilities from card text
        abilities = self._parse_card_abilities(card.text)
        
        if not abilities:
            return False
        
        # Store parsed abilities on the card
        if not hasattr(card, 'parsed_abilities'):
            card.parsed_abilities = []
        
        card.parsed_abilities.extend(abilities)
        
        # Register abilities by type
        for ability in abilities:
            instance = AbilityInstance(
                source_card=card,
                ability_def=ability,
                controller=getattr(card, 'controller_id', 0)
            )
            
            if isinstance(ability, StaticKeywordAbility) or ability.kind == 'static':
                self.static_abilities[card.id].append(instance)
                if ability.kind == 'static':
                    self.continuous_effects.append(instance)
            
            elif isinstance(ability, TriggeredAbility) or ability.kind == 'triggered':
                self.triggered_abilities[card.id].append(instance)
                self._register_trigger_listener(instance)
            
            elif isinstance(ability, ActivatedAbility) or ability.kind == 'activated':
                self.activated_abilities[card.id].append(instance)
        
        return True
    
    def _parse_card_abilities(self, card_text: str) -> List[Ability]:
        """Parse all abilities from card text"""
        abilities = []
        
        # Split text into sentences
        sentences = re.split(r'[.!](?:\s|$)', card_text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Try to parse as specific ability type
            ability = parse_ability(sentence)
            if ability:
                abilities.append(ability)
                continue
            
            # Check for common triggered ability patterns
            if self._is_triggered_pattern(sentence):
                ability = self._parse_triggered_ability(sentence)
                if ability:
                    abilities.append(ability)
                    continue
            
            # Check for activated ability patterns  
            if self._is_activated_pattern(sentence):
                ability = self._parse_activated_ability(sentence)
                if ability:
                    abilities.append(ability)
                    continue
            
            # Check for static ability patterns
            if self._is_static_pattern(sentence):
                ability = self._parse_static_ability(sentence)
                if ability:
                    abilities.append(ability)
        
        return abilities
    
    def _is_triggered_pattern(self, text: str) -> bool:
        """Check if text matches triggered ability patterns"""
        text_lower = text.lower()
        trigger_words = ['when', 'whenever', 'at the beginning', 'at the end']
        return any(text_lower.startswith(word) for word in trigger_words)
    
    def _is_activated_pattern(self, text: str) -> bool:
        """Check if text matches activated ability patterns"""
        # Look for cost:effect pattern
        return ':' in text and ('{' in text or 'tap' in text.lower())
    
    def _is_static_pattern(self, text: str) -> bool:
        """Check if text matches static ability patterns"""
        text_lower = text.lower()
        # Static abilities often contain certain keywords
        static_indicators = [
            'gets +', 'gets -', 'have', 'has', 'can\'t', 'cannot', 
            'must', 'may not', 'if', 'as long as'
        ]
        return any(indicator in text_lower for indicator in static_indicators)
    
    def _parse_triggered_ability(self, text: str) -> Optional[TriggeredAbility]:
        """Parse triggered ability from text"""
        # ETB triggers
        if "enters the battlefield" in text.lower():
            match = re.match(r'when(?:ever)?\s+.*?enters the battlefield,?\s*(.+)', text, re.IGNORECASE)
            if match:
                return TriggeredAbility(
                    kind='triggered',
                    raw_text=text,
                    trigger='ETB',
                    effect_text=match.group(1).strip()
                )
        
        # Attack triggers
        if "attacks" in text.lower():
            match = re.match(r'when(?:ever)?\s+.*?attacks,?\s*(.+)', text, re.IGNORECASE)
            if match:
                return TriggeredAbility(
                    kind='triggered',
                    raw_text=text,
                    trigger='ATTACK',
                    effect_text=match.group(1).strip()
                )
        
        # Death triggers
        if "dies" in text.lower():
            match = re.match(r'when(?:ever)?\s+.*?dies,?\s*(.+)', text, re.IGNORECASE)
            if match:
                return TriggeredAbility(
                    kind='triggered',
                    raw_text=text,
                    trigger='DEATH',
                    effect_text=match.group(1).strip()
                )
        
        # Beginning of upkeep
        if "beginning of" in text.lower() and "upkeep" in text.lower():
            match = re.match(r'at the beginning of.*?upkeep,?\s*(.+)', text, re.IGNORECASE)
            if match:
                return TriggeredAbility(
                    kind='triggered',
                    raw_text=text,
                    trigger='UPKEEP',
                    effect_text=match.group(1).strip()
                )
        
        # Generic triggered ability - only use if no specific pattern matched
        return None
        
        return None
    
    def _parse_activated_ability(self, text: str) -> Optional[ActivatedAbility]:
        """Parse activated ability from text"""
        match = re.match(r'^(.+?):\s*(.+)$', text)
        if not match:
            return None
        
        cost_text = match.group(1).strip()
        effect_text = match.group(2).strip()
        
        # Parse mana cost
        mana_cost = {}
        tap_cost = False
        
        # Check for tap cost
        if '{t}' in cost_text.lower() or 'tap' in cost_text.lower():
            tap_cost = True
        
        # Parse mana symbols
        mana_matches = re.findall(r'\{([^}]+)\}', cost_text)
        for symbol in mana_matches:
            if symbol.upper() != 'T':  # Skip tap symbol
                mana_cost[symbol.upper()] = mana_cost.get(symbol.upper(), 0) + 1
        
        # Check for targeting
        needs_target = 'target' in effect_text.lower()
        target_hint = None
        if needs_target:
            if 'target creature' in effect_text.lower():
                target_hint = 'creature'
            elif 'target player' in effect_text.lower():
                target_hint = 'player'
            elif 'target permanent' in effect_text.lower():
                target_hint = 'permanent'
        
        return ActivatedAbility(
            kind='activated',
            raw_text=text,
            raw_cost=cost_text,
            mana_cost=mana_cost,
            tap_cost=tap_cost,
            effect_text=effect_text,
            needs_target=needs_target,
            target_hint=target_hint
        )
    
    def _parse_static_ability(self, text: str) -> Optional[Ability]:
        """Parse static ability from text"""
        # For now, create a generic static ability
        return Ability(kind='static', raw_text=text)
    
    def _register_trigger_listener(self, instance: AbilityInstance):
        """Register a triggered ability to listen for appropriate events"""
        trigger_type = instance.ability_def.trigger.upper()
        
        # Map trigger types to conditions
        trigger_mapping = {
            'ETB': TriggerCondition.ENTERS_BATTLEFIELD,
            'ATTACK': TriggerCondition.ATTACKS,
            'DEATH': TriggerCondition.DIES,
            'UPKEEP': TriggerCondition.BEGINNING_OF_UPKEEP,
        }
        
        condition = trigger_mapping.get(trigger_type, TriggerCondition.OTHER)
        
        def listener(event: TriggerEvent):
            if self._should_trigger(instance, event):
                self._queue_triggered_ability(instance, event)
        
        self.trigger_listeners[condition].append(listener)
    
    def _should_trigger(self, instance: AbilityInstance, event: TriggerEvent) -> bool:
        """Check if a triggered ability should trigger for an event"""
        # Check if source card is on battlefield (unless it's LTB trigger)
        if (instance.ability_def.trigger != 'LTB' and 
            not self._is_on_battlefield(instance.source_card)):
            return False
        
        # Check trigger-specific conditions
        trigger_type = instance.ability_def.trigger.upper()
        
        if trigger_type == 'ETB':
            return (event.condition == TriggerCondition.ENTERS_BATTLEFIELD and
                    event.affected == instance.source_card)
        
        elif trigger_type == 'ATTACK':
            return (event.condition == TriggerCondition.ATTACKS and
                    event.source == instance.source_card)
        
        elif trigger_type == 'DEATH':
            return (event.condition == TriggerCondition.DIES and
                    event.affected == instance.source_card)
        
        elif trigger_type == 'UPKEEP':
            return (event.condition == TriggerCondition.BEGINNING_OF_UPKEEP and
                    event.controller == instance.controller)
        
        return False
    
    def _queue_triggered_ability(self, instance: AbilityInstance, event: TriggerEvent):
        """Queue a triggered ability for resolution"""
        # Create a copy for the stack
        stack_instance = AbilityInstance(
            source_card=instance.source_card,
            ability_def=instance.ability_def,
            controller=instance.controller,
            timestamp=len(self.triggered_queue)  # Simple timestamp
        )
        
        self.triggered_queue.append(stack_instance)
    
    def emit_event(self, condition: TriggerCondition, **kwargs):
        """Emit a game event that may trigger abilities"""
        event = TriggerEvent(
            condition=condition,
            **kwargs
        )
        
        # Notify all listeners for this condition
        for listener in self.trigger_listeners[condition]:
            try:
                listener(event)
            except Exception as e:
                print(f"Error in trigger listener: {e}")
    
    def process_triggered_abilities(self):
        """Process all queued triggered abilities"""
        while self.triggered_queue:
            instance = self.triggered_queue.pop(0)
            self._resolve_triggered_ability(instance)
    
    def _resolve_triggered_ability(self, instance: AbilityInstance):
        """Resolve a triggered ability"""
        trigger_type = instance.ability_def.trigger.lower()
        
        if "etb" in trigger_type.lower() or trigger_type == "ETB":
            self.ability_handlers["etb"](instance, None)
        elif trigger_type in self.ability_handlers:
            # Use specific handler if available
            self.ability_handlers[trigger_type](instance, None)
        else:
            # Generic effect processing
            effect_text = instance.ability_def.effect_text.lower()
            
            # Handle common effects
            if "draw" in effect_text:
                num_match = re.search(r'draw (\d+)', effect_text)
                if num_match:
                    self._draw_cards(instance.controller, int(num_match.group(1)))
                else:
                    self._draw_cards(instance.controller, 1)
            
            if "gain" in effect_text and "life" in effect_text:
                life_match = re.search(r'gain (\d+) life', effect_text)
                if life_match:
                    self._gain_life(instance.controller, int(life_match.group(1)))
    
    def can_activate_ability(self, player_id: int, card, ability_index: int) -> bool:
        """Check if a player can activate a specific ability on a card"""
        if card.id not in self.activated_abilities:
            return False
        
        if ability_index >= len(self.activated_abilities[card.id]):
            return False
        
        instance = self.activated_abilities[card.id][ability_index]
        ability = instance.ability_def
        
        # Check timing restrictions
        if not self._can_activate_at_current_timing(ability):
            return False
        
        # Check costs
        if not self._can_pay_activation_costs(player_id, card, ability):
            return False
        
        return True
    
    def activate_ability(self, player_id: int, card, ability_index: int, targets: List[Any] = None) -> bool:
        """Activate an activated ability"""
        if not self.can_activate_ability(player_id, card, ability_index):
            return False
        
        instance = self.activated_abilities[card.id][ability_index]
        ability = instance.ability_def
        
        # Pay costs
        if not self._pay_activation_costs(player_id, card, ability):
            return False
        
        # Create stack instance
        stack_instance = AbilityInstance(
            source_card=card,
            ability_def=ability,
            controller=player_id,
            targets=targets or [],
            timestamp=len(self.ability_stack)
        )
        
        # Add to stack (in real implementation, would use game's stack)
        self.ability_stack.append(stack_instance)
        
        return True
    
    def get_static_effects(self, card) -> List[AbilityInstance]:
        """Get all static effects from a card"""
        return self.static_abilities.get(card.id, [])
    
    def get_activated_abilities(self, card) -> List[AbilityInstance]:
        """Get all activated abilities from a card"""
        return self.activated_abilities.get(card.id, [])
    
    def get_triggered_abilities(self, card) -> List[AbilityInstance]:
        """Get all triggered abilities from a card"""
        return self.triggered_abilities.get(card.id, [])
    
    # Helper methods
    
    def _is_on_battlefield(self, card) -> bool:
        """Check if a card is on the battlefield"""
        for player in self.game.players:
            for perm in player.battlefield:
                if hasattr(perm, 'card') and perm.card == card:
                    return True
                elif perm == card:
                    return True
        return False
    
    def _can_activate_at_current_timing(self, ability: ActivatedAbility) -> bool:
        """Check timing restrictions for activated abilities"""
        # For now, assume all activated abilities can be activated
        # In full implementation, would check for sorcery-speed restrictions
        return True
    
    def _can_pay_activation_costs(self, player_id: int, card, ability: ActivatedAbility) -> bool:
        """Check if player can pay activation costs"""
        player = self.game.players[player_id]
        
        # Check mana cost
        if hasattr(player, 'mana_pool') and ability.mana_cost:
            # Calculate total mana needed
            total_needed = sum(ability.mana_cost.values())
            total_available = sum(player.mana_pool.pool.values()) if hasattr(player.mana_pool, 'pool') else 0
            if total_available < total_needed:
                return False
        
        # Check tap cost
        if ability.tap_cost:
            perm = self._find_permanent(card)
            if not perm or perm.tapped:
                return False
        
        return True
    
    def _pay_activation_costs(self, player_id: int, card, ability: ActivatedAbility) -> bool:
        """Pay the costs for activating an ability"""
        player = self.game.players[player_id]
        
        # Pay mana cost
        if hasattr(player, 'mana_pool') and ability.mana_cost:
            # Simple mana payment for now
            total_needed = sum(ability.mana_cost.values())
            total_available = sum(player.mana_pool.pool.values()) if hasattr(player.mana_pool, 'pool') else 0
            if total_available < total_needed:
                return False
            # Deduct mana (simplified)
            if hasattr(player.mana_pool, 'pool'):
                # Remove generic mana first
                remaining = total_needed
                for color in list(player.mana_pool.pool.keys()):
                    if remaining <= 0:
                        break
                    available = player.mana_pool.pool[color]
                    to_remove = min(available, remaining)
                    player.mana_pool.pool[color] -= to_remove
                    remaining -= to_remove
        
        # Pay tap cost
        if ability.tap_cost:
            perm = self._find_permanent(card)
            if not perm or perm.tapped:
                return False
            perm.tapped = True
        
        return True
    
    def _find_permanent(self, card):
        """Find the permanent for a card"""
        for player in self.game.players:
            for perm in player.battlefield:
                if hasattr(perm, 'card') and perm.card == card:
                    return perm
                elif perm == card:
                    return perm
        return None
    
    # Effect helper methods (would be expanded in full implementation)
    
    def _draw_cards(self, player_id: int, num_cards: int):
        """Helper to draw cards"""
        if 0 <= player_id < len(self.game.players):
            player = self.game.players[player_id]
            for _ in range(num_cards):
                if player.library:
                    player.hand.append(player.library.pop(0))
    
    def _gain_life(self, player_id: int, amount: int):
        """Helper to gain life"""
        if 0 <= player_id < len(self.game.players):
            self.game.players[player_id].life += amount
    
    def _deal_damage(self, source, target, amount: int):
        """Helper to deal damage"""
        # Would implement full damage rules in complete implementation
        pass
    
    def _add_mana(self, player_id: int, color: str, amount: int):
        """Helper to add mana to pool"""
        if 0 <= player_id < len(self.game.players):
            player = self.game.players[player_id]
            if hasattr(player, 'mana_pool'):
                player.mana_pool.add(color, amount)


# Global ability engine instance (will be set by game controller)
ability_engine: Optional[AbilityEngine] = None


def set_ability_engine(engine: AbilityEngine):
    """Set the global ability engine instance"""
    global ability_engine
    ability_engine = engine


def get_ability_engine() -> Optional[AbilityEngine]:
    """Get the global ability engine instance"""
    return ability_engine


def emit_game_event(condition: TriggerCondition, **kwargs):
    """Emit a game event through the ability engine"""
    if ability_engine:
        ability_engine.emit_event(condition, **kwargs)


def register_card_abilities(card) -> bool:
    """Register a card's abilities with the ability engine"""
    if ability_engine:
        return ability_engine.register_card(card)
    return False


def process_all_triggers():
    """Process all pending triggered abilities"""
    if ability_engine:
        ability_engine.process_triggered_abilities()
