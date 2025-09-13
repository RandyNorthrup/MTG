"""MTG Spell Casting Timing System - CR 601 & 307 Implementation

This module implements the complete spell casting timing system according to 
Magic: The Gathering Comprehensive Rules 601 (Casting Spells) and 307 (Sorceries).

Ensures proper timing restrictions and the complete casting process.
"""

from typing import TYPE_CHECKING, Optional, List, Dict, Any
from enum import Enum

if TYPE_CHECKING:
    from .game_state import GameState
    from .card_engine import Card

class CastingRestriction(Enum):
    """Types of casting restrictions"""
    SORCERY_SPEED = "sorcery_speed"  # CR 307.1
    INSTANT_SPEED = "instant_speed"   # CR 304.1 
    SPECIAL_ACTION = "special_action" # CR 116.2
    NO_RESTRICTION = "no_restriction"

class CastingStep(Enum):
    """Steps in the casting process per CR 601.2"""
    ANNOUNCE = "announce"           # CR 601.2a
    CHOOSE_MODES = "choose_modes"   # CR 601.2b
    CHOOSE_TARGETS = "choose_targets" # CR 601.2c
    DISTRIBUTE_EFFECTS = "distribute" # CR 601.2d
    DETERMINE_COSTS = "determine_costs" # CR 601.2e
    PAY_COSTS = "pay_costs"         # CR 601.2f/g/h
    COMPLETE = "complete"           # Spell goes to stack

class TimingValidator:
    """Validates spell casting timing per MTG rules"""
    
    def __init__(self, game: 'GameState'):
        self.game = game
    
    def can_cast_spell(self, player_id: int, card: 'Card') -> tuple[bool, str]:
        """Check if a spell can be cast right now (CR 601.1)
        
        Returns:
            (can_cast, reason) - True if can cast, False with reason if not
        """
        # Check basic preconditions
        if not self._has_priority(player_id):
            return False, "Player does not have priority"
        
        # Check timing restrictions based on card type
        restriction = self._get_casting_restriction(card)
        
        if restriction == CastingRestriction.SORCERY_SPEED:
            return self._can_cast_sorcery_speed(player_id)
        elif restriction == CastingRestriction.INSTANT_SPEED:
            return self._can_cast_instant_speed(player_id)
        elif restriction == CastingRestriction.SPECIAL_ACTION:
            return self._can_take_special_action(player_id)
        else:
            # No timing restrictions (like lands, but they use special rules)
            return True, "No timing restrictions"
    
    def can_play_land(self, player_id: int, card: 'Card') -> tuple[bool, str]:
        """Check if a land can be played (CR 305.1)
        
        Land play is a special action, not spell casting
        """
        if not self._has_priority(player_id):
            return False, "Player does not have priority"
            
        if not self._is_main_phase():
            return False, "Not in a main phase"
            
        if not self._is_active_player(player_id):
            return False, "Only active player can play lands"
            
        if not self._stack_empty():
            return False, "Stack is not empty"
            
        if not self._can_play_land_this_turn(player_id):
            return False, "Already played a land this turn"
            
        return True, "Can play land"
    
    def _get_casting_restriction(self, card: 'Card') -> CastingRestriction:
        """Determine what timing restrictions apply to this card"""
        card_types = getattr(card, 'types', [])
        
        if 'Sorcery' in card_types:
            return CastingRestriction.SORCERY_SPEED
        elif 'Creature' in card_types:
            return CastingRestriction.SORCERY_SPEED  # CR 302.1
        elif 'Artifact' in card_types:
            return CastingRestriction.SORCERY_SPEED  # CR 301.1
        elif 'Enchantment' in card_types:
            return CastingRestriction.SORCERY_SPEED  # CR 303.1
        elif 'Planeswalker' in card_types:
            return CastingRestriction.SORCERY_SPEED  # CR 306.1
        elif 'Instant' in card_types:
            return CastingRestriction.INSTANT_SPEED
        elif 'Land' in card_types:
            return CastingRestriction.SPECIAL_ACTION
        else:
            return CastingRestriction.NO_RESTRICTION
    
    def _can_cast_sorcery_speed(self, player_id: int) -> tuple[bool, str]:
        """Check sorcery speed casting requirements (CR 307.1)"""
        if not self._is_active_player(player_id):
            return False, "Only active player can cast sorcery-speed spells"
            
        if not self._is_main_phase():
            return False, "Can only cast during main phase"
            
        if not self._stack_empty():
            return False, "Stack must be empty"
            
        return True, "Sorcery speed conditions met"
    
    def _can_cast_instant_speed(self, player_id: int) -> tuple[bool, str]:
        """Check instant speed casting requirements (CR 304.1)"""
        # Instants can be cast any time the player has priority
        # (which we already checked)
        return True, "Instant speed conditions met"
    
    def _can_take_special_action(self, player_id: int) -> tuple[bool, str]:
        """Check special action requirements (CR 116.2)"""
        # Special actions like playing lands have their own rules
        return True, "Special action conditions met"
    
    # Helper methods to check game state
    
    def _has_priority(self, player_id: int) -> bool:
        """Check if player currently has priority"""
        if hasattr(self.game, 'priority_manager'):
            return self.game.priority_manager.can_take_action(player_id)
        # Fallback: assume active player has priority
        return player_id == self.game.active_player
    
    def _is_active_player(self, player_id: int) -> bool:
        """Check if player is the active player"""
        return player_id == self.game.active_player
    
    def _is_main_phase(self) -> bool:
        """Check if currently in a main phase"""
        current_phase = getattr(self.game, 'phase', '')
        return current_phase in ['MAIN1', 'MAIN2', 'PRECOMBAT_MAIN', 'POSTCOMBAT_MAIN']
    
    def _stack_empty(self) -> bool:
        """Check if the stack is empty"""
        if not hasattr(self.game, 'stack'):
            return True
        stack = self.game.stack
        if hasattr(stack, 'items'):
            return len(stack.items()) == 0
        elif hasattr(stack, '_items'):
            return len(stack._items) == 0
        return True
    
    def _can_play_land_this_turn(self, player_id: int) -> bool:
        """Check if player can still play a land this turn"""
        land_played = getattr(self.game, 'land_played_this_turn', {}).get(player_id, False)
        return not land_played

class CastingProcessor:
    """Handles the complete spell casting process per CR 601.2"""
    
    def __init__(self, game: 'GameState'):
        self.game = game
        self.timing_validator = TimingValidator(game)
        
    def cast_spell(self, player_id: int, card: 'Card', **casting_choices) -> tuple[bool, str]:
        """Execute complete spell casting process (CR 601.2)
        
        Args:
            player_id: Player attempting to cast
            card: Card being cast
            **casting_choices: Targets, modes, etc.
            
        Returns:
            (success, message) - True if cast successfully, False with reason
        """
        # CR 601.1: Check timing restrictions
        can_cast, reason = self.timing_validator.can_cast_spell(player_id, card)
        if not can_cast:
            return False, f"Cannot cast: {reason}"
        
        # CR 601.2: Follow complete casting process
        try:
            # Step 1: Announce the spell (CR 601.2a)
            if not self._announce_spell(player_id, card):
                return False, "Failed to announce spell"
            
            # Step 2: Choose modes if modal (CR 601.2b)
            modes = casting_choices.get('modes', [])
            if not self._choose_modes(card, modes):
                return False, "Invalid mode selection"
            
            # Step 3: Choose targets (CR 601.2c)
            targets = casting_choices.get('targets', [])
            if not self._choose_targets(card, targets, modes):
                return False, "Invalid target selection"
            
            # Step 4: Distribute effects (CR 601.2d)
            if not self._distribute_effects(card, targets):
                return False, "Failed to distribute effects"
            
            # Step 5: Determine total cost (CR 601.2e)
            total_cost = self._determine_total_cost(card, player_id)
            
            # Step 6: Pay costs (CR 601.2f/g/h)
            if not self._pay_costs(player_id, total_cost):
                return False, "Cannot pay costs"
            
            # Step 7: Complete casting - spell goes to stack
            self._complete_casting(player_id, card, targets, modes)
            
            return True, "Spell cast successfully"
            
        except Exception as e:
            # CR 601.3: If any step fails, spell is illegal
            self._handle_illegal_spell(player_id, card)
            return False, f"Illegal spell: {e}"
    
    def play_land(self, player_id: int, card: 'Card') -> tuple[bool, str]:
        """Handle land play (special action, not spell casting)"""
        can_play, reason = self.timing_validator.can_play_land(player_id, card)
        if not can_play:
            return False, reason
            
        # Execute land play
        player = self.game.players[player_id]
        if card not in player.hand:
            return False, "Card not in hand"
            
        player.hand.remove(card)
        from .card_engine import Permanent
        player.battlefield.append(Permanent(card=card, summoning_sick=False))
        
        # Mark land as played this turn
        if not hasattr(self.game, 'land_played_this_turn'):
            self.game.land_played_this_turn = {}
        self.game.land_played_this_turn[player_id] = True
        
        return True, "Land played successfully"
    
    # Casting process steps (CR 601.2)
    
    def _announce_spell(self, player_id: int, card: 'Card') -> bool:
        """CR 601.2a: Announce the spell"""
        # Move card from hand to stack zone
        player = self.game.players[player_id]
        if card not in player.hand:
            return False
        # Don't remove from hand yet - wait until costs are paid
        return True
    
    def _choose_modes(self, card: 'Card', modes: List[str]) -> bool:
        """CR 601.2b: Choose modes for modal spells"""
        # Check if card is modal and modes are valid
        # Simplified implementation
        return True
    
    def _choose_targets(self, card: 'Card', targets: List[Any], modes: List[str]) -> bool:
        """CR 601.2c: Choose targets"""
        # Validate targets are legal
        # Check targeting restrictions
        # Simplified implementation
        return True
    
    def _distribute_effects(self, card: 'Card', targets: List[Any]) -> bool:
        """CR 601.2d: Distribute damage, counters, etc."""
        # Handle cards that distribute effects among targets
        return True
    
    def _determine_total_cost(self, card: 'Card', player_id: int) -> Dict[str, int]:
        """CR 601.2e: Determine total cost including additional costs"""
        base_cost = getattr(card, 'mana_cost_str', '') or ''
        
        # Parse base cost
        from .mana import parse_mana_cost
        total_cost = parse_mana_cost(base_cost)
        
        # Add commander tax if applicable
        if getattr(card, 'is_commander', False):
            player = self.game.players[player_id]
            if hasattr(player, 'commander_tracker'):
                tax = player.commander_tracker.tax_for(card.id)
                total_cost['C'] = total_cost.get('C', 0) + tax
        
        # Additional costs would be added here
        # (kicker, X costs, etc.)
        
        return total_cost
    
    def _pay_costs(self, player_id: int, costs: Dict[str, int]) -> bool:
        """CR 601.2f/g/h: Pay all costs"""
        player = self.game.players[player_id]
        
        # Check if player can pay
        if not hasattr(player, 'mana_pool'):
            from .mana import ManaPool
            player.mana_pool = ManaPool()
        
        # Try to pay with current pool + autotapping lands
        return player.mana_pool.cast_with_pool_and_lands(costs, player.battlefield)
    
    def _complete_casting(self, player_id: int, card: 'Card', targets: List[Any], modes: List[str]):
        """Complete the casting process - spell goes to stack"""
        player = self.game.players[player_id]
        
        # Remove card from hand now that costs are paid
        if card in player.hand:
            player.hand.remove(card)
        
        # Add to stack
        if hasattr(self.game, 'stack'):
            from .stack import StackItem
            
            def spell_effect(game, stack_item):
                # Execute the spell's effect
                self._resolve_spell_effect(card, player_id, targets, modes)
            
            stack_item = StackItem(
                source=card,
                controller=player_id,
                label=f"{card.name}",
                resolve_fn=spell_effect,
                targets=targets
            )
            self.game.stack.push(stack_item)
    
    def _resolve_spell_effect(self, card: 'Card', controller_id: int, targets: List[Any], modes: List[str]):
        """Resolve the spell's effect"""
        # This would contain the actual spell resolution logic
        # For now, just move non-permanents to graveyard
        card_types = getattr(card, 'types', [])
        
        if any(t in card_types for t in ['Creature', 'Artifact', 'Enchantment', 'Planeswalker']):
            # Permanent spell - goes to battlefield
            controller = self.game.players[controller_id]
            from .card_engine import Permanent
            controller.battlefield.append(Permanent(card=card))
        else:
            # Non-permanent - goes to graveyard after resolving
            controller = self.game.players[controller_id]
            controller.graveyard.append(card)
    
    def _handle_illegal_spell(self, player_id: int, card: 'Card'):
        """CR 601.3: Handle illegal spell - return to hand"""
        # Spell is illegal, return to hand with no effect
        player = self.game.players[player_id]
        if card not in player.hand:
            player.hand.append(card)

def init_spell_timing(game: 'GameState') -> CastingProcessor:
    """Initialize spell timing system for a game"""
    processor = CastingProcessor(game)
    game.casting_processor = processor
    
    # Add convenience methods to game
    def can_cast_spell(player_id: int, card):
        return processor.timing_validator.can_cast_spell(player_id, card)
    
    def cast_spell(player_id: int, card, **choices):
        return processor.cast_spell(player_id, card, **choices)
        
    def play_land(player_id: int, card):
        return processor.play_land(player_id, card)
    
    game.can_cast_spell = can_cast_spell
    game.cast_spell_with_timing = cast_spell
    game.play_land_with_timing = play_land
    
    return processor
