#!/usr/bin/env python3
"""
Comprehensive test of all play systems after code cleanup.
Tests core mechanics, combat, abilities, phases, and UI integration.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'engine'))

from engine.mana import ManaPool, parse_mana_cost
from engine.card_engine import Card, Permanent
from engine.game_state import GameState, PlayerState
from engine.rules_engine import RulesEngine, parse_oracle_text, init_rules
from engine.combat import CombatManager
from engine.stack import GameStack, StackItem
from engine.keywords import StaticKeywordAbility, TriggeredAbility, ActivatedAbility

def create_test_card(name, types=None, mana_cost=0, mana_cost_str="", power=None, toughness=None, text=""):
    """Helper function to create test cards with proper parameters"""
    import uuid
    return Card(
        id=str(uuid.uuid4()),
        name=name,
        types=types or [],
        mana_cost=mana_cost,
        mana_cost_str=mana_cost_str,
        power=power,
        toughness=toughness,
        text=text
    )


class TestCoreMechanics(unittest.TestCase):
    """Test core game mechanics: mana, casting, land drops"""
    
    def setUp(self):
        players = [PlayerState(player_id=0, name="Player1"), PlayerState(player_id=1, name="Player2")]
        self.game = GameState(players=players)
        self.rules = init_rules(self.game)
        
    def test_mana_generation_and_payment(self):
        """Test mana generation from lands and payment for spells"""
        player = self.game.players[0]
        
        # Create and play a Forest
        forest = create_test_card("Forest", ["Basic", "Land"], text="Add {G}.")
        player.hand.append(forest)
        
        # Play the land
        result = self.game.play_land(0, forest)
        self.assertEqual(result, "OK")
        self.assertTrue(len(player.battlefield) == 1)
        
        # Tap for mana
        land_perm = player.battlefield[0]
        self.game.tap_for_mana(0, land_perm)
        self.assertEqual(player.mana, 1)
        self.assertTrue(land_perm.tapped)
        
    def test_creature_casting(self):
        """Test creature casting with mana cost"""
        player = self.game.players[0]
        player.mana = 2
        
        # Create a creature
        bear = create_test_card("Grizzly Bears", ["Creature"], mana_cost=2, power=2, toughness=2)
        player.hand.append(bear)
        
        # Cast the creature
        result = self.game.cast_spell(0, bear)
        self.assertEqual(result, "OK")
        self.assertEqual(player.mana, 0)  # Mana spent
        self.assertTrue(len(player.battlefield) == 1)
        
    def test_spell_casting(self):
        """Test instant/sorcery casting"""
        player = self.game.players[0]
        player.mana = 1
        
        # Create a sorcery
        bolt = create_test_card("Lightning Bolt", ["Sorcery"], mana_cost=1, text="Deal 3 damage.")
        player.hand.append(bolt)
        
        # Cast the spell
        result = self.game.cast_spell(0, bolt)
        self.assertEqual(result, "OK")
        self.assertEqual(player.mana, 0)  # Mana spent
        self.assertTrue(bolt not in player.hand)  # Removed from hand


class TestCombatSystem(unittest.TestCase):
    """Test combat mechanics: attacking, blocking, damage"""
    
    def setUp(self):
        players = [PlayerState(player_id=0, name="Player1"), PlayerState(player_id=1, name="Player2")]
        self.game = GameState(players=players)
        self.combat = CombatManager(self.game)
        
    def test_creature_attacking(self):
        """Test basic creature attacking"""
        player = self.game.players[0]
        
        # Create attacking creature
        attacker = create_test_card("Attacking Creature", ["Creature"], power=2, toughness=2)
        attacker_perm = Permanent(attacker)
        player.battlefield.append(attacker_perm)
        
        # Declare attacker
        self.combat.toggle_attacker(0, attacker_perm)
        self.assertTrue(attacker_perm in self.combat.state.attackers)
        
    def test_blocking_mechanics(self):
        """Test creature blocking"""
        player1 = self.game.players[0]
        player2 = self.game.players[1]
        
        # Create attacker and blocker
        attacker = create_test_card("Attacker", ["Creature"], power=2, toughness=2)
        attacker_perm = Permanent(attacker)
        player1.battlefield.append(attacker_perm)
        
        blocker = create_test_card("Blocker", ["Creature"], power=1, toughness=3)
        blocker_perm = Permanent(blocker)
        player2.battlefield.append(blocker_perm)
        
        # Declare attacker
        self.combat.toggle_attacker(0, attacker_perm)
        self.combat.attackers_committed()
        
        # Declare blocker
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        blockers = self.combat.state.blockers.get(attacker.id, [])
        self.assertTrue(blocker_perm in blockers)
        
    def test_flying_blocking_restriction(self):
        """Test flying creatures can't be blocked by non-flying"""
        player1 = self.game.players[0]
        player2 = self.game.players[1]
        
        # Create flying attacker
        flyer = create_test_card("Flying Creature", ["Creature"], power=2, toughness=2, text="Flying")
        flyer_perm = Permanent(flyer)
        player1.battlefield.append(flyer_perm)
        
        # Parse abilities
        from engine.rules_engine import parse_and_attach
        parse_and_attach(flyer)
        
        # Create ground blocker
        ground = create_test_card("Ground Creature", ["Creature"], power=3, toughness=3)
        ground_perm = Permanent(ground)
        player2.battlefield.append(ground_perm)
        
        # Try to block flying creature with ground creature
        self.combat.toggle_attacker(0, flyer_perm)
        self.combat.attackers_committed()
        
        # This should not create a valid block due to flying restriction
        before_block = len(self.combat.state.blockers.get(flyer.id, []))
        self.combat.toggle_blocker(1, ground_perm, flyer_perm)
        after_block = len(self.combat.state.blockers.get(flyer.id, []))
        self.assertEqual(before_block, after_block)  # No change - block not allowed


class TestAbilitySystem(unittest.TestCase):
    """Test ability parsing and triggered abilities"""
    
    def test_keyword_ability_parsing(self):
        """Test parsing of keyword abilities"""
        flying_text = "Flying"
        abilities = parse_oracle_text(flying_text)
        
        self.assertEqual(len(abilities), 1)
        self.assertIsInstance(abilities[0], StaticKeywordAbility)
        self.assertEqual(abilities[0].keyword, "Flying")
        
    def test_triggered_ability_parsing(self):
        """Test parsing of triggered abilities"""
        etb_text = "When this creature enters the battlefield, draw a card."
        abilities = parse_oracle_text(etb_text)
        
        self.assertEqual(len(abilities), 1)
        self.assertIsInstance(abilities[0], TriggeredAbility)
        self.assertEqual(abilities[0].trigger, "ETB")
        
    def test_activated_ability_parsing(self):
        """Test parsing of activated abilities"""
        tap_text = "{T}: Add {G}."
        abilities = parse_oracle_text(tap_text)
        
        self.assertEqual(len(abilities), 1)
        self.assertIsInstance(abilities[0], ActivatedAbility)
        self.assertTrue(abilities[0].tap_cost)
        
    def test_complex_ability_parsing(self):
        """Test parsing multiple abilities on one card"""
        complex_text = "Flying\nWhen this creature enters the battlefield, draw a card.\n{2}: Deal 1 damage to any target."
        abilities = parse_oracle_text(complex_text)
        
        self.assertGreaterEqual(len(abilities), 2)
        # Should have keyword, triggered, and/or activated abilities
        ability_types = [type(ab).__name__ for ab in abilities]
        self.assertTrue(any("Keyword" in t for t in ability_types) or 
                       any("Triggered" in t for t in ability_types))


class TestPhaseProgression(unittest.TestCase):
    """Test turn structure and phase progression"""
    
    def setUp(self):
        players = [PlayerState(player_id=0, name="Player1"), PlayerState(player_id=1, name="Player2")]
        self.game = GameState(players=players)
        
    def test_phase_sequence(self):
        """Test that phases progress in correct order"""
        from engine.game_state import PHASES
        
        initial_phase_idx = self.game.phase_index
        initial_phase = self.game.phase
        
        # Advance phase
        self.game.next_phase()
        
        # Should advance to next phase
        expected_next_idx = (initial_phase_idx + 1) % len(PHASES)
        # May skip auto phases, so just check we progressed
        self.assertNotEqual(self.game.phase_index, initial_phase_idx)
        
    def test_turn_increment(self):
        """Test that turns increment correctly"""
        initial_turn = self.game.turn
        initial_player = self.game.active_player
        
        # Go through a full turn cycle by setting to cleanup phase
        self.game.phase_index = 11  # CLEANUP is last phase
        self.game.next_phase()  # This should start new turn
        
        # Turn should increment and player should switch
        self.assertGreater(self.game.turn, initial_turn)
        
    def test_untap_step_actions(self):
        """Test untap step untaps permanents"""
        player = self.game.players[0]
        
        # Create tapped creature
        creature = create_test_card("Test Creature", ["Creature"], power=2, toughness=2)
        creature_perm = Permanent(creature)
        creature_perm.tapped = True
        player.battlefield.append(creature_perm)
        
        # Perform untap actions
        self.game._perform_phase_actions("UNTAP")
        
        # Creature should be untapped
        self.assertFalse(creature_perm.tapped)


class TestStackSystem(unittest.TestCase):
    """Test stack and priority system"""
    
    def setUp(self):
        players = [PlayerState(player_id=0, name="Player1"), PlayerState(player_id=1, name="Player2")]
        self.game = GameState(players=players)
        self.game.stack = GameStack(self.game)
        
    def test_stack_lifo_order(self):
        """Test stack resolves in LIFO order"""
        resolved_order = []
        
        def create_resolver(name):
            def resolve_fn(game, item):
                resolved_order.append(name)
            return resolve_fn
        
        # Add items to stack
        item1 = StackItem(label="First", resolve_fn=create_resolver("First"))
        item2 = StackItem(label="Second", resolve_fn=create_resolver("Second"))
        
        self.game.stack.push(item1)
        self.game.stack.push(item2)
        
        # Resolve stack
        while self.game.stack.can_resolve():
            self.game.stack.resolve_top(self.game)
            
        # Should resolve in LIFO order
        self.assertEqual(resolved_order, ["Second", "First"])


class TestCommanderMechanics(unittest.TestCase):
    """Test Commander-specific rules"""
    
    def test_commander_tax(self):
        """Test commander tax increases with each cast"""
        from engine.rules_engine import CommanderTracker
        
        tracker = CommanderTracker()
        commander_id = "test-commander"
        
        # Initial tax should be 0
        self.assertEqual(tracker.tax_for(commander_id), 0)
        
        # After casting, tax should increase by 2
        tracker.note_cast(commander_id)
        self.assertEqual(tracker.tax_for(commander_id), 2)
        
        # After second cast, tax should be 4
        tracker.note_cast(commander_id)
        self.assertEqual(tracker.tax_for(commander_id), 4)
        
    def test_commander_damage(self):
        """Test commander damage tracking"""
        from engine.rules_engine import CommanderTracker
        
        tracker = CommanderTracker()
        defender_id = 1
        commander_owner = 0
        
        # Deal damage over multiple turns
        tracker.add_damage(defender_id, commander_owner, 15)
        tracker.add_damage(defender_id, commander_owner, 6)
        
        # Should be lethal (21+ damage)
        self.assertTrue(tracker.lethal_from(defender_id, commander_owner))


class TestManaSystemAdvanced(unittest.TestCase):
    """Test advanced mana system features"""
    
    def test_mana_pool_autotap(self):
        """Test automatic land tapping for mana"""
        pool = ManaPool()
        battlefield = []
        
        # Create lands on battlefield
        forest = create_test_card("Forest", ["Basic", "Land"], text="Add {G}.")
        forest_perm = Permanent(forest)
        battlefield.append(forest_perm)
        
        # Test autotap functionality
        cost = {'G': 1}
        result = pool.autotap_for_cost(battlefield, cost)
        
        # Should successfully tap land
        self.assertTrue(result)
        
    def test_hybrid_mana_parsing(self):
        """Test hybrid mana cost parsing"""
        # Hybrid costs are simplified as generic in this implementation
        cost = parse_mana_cost("{2/R}{W}")
        self.assertIn('C', cost)  # Hybrid treated as generic
        self.assertIn('W', cost)  # White mana required


def run_comprehensive_tests():
    """Run all play system tests"""
    print("=" * 60)
    print("COMPREHENSIVE PLAY SYSTEMS TEST SUITE")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestCoreMechanics,
        TestCombatSystem,
        TestAbilitySystem,
        TestPhaseProgression,
        TestStackSystem,
        TestCommanderMechanics,
        TestManaSystemAdvanced
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PLAY SYSTEMS TEST RESULTS")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ ALL PLAY SYSTEMS WORKING CORRECTLY!")
        success_rate = 100.0
    else:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"Success rate: {success_rate:.1f}%")
        
        if result.failures:
            print(f"\nFAILURES ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"- {test}")
                
        if result.errors:
            print(f"\nERRORS ({len(result.errors)}):")
            for test, traceback in result.errors:
                print(f"- {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
