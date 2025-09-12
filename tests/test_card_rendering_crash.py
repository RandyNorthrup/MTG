#!/usr/bin/env python3
"""Test to trigger potential card rendering crashes during drag-drop operations."""

import sys
import os
import traceback
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QEventLoop, QThread
from PySide6.QtGui import QPixmap, QPainter

def test_card_rendering_crash():
    """Test card rendering under stress conditions."""
    print("🚀 Testing Card Rendering Crash Scenarios...")
    print("="*50)
    
    try:
        # Import the main application components
        from engine.game_init import create_initial_game, parse_args
        from ui.theme import apply_modern_theme
        from main import MainWindow
        from ui.card_widget import InteractiveCardWidget, CardContainer
        from engine.card_engine import Card
        
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
        main_window.show()
        
        # Get the API for direct testing
        api = main_window.api
        print("✅ Main window and API created")
        
        # Initialize the game to get cards in hand
        print("🔍 Initializing game...")
        api.ensure_ai_opponent()
        api.start_game_without_roll()
        api.open_game_window()
        
        print("✅ Game initialized")
        
        # Test stress scenarios
        print("\n📋 Testing stress scenarios that might cause crashes...")
        
        # Test 1: Rapid card widget creation/deletion
        try:
            print("🔍 Test 1: Rapid card widget creation/deletion...")
            
            if hasattr(api.game, 'players') and api.game.players and api.game.players[0].hand:
                test_cards = api.game.players[0].hand[:5]  # Test with first 5 cards
                
                widgets = []
                for i in range(10):  # Create multiple widgets rapidly
                    for card in test_cards:
                        try:
                            widget = InteractiveCardWidget(card, api=api)
                            widgets.append(widget)
                            # Force rendering
                            pixmap = QPixmap(widget.size())
                            widget.render(pixmap)
                        except Exception as e:
                            print(f"   ❌ Widget creation {i} failed: {e}")
                            
                    # Cleanup widgets
                    for widget in widgets:
                        try:
                            widget.deleteLater()
                        except Exception as e:
                            print(f"   ❌ Widget deletion failed: {e}")
                    widgets.clear()
                    
                    # Process events to trigger cleanup
                    app.processEvents()
                    
                print("✅ Test 1 completed")
            else:
                print("⚠️  Test 1 skipped - no cards available")
                
        except Exception as e:
            print(f"❌ Test 1 failed: {e}")
            traceback.print_exc()
        
        # Test 2: Drag operation simulation
        try:
            print("🔍 Test 2: Simulated drag operations...")
            
            if hasattr(api.game, 'players') and api.game.players and api.game.players[0].hand:
                test_cards = api.game.players[0].hand[:3]
                
                for i, card in enumerate(test_cards):
                    try:
                        # Simulate playing a card through API
                        card_id = getattr(card, 'id', None)
                        if card_id:
                            print(f"   🔄 Attempting to play card {i+1}: {getattr(card, 'name', 'Unknown')}")
                            result = api.handle_card_drop_to_battlefield(card_id, "TestZone")
                            print(f"   {'✅' if result else '❌'} Card play result: {result}")
                            
                            # Force UI refresh after each operation
                            api._force_immediate_ui_refresh()
                            app.processEvents()
                            
                    except Exception as e:
                        print(f"   ❌ Card play {i+1} failed: {e}")
                        traceback.print_exc()
                        
            print("✅ Test 2 completed")
            
        except Exception as e:
            print(f"❌ Test 2 failed: {e}")
            traceback.print_exc()
        
        # Test 3: Rapid UI refresh cycles
        try:
            print("🔍 Test 3: Rapid UI refresh cycles...")
            
            for i in range(20):  # 20 rapid refreshes
                try:
                    api._force_immediate_ui_refresh()
                    app.processEvents()
                    time.sleep(0.01)  # Small delay
                except Exception as e:
                    print(f"   ❌ UI refresh {i+1} failed: {e}")
                    
            print("✅ Test 3 completed")
            
        except Exception as e:
            print(f"❌ Test 3 failed: {e}")
            traceback.print_exc()
        
        # Test 4: Memory pressure simulation
        try:
            print("🔍 Test 4: Memory pressure simulation...")
            
            large_objects = []
            try:
                for i in range(100):  # Create many objects
                    # Create large pixmaps to simulate memory pressure
                    pixmap = QPixmap(500, 700)
                    pixmap.fill()
                    large_objects.append(pixmap)
                    
                    if i % 10 == 0:
                        app.processEvents()
                        
                # Force UI refresh under memory pressure
                api._force_immediate_ui_refresh()
                app.processEvents()
                
            finally:
                # Cleanup
                large_objects.clear()
                
            print("✅ Test 4 completed")
            
        except Exception as e:
            print(f"❌ Test 4 failed: {e}")
            traceback.print_exc()
        
        print("\n📋 All stress tests completed")
        print("📋 App will run for 5 more seconds to check for delayed crashes...")
        
        # Let app run for a bit to see if crashes occur
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
    sys.exit(test_card_rendering_crash())
