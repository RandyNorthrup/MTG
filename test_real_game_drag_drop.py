#!/usr/bin/env python3
"""Test script to reproduce drag-drop crashes in the real game."""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def test_real_game_drag_drop():
    """Test drag-drop functionality in the real game environment."""
    print("🚀 Testing Real Game Drag-Drop...")
    print("="*50)
    
    try:
        # Import the main application components
        from main import main
        from engine.game_init import create_initial_game, parse_args
        from ui.theme import apply_modern_theme
        from main import MainWindow
        from engine.game_init import new_game
        
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
        args = parse_args()  # Get default args
        args.no_log = False  # Enable logging to see debug output
        
        game, ai_ids = create_initial_game(args)
        print(f"✅ Game created with {len(game.players)} players")
        
        # Create main window
        main_window = MainWindow(game, ai_ids, args)
        main_window.show()
        
        print("✅ Main window created and displayed")
        print("📋 Instructions for manual testing:")
        print("   1. Click on the Enhanced Lobby tab")
        print("   2. Create or join a game")
        print("   3. When the game board opens:")
        print("      a. Try dragging cards from hand to battlefield")
        print("      b. Watch the console for debug output")
        print("      c. Look for error messages or crashes")
        print("   4. Test with different card types (lands, creatures, artifacts)")
        print("   5. If crash occurs, the console will show the traceback")
        
        # Set up auto-close after 60 seconds for automated testing
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(60000)  # 60 seconds
        
        print("\n🔍 Starting application - test window will close in 60 seconds...")
        print("   Press Ctrl+C or close the window to end testing early")
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_real_game_drag_drop())
