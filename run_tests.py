#!/usr/bin/env python3
"""Test Runner for MTG Commander Game.

Simple test validation script to verify core game mechanics
are working correctly before commits.
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


def test_timing_restrictions():
    """Test spell timing and playability."""
    from engine.casting_system import PlayabilityChecker
    from engine.game_state import PlayerState
    from engine.card_engine import Card
    from engine.mana import ManaPool
    
    print("🧪 Testing Timing Restrictions...")
    
    # Setup mock game and player
    class MockGame:
        def __init__(self):
            self.active_player = 0
            self.phase = 'MAIN1'
            self.stack = []
            self.players = []
    
    player = PlayerState(0, 'Test Player')
    player.mana_pool = ManaPool()
    player.mana_pool.add('R', 1)
    player.hand = []
    player.lands_played_this_turn = 0
    
    game = MockGame()
    game.players = [player]
    
    checker = PlayabilityChecker(game)
    
    # Test land timing
    forest = Card('forest1', 'Forest', ['Land'], 0)
    player.hand.append(forest)
    
    can_play, reason = checker.can_play_card(player, forest)
    assert can_play, f"Should be able to play land in main phase, got: {reason}"
    
    # Test sorcery timing in combat (should fail)
    game.phase = 'COMBAT'
    sorcery = Card('bolt', 'Lightning Bolt', ['Sorcery'], 1)
    player.hand.append(sorcery)
    
    can_play, reason = checker.can_play_card(player, sorcery)
    assert not can_play, "Should not be able to play sorcery in combat"
    assert "main phase" in reason.lower(), f"Reason should mention main phase, got: {reason}"
    
    print("   ✅ Timing restrictions working correctly")


def test_land_restrictions():
    """Test land per turn restrictions.""" 
    from engine.casting_system import PlayabilityChecker
    from engine.game_state import PlayerState
    from engine.card_engine import Card
    
    print("🧪 Testing Land Restrictions...")
    
    class MockGame:
        def __init__(self):
            self.active_player = 0
            self.phase = 'MAIN1'
            self.stack = []
            self.players = []
    
    player = PlayerState(0, 'Test Player')
    player.hand = []
    player.lands_played_this_turn = 0
    player.max_lands_per_turn = 1
    
    game = MockGame()
    game.players = [player]
    
    checker = PlayabilityChecker(game)
    
    land1 = Card('island1', 'Island', ['Land'], 0)
    land2 = Card('island2', 'Island', ['Land'], 0)
    player.hand.extend([land1, land2])
    
    # Should be able to play first land
    can_play, reason = checker.can_play_card(player, land1)
    assert can_play, f"Should be able to play first land, got: {reason}"
    
    # Simulate playing first land  
    player.lands_played_this_turn = 1
    
    # Should not be able to play second land
    can_play, reason = checker.can_play_card(player, land2)
    assert not can_play, "Should not be able to play second land this turn"
    assert "already played" in reason.lower(), f"Should mention already played, got: {reason}"
    
    print("   ✅ Land restrictions working correctly")


def run_all_tests():
    """Run all validation tests."""
    print("🚀 Running MTG Core Mechanics Tests")
    print("=" * 50)
    
    try:
        test_mana_system()
        test_timing_restrictions()
        test_land_restrictions()
        
        print("\n" + "=" * 50)
        print("✅ All core mechanics tests PASSED!")
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
