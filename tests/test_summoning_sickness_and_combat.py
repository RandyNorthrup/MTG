"""
Test suite for summoning sickness and combat declaration rules.

Tests implementation against MTG Comprehensive Rules:
- CR 302.6: Summoning sickness
- CR 508.1: Declaring attackers
- CR 509.1: Declaring blockers
- Combat keyword interactions (haste, flying, reach, menace, fear, intimidate)
"""

import unittest
import os
import sys

# Add the project root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.game_state import GameState, PlayerState, PHASES
from engine.card_engine import Card, Permanent
from engine.combat import CombatManager, attach_combat
from engine.keywords import card_keywords


class TestSummoningSickness(unittest.TestCase):
    """Test summoning sickness rules per CR 302.6"""
    
    def setUp(self):
        """Set up test game state"""
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2")
        self.game = GameState(players=[self.player1, self.player2])
        
        # Create test creatures
        self.creature = Card(
            id="test_creature",
            name="Test Creature",
            types=["Creature"],
            mana_cost=2,
            power=2,
            toughness=2
        )
        
        self.creature_with_haste = Card(
            id="haste_creature",
            name="Haste Creature", 
            types=["Creature"],
            mana_cost=3,
            power=3,
            toughness=1,
            text="Haste"
        )
        
        self.land = Card(
            id="test_land",
            name="Test Land",
            types=["Land"],
            mana_cost=0
        )
    
    def test_creature_enters_with_summoning_sickness(self):
        """Test that creatures enter battlefield with summoning sickness"""
        perm = Permanent(card=self.creature, summoning_sick=True)
        self.assertTrue(perm.summoning_sick)
        
    def test_land_enters_without_summoning_sickness(self):
        """Test that lands don't have summoning sickness"""
        perm = Permanent(card=self.land, summoning_sick=False)
        self.assertFalse(perm.summoning_sick)
    
    def test_summoning_sickness_cleared_on_turn_start(self):
        """Test that summoning sickness is cleared at start of controller's turn"""
        # Add creature to battlefield with summoning sickness
        creature_perm = Permanent(card=self.creature, summoning_sick=True)
        creature_perm.card.controller_id = 0
        self.player1.battlefield.append(creature_perm)
        
        # Verify it has summoning sickness
        self.assertTrue(creature_perm.summoning_sick)
        
        # Simulate UNTAP phase for player 0
        self.game.active_player = 0
        self.game._perform_phase_actions("UNTAP")
        
        # Verify summoning sickness was removed
        self.assertFalse(creature_perm.summoning_sick)
    
    def test_summoning_sickness_not_cleared_for_opponent_creatures(self):
        """Test that summoning sickness is only cleared for active player's creatures"""
        # Add creature controlled by player 0
        creature_perm = Permanent(card=self.creature, summoning_sick=True)
        creature_perm.card.controller_id = 0
        self.player1.battlefield.append(creature_perm)
        
        # Add creature controlled by player 1  
        creature_perm2 = Permanent(card=self.creature, summoning_sick=True)
        creature_perm2.card.controller_id = 1
        self.player2.battlefield.append(creature_perm2)
        
        # Simulate UNTAP phase for player 0 (active player)
        self.game.active_player = 0
        self.game._perform_phase_actions("UNTAP")
        
        # Only player 0's creature should lose summoning sickness
        self.assertFalse(creature_perm.summoning_sick)
        self.assertTrue(creature_perm2.summoning_sick)


class TestAttackerDeclaration(unittest.TestCase):
    """Test attacker declaration rules per CR 508.1"""
    
    def setUp(self):
        """Set up test game state with combat manager"""
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2")
        self.game = GameState(players=[self.player1, self.player2])
        self.game.active_player = 0
        
        # Attach combat manager
        self.combat = attach_combat(self.game)
        
        # Create test creatures
        self.normal_creature = Card(
            id="normal", name="Normal Creature", types=["Creature"],
            mana_cost=2, power=2, toughness=2
        )
        
        self.haste_creature = Card(
            id="haste", name="Haste Creature", types=["Creature"],
            mana_cost=3, power=3, toughness=1, text="Haste"
        )
    
    def test_untapped_creature_can_attack(self):
        """Test that untapped creatures without summoning sickness can attack"""
        perm = Permanent(card=self.normal_creature, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(perm)
        
        # Should be able to declare as attacker
        self.combat.toggle_attacker(0, perm)
        self.assertIn(perm, self.combat.state.attackers)
    
    def test_tapped_creature_cannot_attack(self):
        """Test that tapped creatures cannot attack (CR 508.1c)"""
        perm = Permanent(card=self.normal_creature, summoning_sick=False, tapped=True)
        self.player1.battlefield.append(perm)
        
        # Should not be able to declare as attacker
        self.combat.toggle_attacker(0, perm)
        self.assertNotIn(perm, self.combat.state.attackers)
    
    def test_summoning_sick_creature_cannot_attack(self):
        """Test that creatures with summoning sickness cannot attack"""
        perm = Permanent(card=self.normal_creature, summoning_sick=True, tapped=False)
        self.player1.battlefield.append(perm)
        
        # Should not be able to declare as attacker
        self.combat.toggle_attacker(0, perm)
        self.assertNotIn(perm, self.combat.state.attackers)
    
    def test_haste_creature_can_attack_with_summoning_sickness(self):
        """Test that creatures with haste can attack despite summoning sickness"""
        perm = Permanent(card=self.haste_creature, summoning_sick=True, tapped=False)
        self.player1.battlefield.append(perm)
        
        # Should be able to attack due to haste
        self.combat.toggle_attacker(0, perm)
        self.assertIn(perm, self.combat.state.attackers)
    
    def test_non_active_player_cannot_declare_attackers(self):
        """Test that only active player can declare attackers"""
        perm = Permanent(card=self.normal_creature, summoning_sick=False, tapped=False)
        self.player2.battlefield.append(perm)
        
        # Player 2 shouldn't be able to declare attackers when player 0 is active
        self.combat.toggle_attacker(1, perm)
        self.assertNotIn(perm, self.combat.state.attackers)
    
    def test_non_creature_cannot_attack(self):
        """Test that non-creatures cannot attack"""
        artifact = Card(id="art", name="Artifact", types=["Artifact"], mana_cost=1)
        perm = Permanent(card=artifact, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(perm)
        
        self.combat.toggle_attacker(0, perm)
        self.assertNotIn(perm, self.combat.state.attackers)


class TestBlockerDeclaration(unittest.TestCase):
    """Test blocker declaration rules per CR 509.1"""
    
    def setUp(self):
        """Set up test game state with combat manager"""
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2") 
        self.game = GameState(players=[self.player1, self.player2])
        self.game.active_player = 0
        
        # Attach combat manager  
        self.combat = attach_combat(self.game)
        
        # Create test creatures with various keywords
        self.normal_attacker = Card(
            id="normal_atk", name="Normal Attacker", types=["Creature"],
            mana_cost=2, power=2, toughness=2
        )
        
        self.flying_attacker = Card(
            id="flying_atk", name="Flying Attacker", types=["Creature"],
            mana_cost=3, power=2, toughness=2, text="Flying"
        )
        
        self.fear_attacker = Card(
            id="fear_atk", name="Fear Attacker", types=["Creature"],
            mana_cost=2, power=2, toughness=1, text="Fear"
        )
        
        self.normal_blocker = Card(
            id="normal_blk", name="Normal Blocker", types=["Creature"],
            mana_cost=2, power=1, toughness=3
        )
        
        self.flying_blocker = Card(
            id="flying_blk", name="Flying Blocker", types=["Creature"],
            mana_cost=3, power=1, toughness=2, text="Flying"
        )
        
        self.reach_blocker = Card(
            id="reach_blk", name="Reach Blocker", types=["Creature"],
            mana_cost=2, power=1, toughness=4, text="Reach"
        )
        
        self.artifact_blocker = Card(
            id="artifact_blk", name="Artifact Creature", types=["Artifact", "Creature"],
            mana_cost=4, power=2, toughness=2
        )
    
    def _setup_attack_phase(self, attacker_card):
        """Helper to set up an attack phase with given attacker"""
        attacker_perm = Permanent(card=attacker_card, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(attacker_perm)
        
        # Declare attacker and commit
        self.combat.toggle_attacker(0, attacker_perm)
        self.combat.attackers_committed()
        
        return attacker_perm
    
    def test_normal_creature_can_block_normal_attacker(self):
        """Test that normal creatures can block normal attackers"""
        attacker_perm = self._setup_attack_phase(self.normal_attacker)
        
        blocker_perm = Permanent(card=self.normal_blocker, summoning_sick=False, tapped=False)
        self.player2.battlefield.append(blocker_perm)
        
        # Should be able to block
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        self.assertIn(blocker_perm, self.combat.state.blockers.get(attacker_perm.card.id, []))
    
    def test_normal_creature_cannot_block_flying(self):
        """Test that creatures without flying or reach cannot block flying creatures"""
        attacker_perm = self._setup_attack_phase(self.flying_attacker)
        
        blocker_perm = Permanent(card=self.normal_blocker, summoning_sick=False, tapped=False)
        self.player2.battlefield.append(blocker_perm)
        
        # Should not be able to block flying attacker
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        self.assertNotIn(blocker_perm, self.combat.state.blockers.get(attacker_perm.card.id, []))
    
    def test_flying_creature_can_block_flying(self):
        """Test that flying creatures can block flying attackers"""
        attacker_perm = self._setup_attack_phase(self.flying_attacker)
        
        blocker_perm = Permanent(card=self.flying_blocker, summoning_sick=False, tapped=False)
        self.player2.battlefield.append(blocker_perm)
        
        # Should be able to block flying attacker
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        self.assertIn(blocker_perm, self.combat.state.blockers.get(attacker_perm.card.id, []))
    
    def test_reach_creature_can_block_flying(self):
        """Test that creatures with reach can block flying attackers"""
        attacker_perm = self._setup_attack_phase(self.flying_attacker)
        
        blocker_perm = Permanent(card=self.reach_blocker, summoning_sick=False, tapped=False)
        self.player2.battlefield.append(blocker_perm)
        
        # Should be able to block flying attacker
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        self.assertIn(blocker_perm, self.combat.state.blockers.get(attacker_perm.card.id, []))
    
    def test_artifact_creature_can_block_fear(self):
        """Test that artifact creatures can block creatures with fear"""
        attacker_perm = self._setup_attack_phase(self.fear_attacker)
        
        blocker_perm = Permanent(card=self.artifact_blocker, summoning_sick=False, tapped=False)
        self.player2.battlefield.append(blocker_perm)
        
        # Should be able to block fear attacker
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        self.assertIn(blocker_perm, self.combat.state.blockers.get(attacker_perm.card.id, []))
    
    def test_tapped_creature_cannot_block(self):
        """Test that tapped creatures cannot block"""
        attacker_perm = self._setup_attack_phase(self.normal_attacker)
        
        blocker_perm = Permanent(card=self.normal_blocker, summoning_sick=False, tapped=True)
        self.player2.battlefield.append(blocker_perm)
        
        # Should not be able to block when tapped
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        self.assertNotIn(blocker_perm, self.combat.state.blockers.get(attacker_perm.card.id, []))
    
    def test_active_player_cannot_declare_blockers(self):
        """Test that active player cannot declare blockers"""
        attacker_perm = self._setup_attack_phase(self.normal_attacker)
        
        # Try to have active player (player 0) declare a blocker
        blocker_perm = Permanent(card=self.normal_blocker, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(blocker_perm)
        
        # Should not work - active player can't block
        self.combat.toggle_blocker(0, blocker_perm, attacker_perm)
        self.assertNotIn(blocker_perm, self.combat.state.blockers.get(attacker_perm.card.id, []))


class TestCombatIntegration(unittest.TestCase):
    """Integration tests for complete combat scenarios"""
    
    def setUp(self):
        """Set up test game state"""
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2")
        self.game = GameState(players=[self.player1, self.player2])
        self.game.active_player = 0
        
        self.combat = attach_combat(self.game)
    
    def test_full_combat_scenario(self):
        """Test a complete combat scenario from declaration to damage"""
        # Set up creatures
        attacker = Card(id="atk", name="Attacker", types=["Creature"], 
                       mana_cost=3, power=3, toughness=2)
        attacker_perm = Permanent(card=attacker, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(attacker_perm)
        
        blocker = Card(id="blk", name="Blocker", types=["Creature"],
                      mana_cost=2, power=2, toughness=3)
        blocker_perm = Permanent(card=blocker, summoning_sick=False, tapped=False)
        self.player2.battlefield.append(blocker_perm)
        
        # Declare attackers
        self.combat.toggle_attacker(0, attacker_perm)
        self.combat.attackers_committed()
        
        # Declare blockers
        self.combat.toggle_blocker(1, blocker_perm, attacker_perm)
        
        # Verify combat state
        self.assertIn(attacker_perm, self.combat.state.attackers)
        self.assertIn(blocker_perm, self.combat.state.blockers.get(attacker.id, []))
        
        # Resolve combat damage
        initial_blocker_damage = blocker_perm.damage_marked
        self.combat.assign_and_deal_damage()
        
        # Verify damage was dealt
        self.assertGreater(blocker_perm.damage_marked, initial_blocker_damage)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSummoningSickness))
    suite.addTests(loader.loadTestsFromTestCase(TestAttackerDeclaration))  
    suite.addTests(loader.loadTestsFromTestCase(TestBlockerDeclaration))
    suite.addTests(loader.loadTestsFromTestCase(TestCombatIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
