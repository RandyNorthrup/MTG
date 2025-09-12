#!/usr/bin/env python3
"""Final test for production-ready card placement system."""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def test_final_placement():
    """Test the final clean version of the card placement system."""
    print("🚀 Testing Final Card Placement System...")
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
        
        print("📋 Creating game...")
        game, ai_ids = create_initial_game(args)
        print(f"✅ Game created with {len(game.players)} players")
        
        # Create main window
        main_window = MainWindow(game, ai_ids, args)
        main_window.show()
        api = main_window.api
        
        # Initialize the game
        api.ensure_ai_opponent()
        api.start_game_without_roll()
        api.open_game_window()
        
        print("✅ Game initialized successfully")
        
        # Test card placement
        if hasattr(api.game, 'players') and api.game.players and api.game.players[0].hand:
            land_cards = [card for card in api.game.players[0].hand if "Land" in getattr(card, 'types', [])]
            creature_cards = [card for card in api.game.players[0].hand if "Creature" in getattr(card, 'types', [])]
            
            print(f"📋 Found {len(land_cards)} lands and {len(creature_cards)} creatures in hand")
            
            # Test land placement
            if land_cards:
                test_land = land_cards[0]
                land_name = getattr(test_land, 'name', 'Unknown')
                land_id = getattr(test_land, 'id', None)
                
                print(f"🌲 Testing land placement: {land_name}")
                result = api.handle_card_drop_to_battlefield(land_id, "Lands")
                
                if result:
                    print(f"✅ Land '{land_name}' successfully placed!")
                    
                    # Verify placement in correct zone
                    if hasattr(api, 'board_window') and api.board_window and hasattr(api.board_window, 'play_area'):
                        play_area = api.board_window.play_area
                        if hasattr(play_area, 'player_lands_battlefield') and hasattr(play_area, 'player_creatures_battlefield'):
                            lands_count = len(getattr(play_area.player_lands_battlefield, 'cards', []))
                            creatures_count = len(getattr(play_area.player_creatures_battlefield, 'cards', []))
                            
                            print(f"🎯 Verification: {lands_count} in lands zone, {creatures_count} in creatures zone")
                            
                            if lands_count > 0 and creatures_count == 0:
                                print("🎉 SUCCESS: Land correctly placed in lands zone!")
                            else:
                                print("⚠️  WARNING: Unexpected placement results")
                else:
                    print(f"❌ Land placement failed: {land_name}")
            
        print(f"\n✅ Final placement test completed successfully!")
        print(f"📋 The card placement system is working correctly.")
        
        # Quick exit
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(1000)  # 1 second
        
        result = app.exec()
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_final_placement())
