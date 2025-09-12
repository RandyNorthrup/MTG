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
        
        try:
            # Test base zone widget
            base_zone = ZoneWidget("test", "Test Zone", api=None)
            zones.append(("base", base_zone))
            print("✅ Created base zone widget")
        except Exception as e:
            print(f"❌ Failed to create base zone: {e}")
        
        try:
            # Test battlefield zone
            battlefield = BattlefieldZone("Test Player", api=None)
            zones.append(("battlefield", battlefield))
            print("✅ Created battlefield zone")
        except Exception as e:
            print(f"❌ Failed to create battlefield zone: {e}")
        
        try:
            # Test hand zone
            hand = HandZone("Test Player", api=None)
            zones.append(("hand", hand))
            print("✅ Created hand zone")
        except Exception as e:
            print(f"❌ Failed to create hand zone: {e}")
        
        try:
            # Test graveyard zone
            graveyard = GraveyardZone("Test Player", api=None)
            zones.append(("graveyard", graveyard))
            print("✅ Created graveyard zone")
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
