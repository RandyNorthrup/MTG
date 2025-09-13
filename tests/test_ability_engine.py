"""
Test suite for the MTG ability engine system.

Tests implementation of static, triggered, and activated abilities
according to MTG Comprehensive Rules.
"""

import unittest
import os
import sys

# Add the project root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.game_state import GameState, PlayerState
from engine.card_engine import Card, Permanent
from engine.ability_engine import (
    AbilityEngine, TriggerCondition, AbilityInstance, 
    set_ability_engine, emit_game_event
)
from engine.keywords import TriggeredAbility, ActivatedAbility


class TestAbilityParsing(unittest.TestCase):
    """Test ability parsing from card text"""
    
    def setUp(self):
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2")
        self.game = GameState(players=[self.player1, self.player2])
        self.ability_engine = AbilityEngine(self.game)
        set_ability_engine(self.ability_engine)
    
    def test_parse_etb_trigger(self):
        """Test parsing 'enters the battlefield' triggered abilities"""
        card = Card(
            id="etb_creature",
            name="ETB Creature",
            types=["Creature"],
            mana_cost=3,
            power=2,
            toughness=2,
            text="When ETB Creature enters the battlefield, draw a card."
        )
        
        success = self.ability_engine.register_card(card)
        self.assertTrue(success)
        
        triggered_abilities = self.ability_engine.get_triggered_abilities(card)
        self.assertEqual(len(triggered_abilities), 1)
        
        ability = triggered_abilities[0].ability_def
        self.assertEqual(ability.trigger, "ETB")
        self.assertIn("draw a card", ability.effect_text)
    
    def test_parse_attack_trigger(self):
        """Test parsing attack triggered abilities"""
        card = Card(
            id="attack_creature",
            name="Attack Creature", 
            types=["Creature"],
            mana_cost=4,
            power=3,
            toughness=3,
            text="Whenever Attack Creature attacks, it gets +1/+1 until end of turn."
        )
        
        success = self.ability_engine.register_card(card)
        self.assertTrue(success)
        
        triggered_abilities = self.ability_engine.get_triggered_abilities(card)
        self.assertEqual(len(triggered_abilities), 1)
        
        ability = triggered_abilities[0].ability_def
        self.assertEqual(ability.trigger, "ATTACK")
        self.assertIn("gets +1/+1", ability.effect_text)
    
    def test_parse_activated_ability(self):
        """Test parsing activated abilities"""
        card = Card(
            id="activated_creature",
            name="Activated Creature",
            types=["Creature"],
            mana_cost=2,
            power=1,
            toughness=3,
            text="{2}, {T}: Deal 1 damage to target creature."
        )
        
        success = self.ability_engine.register_card(card)
        self.assertTrue(success)
        
        activated_abilities = self.ability_engine.get_activated_abilities(card)
        self.assertEqual(len(activated_abilities), 1)
        
        ability = activated_abilities[0].ability_def
        self.assertTrue(ability.tap_cost)
        self.assertIn("2", ability.mana_cost)
        self.assertTrue(ability.needs_target)
        self.assertEqual(ability.target_hint, "creature")
    
    def test_parse_mana_ability(self):
        """Test parsing mana-producing activated abilities"""
        card = Card(
            id="mana_land",
            name="Mana Land",
            types=["Land"],
            mana_cost=0,
            text="{T}: Add {G}."
        )
        
        success = self.ability_engine.register_card(card)
        self.assertTrue(success)
        
        activated_abilities = self.ability_engine.get_activated_abilities(card)
        self.assertEqual(len(activated_abilities), 1)
        
        ability = activated_abilities[0].ability_def
        self.assertTrue(ability.tap_cost)
        self.assertIn("Add {G}", ability.effect_text)
    
    def test_parse_multiple_abilities(self):
        """Test parsing cards with multiple abilities"""
        card = Card(
            id="multi_ability",
            name="Multi Ability Card",
            types=["Creature"],
            mana_cost=5,
            power=3,
            toughness=4,
            text="When Multi Ability Card enters the battlefield, draw a card. {1}, {T}: Deal 1 damage to target player."
        )
        
        success = self.ability_engine.register_card(card)
        self.assertTrue(success)
        
        triggered_abilities = self.ability_engine.get_triggered_abilities(card)
        activated_abilities = self.ability_engine.get_activated_abilities(card)
        
        self.assertEqual(len(triggered_abilities), 1)
        self.assertEqual(len(activated_abilities), 1)
        
        # Check triggered ability
        triggered = triggered_abilities[0].ability_def
        self.assertEqual(triggered.trigger, "ETB")
        
        # Check activated ability
        activated = activated_abilities[0].ability_def
        self.assertTrue(activated.needs_target)
        self.assertEqual(activated.target_hint, "player")


class TestTriggeredAbilities(unittest.TestCase):
    """Test triggered ability functionality"""
    
    def setUp(self):
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2")
        self.game = GameState(players=[self.player1, self.player2])
        self.ability_engine = AbilityEngine(self.game)
        set_ability_engine(self.ability_engine)
        
        # Ensure players have mana pools
        from engine.mana import ManaPool
        for player in self.game.players:
            if not hasattr(player, 'mana_pool'):
                player.mana_pool = ManaPool()
    
    def test_etb_trigger_fires(self):
        """Test that ETB triggers fire when creatures enter battlefield"""
        card = Card(
            id="etb_drawer",
            name="ETB Drawer",
            types=["Creature"],
            mana_cost=2,
            power=2,
            toughness=2,
            text="When ETB Drawer enters the battlefield, draw a card."
        )
        
        # Add some cards to library for drawing
        for i in range(5):
            self.player1.library.append(Card(f"lib{i}", f"Library Card {i}", ["Instant"], 1))
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield
        perm = Permanent(card=card, summoning_sick=True)
        self.player1.battlefield.append(perm)
        
        initial_hand_size = len(self.player1.hand)
        
        # Emit ETB event
        emit_game_event(TriggerCondition.ENTERS_BATTLEFIELD, 
                       affected=card, controller=0)
        
        # Process triggers
        self.ability_engine.process_triggered_abilities()
        
        # Check that card was drawn
        self.assertEqual(len(self.player1.hand), initial_hand_size + 1)
    
    def test_attack_trigger_fires(self):
        """Test that attack triggers fire when creatures attack"""
        card = Card(
            id="attack_lifelinker",
            name="Attack Lifelinker",
            types=["Creature"],
            mana_cost=3,
            power=2,
            toughness=3,
            text="Whenever Attack Lifelinker attacks, you gain 2 life."
        )
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield
        perm = Permanent(card=card, summoning_sick=False)
        self.player1.battlefield.append(perm)
        
        initial_life = self.player1.life
        
        # Emit attack event
        emit_game_event(TriggerCondition.ATTACKS, 
                       source=card, controller=0)
        
        # Process triggers
        self.ability_engine.process_triggered_abilities()
        
        # Check that life was gained
        self.assertEqual(self.player1.life, initial_life + 2)
    
    def test_upkeep_trigger_fires(self):
        """Test that upkeep triggers fire at beginning of upkeep"""
        card = Card(
            id="upkeep_drawer",
            name="Upkeep Drawer",
            types=["Enchantment"],
            mana_cost=3,
            text="At the beginning of your upkeep, draw a card."
        )
        
        # Add cards to library
        for i in range(5):
            self.player1.library.append(Card(f"lib{i}", f"Library Card {i}", ["Land"], 0))
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield
        perm = Permanent(card=card, summoning_sick=False)
        self.player1.battlefield.append(perm)
        
        initial_hand_size = len(self.player1.hand)
        
        # Emit upkeep event for player 0
        emit_game_event(TriggerCondition.BEGINNING_OF_UPKEEP, controller=0)
        
        # Process triggers
        self.ability_engine.process_triggered_abilities()
        
        # Check that card was drawn
        self.assertEqual(len(self.player1.hand), initial_hand_size + 1)
    
    def test_death_trigger_fires(self):
        """Test that death triggers fire when creatures die"""
        card = Card(
            id="death_drawer",
            name="Death Drawer",
            types=["Creature"],
            mana_cost=2,
            power=1,
            toughness=1,
            text="When Death Drawer dies, draw a card."
        )
        
        # Add cards to library
        for i in range(5):
            self.player1.library.append(Card(f"lib{i}", f"Library Card {i}", ["Instant"], 1))
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield
        perm = Permanent(card=card, summoning_sick=False)
        self.player1.battlefield.append(perm)
        
        initial_hand_size = len(self.player1.hand)
        
        # Emit death event
        emit_game_event(TriggerCondition.DIES, 
                       affected=card, controller=0)
        
        # Process triggers
        self.ability_engine.process_triggered_abilities()
        
        # Check that card was drawn
        self.assertEqual(len(self.player1.hand), initial_hand_size + 1)


class TestActivatedAbilities(unittest.TestCase):
    """Test activated ability functionality"""
    
    def setUp(self):
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2")
        self.game = GameState(players=[self.player1, self.player2])
        self.ability_engine = AbilityEngine(self.game)
        set_ability_engine(self.ability_engine)
        
        # Ensure players have mana pools
        from engine.mana import ManaPool
        for player in self.game.players:
            if not hasattr(player, 'mana_pool'):
                player.mana_pool = ManaPool()
    
    def test_can_activate_with_mana(self):
        """Test that abilities can be activated when costs can be paid"""
        card = Card(
            id="mana_ability",
            name="Mana Ability Card",
            types=["Creature"],
            mana_cost=3,
            power=2,
            toughness=3,
            text="{2}, {T}: Draw a card."
        )
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield (untapped)
        perm = Permanent(card=card, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(perm)
        
        # Add mana to pool
        self.player1.mana_pool.add('C', 2)
        
        # Check if ability can be activated
        can_activate = self.ability_engine.can_activate_ability(0, card, 0)
        self.assertTrue(can_activate)
    
    def test_cannot_activate_without_mana(self):
        """Test that abilities cannot be activated when costs cannot be paid"""
        card = Card(
            id="expensive_ability",
            name="Expensive Ability Card",
            types=["Creature"],
            mana_cost=1,
            power=1,
            toughness=1,
            text="{5}: Deal 3 damage to target creature."
        )
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield
        perm = Permanent(card=card, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(perm)
        
        # Add insufficient mana
        self.player1.mana_pool.add('C', 2)
        
        # Check if ability can be activated
        can_activate = self.ability_engine.can_activate_ability(0, card, 0)
        self.assertFalse(can_activate)
    
    def test_cannot_activate_tapped_creature(self):
        """Test that tap abilities cannot be activated on tapped creatures"""
        card = Card(
            id="tap_ability",
            name="Tap Ability Card",
            types=["Creature"],
            mana_cost=2,
            power=2,
            toughness=2,
            text="{T}: Deal 1 damage to target player."
        )
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield (tapped)
        perm = Permanent(card=card, summoning_sick=False, tapped=True)
        self.player1.battlefield.append(perm)
        
        # Check if ability can be activated
        can_activate = self.ability_engine.can_activate_ability(0, card, 0)
        self.assertFalse(can_activate)
    
    def test_activate_ability_pays_costs(self):
        """Test that activating abilities properly pays costs"""
        card = Card(
            id="cost_ability",
            name="Cost Ability Card",
            types=["Artifact"],
            mana_cost=3,
            text="{1}, {T}: You gain 1 life."
        )
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Put card on battlefield (untapped)
        perm = Permanent(card=card, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(perm)
        
        # Add mana to pool
        self.player1.mana_pool.add('C', 3)
        initial_mana = sum(self.player1.mana_pool.pool.values())
        initial_life = self.player1.life
        
        # Activate ability
        success = self.ability_engine.activate_ability(0, card, 0)
        self.assertTrue(success)
        
        # Check costs were paid
        current_mana = sum(self.player1.mana_pool.pool.values())
        self.assertEqual(current_mana, initial_mana - 1)
        self.assertTrue(perm.tapped)
        
        # Check effect occurred
        self.assertEqual(self.player1.life, initial_life + 1)


class TestAbilityIntegration(unittest.TestCase):
    """Test integration of abilities with game flow"""
    
    def setUp(self):
        self.player1 = PlayerState(player_id=0, name="Player 1")
        self.player2 = PlayerState(player_id=1, name="Player 2")
        self.game = GameState(players=[self.player1, self.player2])
        self.ability_engine = AbilityEngine(self.game)
        set_ability_engine(self.ability_engine)
        
        # Ensure players have mana pools
        from engine.mana import ManaPool
        for player in self.game.players:
            if not hasattr(player, 'mana_pool'):
                player.mana_pool = ManaPool()
    
    def test_complex_card_with_multiple_abilities(self):
        """Test a card with both triggered and activated abilities"""
        card = Card(
            id="complex_card",
            name="Complex Card",
            types=["Creature"],
            mana_cost=4,
            power=2,
            toughness=4,
            text="When Complex Card enters the battlefield, you gain 2 life. {1}, {T}: Draw a card."
        )
        
        # Add cards to library
        for i in range(3):
            self.player1.library.append(Card(f"lib{i}", f"Library Card {i}", ["Land"], 0))
        
        # Register the card
        success = self.ability_engine.register_card(card)
        self.assertTrue(success)
        
        # Check abilities were parsed
        triggered_abilities = self.ability_engine.get_triggered_abilities(card)
        activated_abilities = self.ability_engine.get_activated_abilities(card)
        
        self.assertEqual(len(triggered_abilities), 1)
        self.assertEqual(len(activated_abilities), 1)
        
        # Put card on battlefield
        perm = Permanent(card=card, summoning_sick=False, tapped=False)
        self.player1.battlefield.append(perm)
        
        initial_life = self.player1.life
        initial_hand_size = len(self.player1.hand)
        
        # Emit ETB event
        emit_game_event(TriggerCondition.ENTERS_BATTLEFIELD, 
                       affected=card, controller=0)
        
        # Process triggers
        self.ability_engine.process_triggered_abilities()
        
        # Check ETB trigger worked
        self.assertEqual(self.player1.life, initial_life + 2)
        
        # Add mana and activate ability
        self.player1.mana_pool.add('C', 2)
        success = self.ability_engine.activate_ability(0, card, 0)
        self.assertTrue(success)
        
        # Check activated ability worked
        self.assertEqual(len(self.player1.hand), initial_hand_size + 1)
        self.assertTrue(perm.tapped)
    
    def test_ability_only_triggers_when_on_battlefield(self):
        """Test that triggered abilities only work when card is on battlefield"""
        card = Card(
            id="battlefield_only",
            name="Battlefield Only",
            types=["Creature"],
            mana_cost=2,
            power=2,
            toughness=2,
            text="Whenever Battlefield Only attacks, you gain 1 life."
        )
        
        # Register the card
        self.ability_engine.register_card(card)
        
        # Keep card in hand (not on battlefield)
        self.player1.hand.append(card)
        
        initial_life = self.player1.life
        
        # Emit attack event
        emit_game_event(TriggerCondition.ATTACKS, 
                       source=card, controller=0)
        
        # Process triggers
        self.ability_engine.process_triggered_abilities()
        
        # Check that ability didn't trigger (card not on battlefield)
        self.assertEqual(self.player1.life, initial_life)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAbilityParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestTriggeredAbilities))
    suite.addTests(loader.loadTestsFromTestCase(TestActivatedAbilities))
    suite.addTests(loader.loadTestsFromTestCase(TestAbilityIntegration))
    
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
