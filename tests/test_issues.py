"""Test script to identify and fix issues in the modernized codebase."""

import sys
import traceback
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_engine_imports():
    """Test engine imports."""
    print("=== Testing Engine Imports ===")
    try:
        from engine import GameState, PlayerState, GameController, Card, Permanent, ManaPool, CombatManager, Stack, RulesEngine
        print("✅ All engine imports successful")
        return True
    except Exception as e:
        print(f"❌ Engine import error: {e}")
        traceback.print_exc()
        return False

def test_ui_imports():
    """Test UI imports."""
    print("\n=== Testing UI Imports ===")
    try:
        from ui.theme import MTGTheme
        print("✅ Theme import successful")
        
        from ui.card_widget import InteractiveCardWidget, CardContainer, create_card_widget
        print("✅ Card widget imports successful")
        
        from ui.enhanced_game_board import EnhancedGameBoard
        print("✅ Game board import successful")
        
        from ui.enhanced_lobby import EnhancedLobby
        print("✅ Lobby import successful")
        
        return True
    except Exception as e:
        print(f"❌ UI import error: {e}")
        traceback.print_exc()
        return False

def test_game_creation():
    """Test basic game creation."""
    print("\n=== Testing Game Creation ===")
    try:
        from engine.game_state import GameState, PlayerState
        from engine.card_engine import Card
        
        # Create players
        players = [
            PlayerState(player_id=0, name="Player 1"),
            PlayerState(player_id=1, name="Player 2")
        ]
        
        # Create game
        game = GameState(players=players)
        print(f"✅ Game created with {len(game.players)} players")
        
        # Test basic operations
        game.players[0].add_mana(5)
        print(f"✅ Mana operations work: Player has {game.players[0].mana} mana")
        
        return True
    except Exception as e:
        print(f"❌ Game creation error: {e}")
        traceback.print_exc()
        return False

def test_card_widget_creation():
    """Test card widget creation with QApplication."""
    print("\n=== Testing Card Widget Creation ===")
    try:
        from PySide6.QtWidgets import QApplication
        from ui.card_widget import create_card_widget
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create mock card
        class MockCard:
            def __init__(self):
                self.name = "Test Card"
                self.types = ["Creature"]
                self.id = "test_id"
                self.power = "2"
                self.toughness = "2"
                self.text = "A test creature."
        
        mock_card = MockCard()
        widget = create_card_widget(mock_card)
        print("✅ Card widget creation successful")
        
        # Clean up
        widget.deleteLater()
        
        return True
    except Exception as e:
        print(f"❌ Card widget creation error: {e}")
        traceback.print_exc()
        return False

def test_game_board_creation():
    """Test game board creation."""
    print("\n=== Testing Game Board Creation ===")
    try:
        from PySide6.QtWidgets import QApplication
        from ui.enhanced_game_board import EnhancedGameBoard
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create mock API
        class MockAPI:
            def __init__(self):
                self.game = None
        
        mock_api = MockAPI()
        board = EnhancedGameBoard(mock_api)
        print("✅ Game board creation successful")
        
        # Clean up
        board.deleteLater()
        
        return True
    except Exception as e:
        print(f"❌ Game board creation error: {e}")
        traceback.print_exc()
        return False

def test_main_imports():
    """Test imports from main.py."""
    print("\n=== Testing Main Application Imports ===")
    try:
        from engine.game_init import create_initial_game, new_game, parse_args
        print("✅ Game init imports successful")
        
        from ui.game_app_api import GameAppAPI
        print("✅ Game API import successful")
        
        from ui.enhanced_lobby import build_enhanced_play_stack
        print("✅ Enhanced lobby build function import successful")
        
        return True
    except Exception as e:
        print(f"❌ Main imports error: {e}")
        traceback.print_exc()
        return False

def test_with_minimal_qt():
    """Test with minimal Qt setup."""
    print("\n=== Testing Minimal Qt Setup ===")
    try:
        from PySide6.QtWidgets import QApplication, QWidget, QLabel
        from PySide6.QtCore import Qt
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create a simple widget
        widget = QWidget()
        widget.setWindowTitle("Test Widget")
        widget.resize(300, 200)
        
        label = QLabel("Test successful!", widget)
        label.setAlignment(Qt.AlignCenter)
        
        print("✅ Minimal Qt setup successful")
        
        # Show briefly and close
        widget.show()
        widget.close()
        widget.deleteLater()
        
        return True
    except Exception as e:
        print(f"❌ Minimal Qt setup error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Modernized MTG Commander Codebase for Issues\n")
    
    tests = [
        ("Engine Imports", test_engine_imports),
        ("UI Imports", test_ui_imports),
        ("Game Creation", test_game_creation),
        ("Main Imports", test_main_imports),
        ("Minimal Qt Setup", test_with_minimal_qt),
        ("Card Widget Creation", test_card_widget_creation),
        ("Game Board Creation", test_game_board_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- Running {test_name} ---")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            traceback.print_exc()
    
    print(f"\n📊 Final Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready for full application test.")
    else:
        print("❌ Some tests failed. Issues need to be fixed.")
    
    # Clean up Qt
    try:
        app = QApplication.instance()
        if app:
            app.quit()
    except:
        pass
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
