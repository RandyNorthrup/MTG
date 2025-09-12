#!/usr/bin/env python3
"""
Simplified test for zone drop crash debugging.
This directly tests the drop event handling methods we improved.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMimeData

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

def test_zone_drop_handling():
    """Test our improved zone drop handling directly."""
    print("🧪 Testing Zone Drop Handling...")
    print("="*40)
    
    try:
        # Import our zone classes
        from ui.enhanced_battlefield import ZoneWidget, BattlefieldZone, HandZone, GraveyardZone
        
        # Create zones without full game setup
        print("📋 Creating test zones...")
        zones = []
        
        # Create a real API for testing
        from ui.game_app_api import GameAppAPI
        from engine.game_state import GameState, PlayerState
        from engine.card_engine import Card
        from engine.mana import ManaPool
        
        # Create minimal test game
        forest = Card(id="test_card_123", name="Forest", types=["Land"], mana_cost=0)
        player1 = PlayerState(0, "Player 1")
        player1.hand = [forest]
        player1.mana_pool = ManaPool()
        player1.battlefield = []
        
        game = GameState(players=[player1])
        
        class MockMainWindow:
            def __init__(self): self.logging_enabled = True
        def new_game_factory(specs, ai_enabled=True): return game, []
        class MockArgs:
            def __init__(self): self.no_log = False
                
        api = GameAppAPI(MockMainWindow(), game, [], MockArgs(), new_game_factory)
        print("✅ Created real API for testing")

        try:
            # Test base zone widget with real API
            base_zone = ZoneWidget("test", "Test Zone", api=api)
            zones.append(("base", base_zone))
            print("✅ Created base zone widget with API")
        except Exception as e:
            print(f"❌ Failed to create base zone: {e}")
        
        try:
            # Test battlefield zone with real API
            battlefield = BattlefieldZone("Test Player", api=api)
            zones.append(("battlefield", battlefield))
            print("✅ Created battlefield zone with API")
        except Exception as e:
            print(f"❌ Failed to create battlefield zone: {e}")
        
        try:
            # Test hand zone with real API
            hand = HandZone("Test Player", api=api)
            zones.append(("hand", hand))
            print("✅ Created hand zone with API")
        except Exception as e:
            print(f"❌ Failed to create hand zone: {e}")
        
        try:
            # Test graveyard zone with real API  
            graveyard = GraveyardZone("Test Player", api=api)
            zones.append(("graveyard", graveyard))
            print("✅ Created graveyard zone with API")
        except Exception as e:
            print(f"❌ Failed to create graveyard zone: {e}")
        
        # Test drop events on each zone
        print(f"\n🧪 Testing drop events on {len(zones)} zones...")
        test_card_id = "test_card_123"
        
        for zone_name, zone_widget in zones:
            print(f"\n🔍 Testing {zone_name} zone...")
            
            try:
                # Create mock drop event
                drop_event = MockDropEvent(test_card_id)
                
                # Test the drop
                print(f"   📋 Calling dropEvent on {zone_name}...")
                zone_widget.dropEvent(drop_event)
                
                if drop_event.isAccepted():
                    print(f"   ✅ {zone_name} zone accepted the drop")
                else:
                    print(f"   ⚠️  {zone_name} zone rejected the drop (expected)")
                
            except Exception as e:
                print(f"   ❌ {zone_name} zone crashed: {e}")
                traceback.print_exc()
                print()
        
        print(f"\n📊 Zone drop testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Create Qt application
    app = QApplication(sys.argv)
    
    try:
        success = test_zone_drop_handling()
        if success:
            print("✅ All zone drop tests completed")
        else:
            print("❌ Some tests failed")
            
    except Exception as e:
        print(f"❌ Critical test error: {e}")
        traceback.print_exc()
    
    # Exit without starting event loop
    sys.exit(0)
