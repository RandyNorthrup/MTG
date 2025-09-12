#!/usr/bin/env python3
"""End-to-end test for drag-and-drop with real game state."""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QSize

# Import our components
from ui.enhanced_game_board import EnhancedGameBoard
from ui.game_app_api import GameAppAPI
from engine.game_state import GameState, PlayerState
from engine.card_engine import Card
from engine.mana import ManaPool


def create_test_game():
    """Create a test game with cards in hand."""
    
    # Create test cards
    forest = Card(id="forest1", name="Forest", types=["Land"], mana_cost=0)
    forest.text = "{T}: Add {G}."
    
    dragon = Card(id="dragon1", name="Shivan Dragon", types=["Creature", "Dragon"], mana_cost=6)
    dragon.mana_cost_str = "{4}{R}{R}"
    dragon.power = 5
    dragon.toughness = 5
    dragon.text = "Flying"
    
    bolt = Card(id="bolt1", name="Lightning Bolt", types=["Instant"], mana_cost=1)
    bolt.mana_cost_str = "{R}"
    bolt.text = "Lightning Bolt deals 3 damage to any target."
    
    # Create players
    player1 = PlayerState(0, "Player 1")
    player1.life = 20
    player1.hand = [forest, dragon, bolt]
    player1.mana_pool = ManaPool()
    player1.mana_pool.add('R', 6)  # Give player enough mana
    player1.battlefield = []
    player1.graveyard = []
    
    player2 = PlayerState(1, "AI Player")
    player2.life = 20
    player2.hand = []
    player2.battlefield = []
    player2.graveyard = []
    
    # Create game state
    game = GameState(players=[player1, player2])
    game.active_player = 0
    
    return game


def create_test_api(game):
    """Create a test API with the game."""
    
    class MockMainWindow:
        def __init__(self):
            self.logging_enabled = True
    
    def new_game_factory(specs, ai_enabled=True):
        return game, [1]  # AI controls player 1
    
    class MockArgs:
        def __init__(self):
            self.no_log = False
    
    main_window = MockMainWindow()
    args = MockArgs()
    ai_ids = [1]
    
    api = GameAppAPI(main_window, game, ai_ids, args, new_game_factory)
    
    return api


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real Drag & Drop Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create test game and API
        self.game = create_test_game()
        self.api = create_test_api(self.game)
        
        # Create game board
        self.game_board = EnhancedGameBoard(api=self.api)
        self.setCentralWidget(self.game_board)
        
        print("✅ Test window created with:")
        print(f"   - Player has {len(self.game.players[0].hand)} cards in hand")
        print(f"   - Player has {self.game.players[0].mana_pool.pool} mana")
        print("📋 Try dragging cards from hand to battlefield zones!")


def test_real_drag_drop():
    """Test drag-and-drop with a real game setup."""
    print("🚀 Starting Real Game Drag & Drop Test...")
    print("="*50)
    
    try:
        app = QApplication(sys.argv)
        
        window = TestWindow()
        window.show()
        
        print("✅ Test window ready")
        print("📋 Instructions:")
        print("   1. Look for cards in the hand area at the bottom")
        print("   2. Drag them to the battlefield zones")
        print("   3. Watch console for success/error messages")
        
        # Run briefly for testing
        import time
        time.sleep(10)  # Run for 10 seconds for testing
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_real_drag_drop()
    sys.exit(0 if success else 1)
