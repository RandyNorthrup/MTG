"""Integration layer for enhanced card interactions with existing game system.

This module bridges the new enhanced card widgets and battlefield layout
with the existing game API and controller system.
"""

from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter
from PySide6.QtCore import QTimer, Signal, Qt

from ui.enhanced_battlefield import EnhancedBattlefieldLayout
from ui.enhanced_card_widget import EnhancedCardWidget


class EnhancedGameIntegration(QWidget):
    """Integration layer for enhanced game interactions."""
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.game = api.game
        self.controller = api.controller
        
        # Track battlefield layouts for each player
        self.player_battlefields = {}
        
        self.setup_ui()
        self.connect_to_game_events()
        
        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_from_game_state)
        self.refresh_timer.start(1000)  # Refresh every second
        
    def setup_ui(self):
        """Setup the enhanced game UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        
        # Create battlefield layouts for each player
        for i, player in enumerate(self.game.players):
            battlefield = EnhancedBattlefieldLayout(
                player_name=player.name,
                parent=self,
                api=self.api
            )
            
            # Connect battlefield signals
            battlefield.card_played.connect(self.handle_card_played)
            battlefield.card_activated.connect(self.handle_card_activated)
            battlefield.mana_tapped.connect(self.handle_mana_tapped)
            
            self.player_battlefields[i] = battlefield
            
            if i == 0:  # Current player at bottom
                layout.addWidget(battlefield, 1)
            else:  # Other players at top (for now just one opponent)
                layout.insertWidget(0, battlefield, 1)
                
    def connect_to_game_events(self):
        """Connect to game events for automatic updates."""
        # This would connect to game state change events
        # For now, we'll use the refresh timer
        pass
        
    def refresh_from_game_state(self):
        """Refresh the UI from current game state."""
        try:
            for player_id, battlefield in self.player_battlefields.items():
                if player_id < len(self.game.players):
                    player = self.game.players[player_id]
                    self.update_player_battlefield(player_id, player, battlefield)
        except Exception as e:
            print(f"Error refreshing game state: {e}")
            
    def update_player_battlefield(self, player_id, player, battlefield):
        """Update a player's battlefield from game state."""
        # Update hand
        current_hand_cards = set(battlefield.hand.cards)
        game_hand_cards = set(getattr(player, 'hand', []))
        
        # Add new cards to hand
        for card in game_hand_cards - current_hand_cards:
            battlefield.add_card_to_hand(card, animated=True)
            
        # Remove cards no longer in hand
        for card in current_hand_cards - game_hand_cards:
            battlefield.hand.remove_card(card, animated=True)
            
        # Update battlefield permanents
        current_battlefield_cards = set(battlefield.battlefield.cards)
        game_battlefield_cards = set()
        
        # Extract cards from permanents
        for perm in getattr(player, 'battlefield', []):
            if hasattr(perm, 'card'):
                game_battlefield_cards.add(perm.card)
                
        # Add new permanents
        for card in game_battlefield_cards - current_battlefield_cards:
            battlefield.add_card_to_battlefield(card, animated=True)
            
        # Remove permanents no longer on battlefield
        for card in current_battlefield_cards - game_battlefield_cards:
            battlefield.battlefield.remove_card(card, animated=True)
            
        # Update card states (tapped, summoning sick, etc.)
        self.update_card_states(player, battlefield)
        
    def update_card_states(self, player, battlefield):
        """Update visual states of cards based on game state."""
        for perm in getattr(player, 'battlefield', []):
            if hasattr(perm, 'card'):
                card_widget = battlefield.battlefield.get_card_widget(perm.card)
                if card_widget:
                    # Update tapped state
                    is_tapped = getattr(perm, 'tapped', False)
                    if is_tapped != card_widget.is_tapped:
                        if is_tapped:
                            card_widget.tap_card(animated=False)
                        else:
                            card_widget.untap_card(animated=False)
                            
                    # Update summoning sickness
                    is_sick = getattr(perm, 'summoning_sick', False)
                    card_widget.set_summoning_sick(is_sick)
                    
    def handle_card_played(self, card):
        """Handle a card being played."""
        try:
            if self.api and hasattr(self.api, 'play_card_from_hand'):
                success = self.api.play_card_from_hand(card)
                if not success:
                    print(f"Failed to play {getattr(card, 'name', 'card')}")
        except Exception as e:
            print(f"Error playing card: {e}")
            
    def handle_card_activated(self, card, action):
        """Handle card activation (clicks, abilities, etc.)."""
        try:
            if action == "double_clicked":
                self.handle_card_double_clicked(card)
            elif action == "tapped":
                self.handle_card_tapped(card)
            elif action.startswith("ability_"):
                ability_name = action[8:]  # Remove "ability_" prefix
                self.handle_ability_activation(card, ability_name)
        except Exception as e:
            print(f"Error handling card activation: {e}")
            
    def handle_card_double_clicked(self, card):
        """Handle card double-click (usually play/activate)."""
        # Try to play the card or activate its main ability
        if "Land" in getattr(card, 'types', []):
            self.try_play_land(card)
        elif any(t in getattr(card, 'types', []) for t in ['Instant', 'Sorcery']):
            self.try_cast_spell(card)
        elif "Creature" in getattr(card, 'types', []):
            # Could be summoning or attacking
            self.try_creature_action(card)
            
    def handle_card_tapped(self, card):
        """Handle card being tapped."""
        # This is triggered by the visual tap, now sync with game state
        try:
            player = self.api.get_current_player()
            if hasattr(player, 'battlefield'):
                for perm in player.battlefield:
                    if hasattr(perm, 'card') and perm.card == card:
                        # Update game state to reflect tap
                        perm.tapped = True
                        if hasattr(perm.card, 'tap'):
                            perm.card.tap()
                        break
        except Exception as e:
            print(f"Error syncing tap state: {e}")
            
    def handle_mana_tapped(self, card):
        """Handle tapping a card for mana."""
        try:
            if self.api and hasattr(self.api, 'tap_permanent_for_mana'):
                player = self.api.get_current_player()
                success = self.api.tap_permanent_for_mana(player, card)
                if not success:
                    print(f"Failed to tap {getattr(card, 'name', 'card')} for mana")
        except Exception as e:
            print(f"Error tapping for mana: {e}")
            
    def handle_ability_activation(self, card, ability_name):
        """Handle ability activation."""
        try:
            if ability_name == "tap_ability":
                self.activate_tap_ability(card)
            # Add other ability types as needed
        except Exception as e:
            print(f"Error activating ability: {e}")
            
    def try_play_land(self, card):
        """Try to play a land card."""
        try:
            if self.api and hasattr(self.api, 'play_land'):
                player = self.api.get_current_player()
                success, message = self.api.play_land(player, card)
                if not success:
                    print(f"Cannot play land: {message}")
        except Exception as e:
            print(f"Error playing land: {e}")
            
    def try_cast_spell(self, card):
        """Try to cast a spell."""
        try:
            if self.api and hasattr(self.api, 'cast_spell'):
                success, message = self.api.cast_spell(card)
                if not success:
                    print(f"Cannot cast spell: {message}")
        except Exception as e:
            print(f"Error casting spell: {e}")
            
    def try_creature_action(self, card):
        """Try to perform a creature action (summon or attack)."""
        # Check if creature is in hand (summon) or on battlefield (attack)
        player = self.api.get_current_player()
        
        if card in getattr(player, 'hand', []):
            # Try to summon the creature
            self.try_cast_spell(card)
        else:
            # Try to attack with the creature
            self.try_attack_with_creature(card)
            
    def try_attack_with_creature(self, card):
        """Try to attack with a creature."""
        try:
            if self.api and hasattr(self.api, 'declare_attacker'):
                success = self.api.declare_attacker(card)
                if success:
                    # Update visual state
                    for battlefield in self.player_battlefields.values():
                        card_widget = battlefield.battlefield.get_card_widget(card)
                        if card_widget:
                            card_widget.set_attacking(True)
                else:
                    print(f"Cannot attack with {getattr(card, 'name', 'creature')}")
        except Exception as e:
            print(f"Error declaring attacker: {e}")
            
    def activate_tap_ability(self, card):
        """Activate a tap ability."""
        try:
            if self.api and hasattr(self.api, 'activate_tap_ability'):
                success = self.api.activate_tap_ability(card)
                if not success:
                    print(f"Cannot activate tap ability of {getattr(card, 'name', 'card')}")
        except Exception as e:
            print(f"Error activating tap ability: {e}")
            
    def handle_phase_change(self):
        """Handle game phase changes."""
        # Update UI to reflect phase change
        current_phase = getattr(self.controller, 'phase', '')
        
        if current_phase.upper() == 'UNTAP':
            # Untap all permanents
            for battlefield in self.player_battlefields.values():
                battlefield.untap_all()
                
    def force_refresh(self):
        """Force a complete refresh of the UI."""
        self.refresh_from_game_state()


def integrate_enhanced_game_board(api, parent=None):
    """Create and return an enhanced game board integrated with the API."""
    return EnhancedGameIntegration(api, parent)
