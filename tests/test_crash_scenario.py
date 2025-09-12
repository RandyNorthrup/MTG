#!/usr/bin/env python3
"""Test that simulates the exact crash scenario."""

import sys
import os
from PySide6.QtWidgets import QApplication

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_crash_scenario():
    """Test the scenario that causes crashes."""
    print("🚀 Testing Crash Scenario...")
    print("="*50)
    
    try:
        # Import the main application components
        from main import setup_and_run_app
        
        print("✅ Imports successful")
        
        # Create a minimal test to see if the app can start
        print("📋 Starting application...")
        
        # This should launch the app and we can test drag-drop manually
        app = QApplication(sys.argv)
        
        # Import the main window setup
        from ui.main_window import MainWindow
        from ui.theme import apply_theme
        
        apply_theme(app)
        main_window = MainWindow()
        main_window.show()
        
        print("✅ Application started successfully")
        print("📋 Instructions:")
        print("   1. Go to the lobby and start a game")
        print("   2. Try dragging cards from hand to battlefield")
        print("   3. Watch console for debug output")
        print("   4. If crash occurs, check console for exact location")
        
        # Run for testing - user can close when done
        return app.exec()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(test_crash_scenario())
