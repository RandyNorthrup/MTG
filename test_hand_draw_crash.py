#!/usr/bin/env python3
"""Test to isolate and debug the hand drawing crash."""

import sys
import os
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def test_hand_draw_crash():
    """Test the hand drawing phase that's causing crashes."""
    print("🚀 Testing Hand Draw Crash...")
    print("="*50)
    
    try:
        # Import the main application components
        from engine.game_init import create_initial_game, parse_args, new_game
        from ui.theme import apply_modern_theme
        from main import MainWindow
        from ui.game_app_api import GameAppAPI
        
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
        args.no_log = False  # Enable logging to see debug output
        
        print("📋 Creating initial game...")
        game, ai_ids = create_initial_game(args)
        print(f"✅ Initial game created with {len(game.players)} players")
        
        # Create main window
        print("📋 Creating main window...")
        main_window = MainWindow(game, ai_ids, args)
        
        # Get the API for direct testing
        api = main_window.api
        print("✅ Main window and API created")
        
        # Show the window
        main_window.show()
        print("✅ Window displayed")
        
        # Now test the specific operations that might cause crashes
        print("\n📋 Testing game initialization steps...")
        
        try:
            print("🔍 Step 1: Ensuring AI opponent...")
            api.ensure_ai_opponent()
            print("✅ AI opponent ensured")
        except Exception as e:
            print(f"❌ AI opponent failed: {e}")
            traceback.print_exc()
        
        try:
            print("🔍 Step 2: Starting game without roll...")
            api.start_game_without_roll()
            print("✅ Game started")
        except Exception as e:
            print(f"❌ Game start failed: {e}")
            traceback.print_exc()
            
        try:
            print("🔍 Step 3: Checking game state...")
            if hasattr(api.game, 'players') and api.game.players:
                for i, player in enumerate(api.game.players):
                    hand_size = len(getattr(player, 'hand', []))
                    print(f"   Player {i} ({getattr(player, 'name', 'Unknown')}): {hand_size} cards in hand")
            print("✅ Game state checked")
        except Exception as e:
            print(f"❌ Game state check failed: {e}")
            traceback.print_exc()
            
        try:
            print("🔍 Step 4: Opening game board window...")
            api.open_game_window()
            print("✅ Game board window opened")
        except Exception as e:
            print(f"❌ Game board window failed: {e}")
            traceback.print_exc()
            
        try:
            print("🔍 Step 5: Force UI refresh...")
            api._force_immediate_ui_refresh()
            print("✅ UI refresh completed")
        except Exception as e:
            print(f"❌ UI refresh failed: {e}")
            traceback.print_exc()
        
        print("\n📋 Crash test completed - if we got here, the crash might be in UI rendering")
        print("📋 Let the app run for 10 seconds to see if crashes occur during rendering...")
        
        # Set up auto-close after 10 seconds
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(10000)  # 10 seconds
        
        # Run the application
        result = app.exec()
        print(f"🔍 Application finished with exit code: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Critical test failure: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_hand_draw_crash())
