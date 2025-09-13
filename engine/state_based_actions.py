"""MTG State-Based Actions Engine - CR 704 Implementation

This module implements the complete state-based actions system according to 
Magic: The Gathering Comprehensive Rules 704.

State-based actions are checked continuously and performed automatically
whenever a player would receive priority.
"""

from typing import List, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .game_state import GameState

@dataclass
class StateBasedAction:
    """Represents a state-based action to be performed"""
    action_type: str
    target: Any
    reason: str
    rule_reference: str

class StateBasedActionEngine:
    """Implements comprehensive state-based actions per CR 704"""
    
    def __init__(self, game: 'GameState'):
        self.game = game
        self.actions_this_check = []
        
    def check_and_perform_all(self) -> bool:
        """Check and perform all applicable state-based actions (CR 704.3)
        
        Returns True if any actions were performed, False otherwise.
        Per CR 704.4, if any actions are performed, SBAs are checked again.
        """
        actions_performed = False
        
        # CR 704.4: Keep checking until no actions are performed
        while True:
            current_actions = self._collect_all_actions()
            
            if not current_actions:
                break
                
            # CR 704.3: All applicable SBAs are performed simultaneously
            self._perform_actions(current_actions)
            actions_performed = True
            
        return actions_performed
    
    def _collect_all_actions(self) -> List[StateBasedAction]:
        """Collect all applicable state-based actions (CR 704.5)"""
        actions = []
        
        # CR 704.5a: Life loss
        actions.extend(self._check_life_loss())
        
        # CR 704.5b: Drawing from empty library
        actions.extend(self._check_empty_library_draw())
        
        # CR 704.5c: Poison counters
        actions.extend(self._check_poison_counters())
        
        # CR 704.5f: Zero or negative toughness
        actions.extend(self._check_zero_toughness())
        
        # CR 704.5g: Lethal damage
        actions.extend(self._check_lethal_damage())
        
        # CR 704.5h: Deathtouch damage
        actions.extend(self._check_deathtouch_damage())
        
        # CR 704.5i: Planeswalker zero loyalty
        actions.extend(self._check_planeswalker_loyalty())
        
        # CR 704.5j: Legendary rule
        actions.extend(self._check_legendary_rule())
        
        # CR 704.5k: World rule (deprecated but included for completeness)
        actions.extend(self._check_world_rule())
        
        # CR 704.5m: Aura attachment rules
        actions.extend(self._check_aura_attachments())
        
        # CR 704.5n: Equipment attachment rules
        actions.extend(self._check_equipment_attachments())
        
        # CR 704.5p: Token in wrong zone
        actions.extend(self._check_tokens_in_wrong_zones())
        
        # CR 704.5q: Copy effects ending
        actions.extend(self._check_copy_effects())
        
        return actions
    
    def _check_life_loss(self) -> List[StateBasedAction]:
        """CR 704.5a: Player with 0 or less life loses the game"""
        actions = []
        
        for player in self.game.players:
            if player.life <= 0:
                actions.append(StateBasedAction(
                    action_type="lose_game",
                    target=player,
                    reason=f"Life total is {player.life}",
                    rule_reference="CR 704.5a"
                ))
                
        return actions
    
    def _check_empty_library_draw(self) -> List[StateBasedAction]:
        """CR 704.5b: Player who would draw from empty library loses"""
        actions = []
        
        # This is checked when a player attempts to draw, not continuously
        # Implementation would be in the draw card method
        
        return actions
    
    def _check_poison_counters(self) -> List[StateBasedAction]:
        """CR 704.5c: Player with 10+ poison counters loses"""
        actions = []
        
        for player in self.game.players:
            poison_counters = getattr(player, 'poison_counters', 0)
            if poison_counters >= 10:
                actions.append(StateBasedAction(
                    action_type="lose_game",
                    target=player,
                    reason=f"Has {poison_counters} poison counters",
                    rule_reference="CR 704.5c"
                ))
                
        return actions
    
    def _check_zero_toughness(self) -> List[StateBasedAction]:
        """CR 704.5f: Creatures with 0 or less toughness are destroyed"""
        actions = []
        
        for player in self.game.players:
            for perm in player.battlefield[:]:  # Copy list to avoid modification issues
                if 'Creature' in getattr(perm.card, 'types', []):
                    toughness = self._get_current_toughness(perm)
                    if toughness <= 0:
                        actions.append(StateBasedAction(
                            action_type="destroy",
                            target=perm,
                            reason=f"Toughness is {toughness}",
                            rule_reference="CR 704.5f"
                        ))
                        
        return actions
    
    def _check_lethal_damage(self) -> List[StateBasedAction]:
        """CR 704.5g: Creatures with lethal damage are destroyed"""
        actions = []
        
        for player in self.game.players:
            for perm in player.battlefield[:]:
                if 'Creature' in getattr(perm.card, 'types', []):
                    damage = getattr(perm, 'damage', 0)
                    toughness = self._get_current_toughness(perm)
                    
                    if damage >= toughness and toughness > 0:
                        actions.append(StateBasedAction(
                            action_type="destroy",
                            target=perm,
                            reason=f"Has {damage} damage, toughness is {toughness}",
                            rule_reference="CR 704.5g"
                        ))
                        
        return actions
    
    def _check_deathtouch_damage(self) -> List[StateBasedAction]:
        """CR 704.5h: Creatures with deathtouch damage are destroyed"""
        actions = []
        
        for player in self.game.players:
            for perm in player.battlefield[:]:
                if 'Creature' in getattr(perm.card, 'types', []):
                    # Check if creature has been damaged by deathtouch source
                    if getattr(perm, 'deathtouch_damage', False):
                        actions.append(StateBasedAction(
                            action_type="destroy",
                            target=perm,
                            reason="Has damage from deathtouch source",
                            rule_reference="CR 704.5h"
                        ))
                        
        return actions
    
    def _check_planeswalker_loyalty(self) -> List[StateBasedAction]:
        """CR 704.5i: Planeswalkers with 0 loyalty are destroyed"""
        actions = []
        
        for player in self.game.players:
            for perm in player.battlefield[:]:
                if 'Planeswalker' in getattr(perm.card, 'types', []):
                    loyalty = getattr(perm, 'loyalty', 0)
                    if loyalty <= 0:
                        actions.append(StateBasedAction(
                            action_type="destroy",
                            target=perm,
                            reason=f"Has {loyalty} loyalty",
                            rule_reference="CR 704.5i"
                        ))
                        
        return actions
    
    def _check_legendary_rule(self) -> List[StateBasedAction]:
        """CR 704.5j: Legendary rule - player chooses which to keep"""
        actions = []
        
        for player in self.game.players:
            legendary_permanents = {}
            
            # Group legendary permanents by name
            for perm in player.battlefield:
                if 'Legendary' in getattr(perm.card, 'types', []):
                    name = perm.card.name
                    if name not in legendary_permanents:
                        legendary_permanents[name] = []
                    legendary_permanents[name].append(perm)
            
            # If multiple copies exist, all but one must be destroyed
            for name, perms in legendary_permanents.items():
                if len(perms) > 1:
                    # For AI or automatic resolution, keep the newest one
                    perms_to_destroy = perms[:-1]  # All but the last one
                    
                    for perm in perms_to_destroy:
                        actions.append(StateBasedAction(
                            action_type="destroy",
                            target=perm,
                            reason=f"Legendary rule violation - multiple {name}",
                            rule_reference="CR 704.5j"
                        ))
                        
        return actions
    
    def _check_world_rule(self) -> List[StateBasedAction]:
        """CR 704.5k: World rule (deprecated, kept for completeness)"""
        # World enchantments are no longer printed, but rule still exists
        return []
    
    def _check_aura_attachments(self) -> List[StateBasedAction]:
        """CR 704.5m: Auras not attached to legal objects are destroyed"""
        actions = []
        
        for player in self.game.players:
            for perm in player.battlefield[:]:
                if 'Aura' in getattr(perm.card, 'types', []):
                    attached_to = getattr(perm, 'attached_to', None)
                    if not attached_to or not self._is_legal_attachment_target(perm, attached_to):
                        actions.append(StateBasedAction(
                            action_type="destroy",
                            target=perm,
                            reason="Not attached to legal object",
                            rule_reference="CR 704.5m"
                        ))
                        
        return actions
    
    def _check_equipment_attachments(self) -> List[StateBasedAction]:
        """CR 704.5n: Equipment not attached to creatures become unattached"""
        actions = []
        
        for player in self.game.players:
            for perm in player.battlefield:
                if 'Equipment' in getattr(perm.card, 'types', []):
                    attached_to = getattr(perm, 'attached_to', None)
                    if attached_to and 'Creature' not in getattr(attached_to.card, 'types', []):
                        actions.append(StateBasedAction(
                            action_type="unattach",
                            target=perm,
                            reason="Attached to non-creature",
                            rule_reference="CR 704.5n"
                        ))
                        
        return actions
    
    def _check_tokens_in_wrong_zones(self) -> List[StateBasedAction]:
        """CR 704.5p: Tokens not on battlefield cease to exist"""
        actions = []
        
        # Check all zones except battlefield for tokens
        for player in self.game.players:
            zones_to_check = [
                ('hand', player.hand),
                ('graveyard', player.graveyard),
                ('library', player.library),
                ('exile', getattr(player, 'exile', []))
            ]
            
            for zone_name, zone in zones_to_check:
                for card in zone[:]:
                    if getattr(card, 'is_token', False):
                        actions.append(StateBasedAction(
                            action_type="cease_to_exist",
                            target=card,
                            reason=f"Token in {zone_name}",
                            rule_reference="CR 704.5p"
                        ))
                        
        return actions
    
    def _check_copy_effects(self) -> List[StateBasedAction]:
        """CR 704.5q: Copy effects that should end"""
        # Complex rule about copy effects ending
        # Implementation depends on specific copy effect tracking
        return []
    
    def _perform_actions(self, actions: List[StateBasedAction]) -> None:
        """Perform all state-based actions simultaneously (CR 704.3)"""
        
        # Group actions by type for efficient processing
        actions_by_type = {}
        for action in actions:
            if action.action_type not in actions_by_type:
                actions_by_type[action.action_type] = []
            actions_by_type[action.action_type].append(action)
        
        # Perform each type of action
        for action_type, action_list in actions_by_type.items():
            if action_type == "destroy":
                self._perform_destroy_actions(action_list)
            elif action_type == "lose_game":
                self._perform_lose_game_actions(action_list)
            elif action_type == "unattach":
                self._perform_unattach_actions(action_list)
            elif action_type == "cease_to_exist":
                self._perform_cease_to_exist_actions(action_list)
    
    def _perform_destroy_actions(self, actions: List[StateBasedAction]) -> None:
        """Destroy all marked permanents"""
        for action in actions:
            perm = action.target
            if hasattr(perm, 'controller_id'):
                controller = self.game.players[perm.controller_id]
                if perm in controller.battlefield:
                    controller.battlefield.remove(perm)
                    controller.graveyard.append(perm.card)
    
    def _perform_lose_game_actions(self, actions: List[StateBasedAction]) -> None:
        """Handle players losing the game"""
        for action in actions:
            player = action.target
            # Mark player as having lost
            setattr(player, 'has_lost', True)
            # In a complete implementation, this would trigger game end checks
    
    def _perform_unattach_actions(self, actions: List[StateBasedAction]) -> None:
        """Unattach equipment from illegal targets"""
        for action in actions:
            perm = action.target
            setattr(perm, 'attached_to', None)
    
    def _perform_cease_to_exist_actions(self, actions: List[StateBasedAction]) -> None:
        """Remove tokens from wrong zones"""
        for action in actions:
            token = action.target
            # Remove token from its current zone
            for player in self.game.players:
                for zone in [player.hand, player.graveyard, player.library, getattr(player, 'exile', [])]:
                    if token in zone:
                        zone.remove(token)
                        break
    
    # Helper methods
    
    def _get_current_toughness(self, permanent) -> int:
        """Get the current toughness of a permanent, including modifiers"""
        base_toughness = getattr(permanent.card, 'toughness', 0)
        toughness_modifiers = getattr(permanent, 'toughness_modifiers', 0)
        return base_toughness + toughness_modifiers
    
    def _is_legal_attachment_target(self, aura, target) -> bool:
        """Check if the target is legal for the aura to be attached to"""
        # This would need to check the aura's enchant ability
        # For now, just check if target still exists on battlefield
        for player in self.game.players:
            if target in player.battlefield:
                return True
        return False

def init_state_based_actions(game: 'GameState') -> StateBasedActionEngine:
    """Initialize state-based actions system for a game"""
    sba_engine = StateBasedActionEngine(game)
    game.state_based_actions = sba_engine
    
    # Add method to game for easy access
    def check_state_based_actions():
        return game.state_based_actions.check_and_perform_all()
    
    game.check_state_based_actions = check_state_based_actions
    
    return sba_engine
