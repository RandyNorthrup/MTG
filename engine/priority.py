from __future__ import annotations
from typing import TYPE_CHECKING, Set, Optional
from enum import Enum
if TYPE_CHECKING:
    from .game_state import GameState

class PriorityState(Enum):
    """Priority system states per CR 116"""
    WAITING_FOR_PRIORITY = "waiting"
    HOLDING_PRIORITY = "holding" 
    PASSED = "passed"
    STEP_ENDING = "ending"

class PriorityManager:
    """Manages priority system per MTG Comprehensive Rules 116"""
    
    def __init__(self, game: 'GameState'):
        self.game = game
        self.priority_player: int = 0  # Player who currently has priority
        self.players_passed: Set[int] = set()  # Players who passed priority this round
        self.state = PriorityState.WAITING_FOR_PRIORITY
        self.priority_rounds = 0  # Track consecutive passes for rule enforcement
        
    def give_priority(self, player_id: int, clear_passes: bool = True) -> None:
        """Give priority to specified player (CR 116.3a)"""
        self.priority_player = player_id
        self.state = PriorityState.HOLDING_PRIORITY
        if clear_passes:
            self.players_passed.clear()
            self.priority_rounds = 0
    
    def can_take_action(self, player_id: int) -> bool:
        """Check if player can take actions (cast spells, activate abilities)"""
        return (self.priority_player == player_id and 
                self.state == PriorityState.HOLDING_PRIORITY)
    
    def pass_priority(self, player_id: int) -> bool:
        """Player passes priority (CR 116.4)
        
        Returns True if priority was successfully passed,
        False if player doesn't have priority or action is invalid
        """
        if not self.can_take_action(player_id):
            return False
            
        self.players_passed.add(player_id)
        
        # Check if all players have passed priority with empty stack
        if self._all_players_passed() and self._stack_empty():
            self.state = PriorityState.STEP_ENDING
            return True
            
        # Pass to next player in APNAP order (CR 116.4)
        next_player = self._next_player_apnap(player_id)
        
        # If we've cycled back to a player who already passed, end step/phase
        if next_player in self.players_passed:
            if self._stack_empty():
                self.state = PriorityState.STEP_ENDING
            else:
                # Stack not empty, reset passes and continue
                self.players_passed.clear()
                self.priority_rounds += 1
                
        self.priority_player = next_player
        return True
        
    def hold_priority(self, player_id: int) -> bool:
        """Player explicitly holds priority after casting spell/activating ability
        
        This allows the player to cast additional spells/abilities before 
        passing priority (CR 116.7)
        """
        if not self.can_take_action(player_id):
            return False
            
        # Player retains priority but hasn't "passed"
        # Remove from passed set if they were there
        self.players_passed.discard(player_id)
        return True
    
    def reset_for_new_step(self) -> None:
        """Reset priority state for new step/phase (CR 116.3a)"""
        self.players_passed.clear()
        self.priority_rounds = 0
        self.state = PriorityState.WAITING_FOR_PRIORITY
        # Active player gets priority unless in untap or cleanup step
        self.priority_player = self.game.active_player
        
    def can_advance_step(self) -> bool:
        """Check if current step/phase can advance (CR 116.4)"""
        return (self.state == PriorityState.STEP_ENDING or
                (self._all_players_passed() and self._stack_empty()))
    
    def resolve_stack_item(self) -> bool:
        """Handle priority after stack item resolution (CR 608.2h)
        
        Returns True if priority should be given to active player,
        False if step/phase should end
        """
        if not hasattr(self.game, 'stack') or not self.game.stack:
            return False
            
        # After resolution, active player receives priority
        self.give_priority(self.game.active_player, clear_passes=True)
        
        # Check if stack is now empty and all players had passed
        if self._stack_empty() and self._all_players_passed():
            self.state = PriorityState.STEP_ENDING
            return False
            
        return True
    
    def get_status(self) -> dict:
        """Get current priority status for UI/debugging"""
        return {
            'priority_player': self.priority_player,
            'state': self.state.value,
            'players_passed': list(self.players_passed),
            'can_advance': self.can_advance_step(),
            'priority_rounds': self.priority_rounds
        }
    
    # Private helper methods
    
    def _next_player_apnap(self, current_player: int) -> int:
        """Get next player in APNAP (Active Player, Non-Active Player) order"""
        if not self.game.players:
            return 0
            
        # For 2-player games: simple alternation
        if len(self.game.players) == 2:
            return 1 - current_player
            
        # For multiplayer: clockwise from active player
        active = self.game.active_player
        player_count = len(self.game.players)
        
        # Find current player's position relative to active player
        if current_player == active:
            # Active player passes to next non-active player
            return (active + 1) % player_count
        else:
            # Non-active players pass in turn order
            return (current_player + 1) % player_count
    
    def _all_players_passed(self) -> bool:
        """Check if all players have passed priority this round"""
        return len(self.players_passed) >= len(self.game.players)
    
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
        
    def auto_pass_if_ai(self):
        """AI auto-pass logic - kept for backwards compatibility"""
        if self.priority_player in getattr(self.game, 'ai_players', {}):
            return self.pass_priority(self.priority_player)
        return False
