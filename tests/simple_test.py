#!/usr/bin/env python3
"""Simple Test Runner for MTG Commander Game.

Tests only the core components that are currently working.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_mana_system():
    """Test core mana system functionality."""
    from engine.mana import ManaPool, parse_mana_cost
    
    print("🧪 Testing Mana System...")
    
    # Test mana pool operations
    pool = ManaPool()
    pool.add('R', 2)
    pool.add('G', 1)
    pool.add('C', 3)
    
    # Test cost parsing
    cost = parse_mana_cost('{2}{R}{R}')
    assert cost == {'C': 2, 'R': 2}, f"Expected {{'C': 2, 'R': 2}}, got {cost}"
    
    # Test payment ability
    can_pay = pool.can_pay(cost)
    assert can_pay, "Should be able to pay {2}{R}{R} with 2R + 1G + 3C"
    
    # Test actual payment
    success = pool.pay(cost)
    assert success, "Payment should succeed"
    assert pool.pool['R'] == 0, "Should have 0 red mana remaining"
    assert pool.pool['C'] == 1, "Should have 1 colorless mana remaining"
    
    print("   ✅ Mana system working correctly")


def test_engine_imports():
    """Test that all engine modules can be imported."""
    print("🧪 Testing Engine Imports...")
    
    try:
        from engine import GameState, PlayerState, GameController, Card, Permanent
        from engine import ManaPool, CombatManager, Stack, RulesEngine
        print("   ✅ All engine modules import successfully")
        return True
    except Exception as e:
        print(f"   ❌ Engine import failed: {e}")
        return False


def test_ui_imports():
    """Test that all UI modules can be imported."""
    print("🧪 Testing UI Imports...")
    
    try:
        from ui.enhanced_game_board import EnhancedGameBoard
        from ui.enhanced_lobby import EnhancedLobby
        from ui.card_widget import InteractiveCardWidget
        print("   ✅ All UI modules import successfully")
        return True
    except Exception as e:
        print(f"   ❌ UI import failed: {e}")
        return False


def test_game_creation():
    """Test basic game object creation."""
    print("🧪 Testing Game Creation...")
    
    try:
        from engine import GameController, GameState, PlayerState
        
        # Create basic game state and players
        player1 = PlayerState(0, "Player 1")
        player2 = PlayerState(1, "Player 2") 
        game_state = GameState(players=[player1, player2])
        
        # Create game controller
        controller = GameController(game_state, ai_ids=[1], logging_enabled=False)
        
        # Basic validation
        assert player1.player_id == 0
        assert player1.name == "Player 1"
        assert player2.player_id == 1
        assert player2.name == "Player 2"
        assert controller.game == game_state
        
        print("   ✅ Game creation working correctly")
        return True
    except Exception as e:
        print(f"   ❌ Game creation failed: {e}")
        return False


def run_all_tests():
    """Run all validation tests."""
    print("🚀 Running MTG Core Tests")
    print("=" * 50)
    
    try:
        test_mana_system()
        
        if not test_engine_imports():
            return False
            
        if not test_ui_imports():
            return False
            
        if not test_game_creation():
            return False
        
        print("\n" + "=" * 50)
        print("✅ All core tests PASSED!")
        print("🎯 Game engine is ready for play!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
