#!/usr/bin/env python3
"""Test to isolate and fix the specific land drop crash."""

import sys
import os
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def test_land_drop_crash():
    """Test land drops to battlefield zones to identify crash cause."""
    print("🚀 Testing Land Drop Crash Scenario...")
    print("="*50)
    
    try:
        # Import the main application components
        from engine.game_init import create_initial_game, parse_args
        from ui.theme import apply_modern_theme
        from main import MainWindow
        
        print("✅ Imports successful")
        
        # Create the application
        app = QApplication(sys.argv)
        
        # Apply theme
        try:
            apply_modern_theme(app)
            print("✅ Theme applied")
        except Exception as e:
            print(f"⚠️  Warning: Theme failed - {e}")
        
        # Create game with minimal setup
        args = parse_args()
        args.no_log = False  # Enable logging
        
        print("📋 Creating initial game...")
        game, ai_ids = create_initial_game(args)
        print(f"✅ Initial game created with {len(game.players)} players")
        
        # Create main window
        print("📋 Creating main window...")
        main_window = MainWindow(game, ai_ids, args)
        main_window.show()
        
        # Get the API
        api = main_window.api
        print("✅ Main window and API created")
        
        # Initialize the game
        print("🔍 Initializing game...")
        api.ensure_ai_opponent()
        api.start_game_without_roll()
        api.open_game_window()
        
        print("✅ Game initialized")
        
        # Test land drops to different zones
        print("\n📋 Testing land drops to different zones...")
        
        if hasattr(api.game, 'players') and api.game.players and api.game.players[0].hand:
            # Find land cards
            land_cards = [card for card in api.game.players[0].hand if "Land" in getattr(card, 'types', [])]
            
            if land_cards:
                print(f"🔍 Found {len(land_cards)} land cards:")
                for i, card in enumerate(land_cards):
                    print(f"   {i+1}. {getattr(card, 'name', 'Unknown')} (ID: {getattr(card, 'id', 'NO_ID')})")
                
                test_land = land_cards[0]
                card_id = getattr(test_land, 'id', None)
                card_name = getattr(test_land, 'name', 'Unknown')
                
                print(f"\n🧪 TEST: Dropping land '{card_name}' to different zones...")
                
                # Test 1: Drop to "Lands" zone (should work)
                print(f"\n🔍 TEST 1: Dropping to 'Lands' zone...")
                try:
                    result = api.handle_card_drop_to_battlefield(card_id, "Lands")
                    print(f"✅ Drop to Lands zone: {result}")
                except Exception as e:
                    print(f"❌ Drop to Lands zone failed: {e}")
                    traceback.print_exc()
                
                # Check if we still have lands to test
                remaining_lands = [card for card in api.game.players[0].hand if "Land" in getattr(card, 'types', [])]
                
                if remaining_lands:
                    test_land2 = remaining_lands[0]
                    card_id2 = getattr(test_land2, 'id', None)
                    card_name2 = getattr(test_land2, 'name', 'Unknown')
                    
                    # Test 2: Drop to "Creatures" zone (should fail gracefully)
                    print(f"\n🔍 TEST 2: Dropping land '{card_name2}' to 'Creatures' zone...")
                    try:
                        result = api.handle_card_drop_to_battlefield(card_id2, "Creatures")
                        print(f"✅ Drop to Creatures zone: {result}")
                    except Exception as e:
                        print(f"❌ Drop to Creatures zone failed: {e}")
                        traceback.print_exc()
                
                # Test 3: Drop to invalid zone
                if len(remaining_lands) > 1:
                    test_land3 = remaining_lands[1]
                    card_id3 = getattr(test_land3, 'id', None)
                    card_name3 = getattr(test_land3, 'name', 'Unknown')
                    
                    print(f"\n🔍 TEST 3: Dropping land '{card_name3}' to invalid zone...")
                    try:
                        result = api.handle_card_drop_to_battlefield(card_id3, "InvalidZone")
                        print(f"✅ Drop to invalid zone: {result}")
                    except Exception as e:
                        print(f"❌ Drop to invalid zone failed: {e}")
                        traceback.print_exc()
            else:
                print("⚠️  No land cards found in hand for testing")
                
            # Test battlefield zones directly
            print(f"\n🔍 Testing battlefield zones directly...")
            try:
                if hasattr(api, 'board_window') and api.board_window:
                    board_window = api.board_window
                    if hasattr(board_window, 'play_area'):
                        play_area = board_window.play_area
                        
                        # Check if battlefield zones exist
                        zones_to_check = ['player_creatures_battlefield', 'player_lands_battlefield']
                        for zone_name in zones_to_check:
                            if hasattr(play_area, zone_name):
                                zone = getattr(play_area, zone_name)
                                print(f"✅ Found zone: {zone_name}")
                                print(f"   Zone name: {getattr(zone, 'zone_name', 'NO_NAME')}")
                                print(f"   Is opponent: {getattr(zone, 'is_opponent', 'UNKNOWN')}")
                                print(f"   Cards count: {len(getattr(zone, 'cards', []))}")
                                print(f"   Has API: {hasattr(zone, 'api') and zone.api is not None}")
                            else:
                                print(f"❌ Zone not found: {zone_name}")
                                
            except Exception as e:
                print(f"❌ Battlefield zone check failed: {e}")
                traceback.print_exc()
        
        print(f"\n📋 Land drop tests completed")
        print(f"📋 App will run for 5 seconds...")
        
        # Let app run
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(5000)  # 5 seconds
        
        # Run the application
        result = app.exec()
        print(f"🔍 Application finished with exit code: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Critical test failure: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_land_drop_crash())
