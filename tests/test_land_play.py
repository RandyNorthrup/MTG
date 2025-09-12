#!/usr/bin/env python3
"""Test land playing specifically to identify crash."""

import sys
from PySide6.QtWidgets import QApplication

def test_land_play():
    """Test just the land playing functionality."""
    print("🚀 Testing Land Play Functionality...")
    print("="*50)
    
    try:
        # Create minimal test setup
        from ui.game_app_api import GameAppAPI
        from engine.game_state import GameState, PlayerState
        from engine.card_engine import Card
        from engine.mana import ManaPool
        
        # Create test land
        forest = Card(id="forest1", name="Forest", types=["Land"], mana_cost=0)
        forest.text = "{T}: Add {G}."
        
        # Create player with the land in hand
        player1 = PlayerState(0, "Test Player")
        player1.life = 20
        player1.hand = [forest]
        player1.mana_pool = ManaPool()
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
        
        # Create mock objects for API
        class MockMainWindow:
            def __init__(self):
                self.logging_enabled = True
        
        class MockArgs:
            def __init__(self):
                self.no_log = False
        
        def new_game_factory(specs, ai_enabled=True):
            return game, [1]
        
        # Create API
        main_window = MockMainWindow()
        args = MockArgs()
        ai_ids = [1]
        
        api = GameAppAPI(main_window, game, ai_ids, args, new_game_factory)
        
        print("✅ Test setup created")
        print(f"   - Player has {len(player1.hand)} cards in hand")
        print(f"   - Card in hand: {forest.name}")
        
        # Test the land play operation directly
        print("🧪 Testing land play...")
        
        result = api.handle_card_drop_to_battlefield("forest1", "Lands")
        
        print(f"📋 Land play result: {result}")
        
        if result:
            print("✅ Land play succeeded without crash!")
        else:
            print("❌ Land play failed (but no crash)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    app = QApplication(sys.argv)  # Need Qt app for some operations
    success = test_land_play()
    sys.exit(0 if success else 1)
