#!/usr/bin/env python3
"""
Debug zone dropping issue by testing with proper API setup.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMimeData

# Import the API and game components
from ui.game_app_api import GameAppAPI
from engine.game_state import GameState, PlayerState
from engine.card_engine import Card
from engine.mana import ManaPool

# Create a minimal test drop event
class MockDropEvent:
    def __init__(self, card_id):
        self._mime_data = QMimeData()
        self._mime_data.setData("application/mtg-card", str(card_id).encode())
        self._accepted = False
        
    def mimeData(self):
        return self._mime_data
        
    def acceptProposedAction(self):
        self._accepted = True
        print("   ✅ Event accepted")
        
    def ignore(self):
        self._accepted = False
        print("   ❌ Event ignored")
        
    def isAccepted(self):
        return self._accepted

def create_test_game():
    """Create a minimal game with cards in hand."""
    # Create test cards
    forest = Card(id="forest_test", name="Forest", types=["Land"], mana_cost=0)
    forest.text = "{T}: Add {G}."
    
    dragon = Card(id="dragon_test", name="Shivan Dragon", types=["Creature", "Dragon"], mana_cost=6)
    dragon.mana_cost_str = "{4}{R}{R}"
    dragon.power = 5
    dragon.toughness = 5
    dragon.text = "Flying"
    
    # Create players
    player1 = PlayerState(0, "Player 1")
    player1.life = 20
    player1.hand = [forest, dragon]
    player1.mana_pool = ManaPool()
    player1.mana_pool.add('R', 6)  # Give enough mana
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

def create_real_api(game):
    """Create a real API instance with the test game."""
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

def test_api_methods_directly():
    """Test API methods directly to verify they work."""
    print("🔧 Testing API methods directly...")
    
    game = create_test_game()
    api = create_real_api(game)
    
    # Test that the API has the expected methods
    print(f"📋 API has handle_card_drop_to_battlefield: {hasattr(api, 'handle_card_drop_to_battlefield')}")
    print(f"📋 API has handle_card_drop_to_hand: {hasattr(api, 'handle_card_drop_to_hand')}")
    
    # Test calling the methods directly
    try:
        print("🧪 Testing battlefield drop...")
        result = api.handle_card_drop_to_battlefield("forest_test", "battlefield")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
        traceback.print_exc()
    
    try:
        print("🧪 Testing hand drop...")
        result = api.handle_card_drop_to_hand("forest_test")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
        traceback.print_exc()

def test_zone_widgets_with_real_api():
    """Test zone widgets with real API."""
    print("\n🧪 Testing zone widgets with real API...")
    
    try:
        # Import zone classes
        from ui.enhanced_battlefield import ZoneWidget, BattlefieldZone, HandZone
        
        # Create real API
        game = create_test_game()
        api = create_real_api(game)
        print("✅ Created real API instance")
        
        # Create zones WITH the real API
        print("\n📋 Creating zones with real API...")
        
        try:
            # Test battlefield zone
            battlefield = BattlefieldZone("Test Player", api=api)
            print("✅ Created battlefield zone with real API")
            
            # Test the drop
            drop_event = MockDropEvent("forest_test")
            print("🧪 Testing drop on battlefield zone...")
            battlefield.dropEvent(drop_event)
            
            if drop_event.isAccepted():
                print("✅ Battlefield zone accepted the drop!")
            else:
                print("⚠️  Battlefield zone rejected the drop")
                
        except Exception as e:
            print(f"❌ Battlefield zone error: {e}")
            traceback.print_exc()
        
        try:
            # Test hand zone
            hand = HandZone("Test Player", api=api)
            print("✅ Created hand zone with real API")
            
            # Test the drop
            drop_event = MockDropEvent("dragon_test")
            print("🧪 Testing drop on hand zone...")
            hand.dropEvent(drop_event)
            
            if drop_event.isAccepted():
                print("✅ Hand zone accepted the drop!")
            else:
                print("⚠️  Hand zone rejected the drop (expected)")
                
        except Exception as e:
            print(f"❌ Hand zone error: {e}")
            traceback.print_exc()
            
        return True
        
    except Exception as e:
        print(f"❌ Zone widget test failed: {e}")
        traceback.print_exc()
        return False

def debug_zone_api_connection():
    """Debug the zone-API connection."""
    print("\n🔍 Debugging zone-API connection...")
    
    try:
        from ui.enhanced_battlefield import ZoneWidget
        
        # Create real API
        game = create_test_game()
        api = create_real_api(game)
        
        # Create zone
        zone = ZoneWidget("test", "Test Zone", api=api)
        
        print(f"📋 Zone has api attribute: {hasattr(zone, 'api')}")
        print(f"📋 Zone.api is not None: {zone.api is not None}")
        if zone.api:
            print(f"📋 Zone.api has handle_card_drop_to_battlefield: {hasattr(zone.api, 'handle_card_drop_to_battlefield')}")
            print(f"📋 Zone.api has handle_card_drop_to_hand: {hasattr(zone.api, 'handle_card_drop_to_hand')}")
        
        # Test calling the drop handler directly
        drop_event = MockDropEvent("forest_test")
        try:
            result = zone._handle_card_drop(drop_event)
            print(f"📋 Zone._handle_card_drop result: {result}")
        except Exception as e:
            print(f"❌ Zone._handle_card_drop error: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Create Qt application
    app = QApplication(sys.argv)
    
    try:
        print("🧪 Zone Drop API Debug")
        print("="*40)
        
        # Test 1: API methods directly
        test_api_methods_directly()
        
        # Test 2: Zone widgets with real API
        test_zone_widgets_with_real_api()
        
        # Test 3: Debug the connection
        debug_zone_api_connection()
        
        print("\n🎉 Debug tests completed!")
        
    except Exception as e:
        print(f"❌ Critical debug error: {e}")
        traceback.print_exc()
    
    # Exit without starting event loop
    sys.exit(0)
