"""MTG Card Mechanics Test Suite.

Comprehensive test suite for the card mechanics systems:
- Mana cost parsing and validation
- Timing restrictions and playability
- Card abilities and interactions
- Stack and priority management

Run with: python -m pytest tests/ or python tests/test_card_mechanics.py
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.casting_system import ManaCostParser, PlayabilityChecker, CastingEngine
from engine.abilities_system import KeywordAbilities, TriggeredAbilityParser, AbilityManager, TriggerEvent
from engine.stack_system import StackController, Stack, StackObject
from engine.mana import ManaPool, parse_mana_cost
from engine.card_engine import Card, Permanent
from engine.gameplay_integration import GameplayController


class MockPlayer:
    """Mock player for testing."""
    def __init__(self, player_id=0):
        self.player_id = player_id
        self.name = f"Player {player_id}"
        self.life = 20
        self.mana_pool = ManaPool()
        self.hand = []
        self.battlefield = []
        self.graveyard = []
        self.library = []
        self.command = []
        self.lands_played_this_turn = 0
        self.max_lands_per_turn = 1
        self.commander_casts = 0
        self.eliminated = False
    
    def draw(self):
        if self.library:
            card = self.library.pop()
            self.hand.append(card)


class MockGame:
    """Mock game for testing."""
    def __init__(self):
        self.players = [MockPlayer(0), MockPlayer(1)]
        self.active_player = 0
        self.phase = "MAIN1"
        self.turn = 1
        self.stack = []


class TestManaCostParser(unittest.TestCase):
    """Test mana cost parsing functionality."""
    
    def test_simple_costs(self):
        """Test parsing of simple mana costs."""
        # Colorless costs
        result = ManaCostParser.parse_cost_string("{3}")
        self.assertEqual(result, {"C": 3})
        
        # Single color costs
        result = ManaCostParser.parse_cost_string("{R}")
        self.assertEqual(result, {"R": 1})
        
        # Mixed costs
        result = ManaCostParser.parse_cost_string("{2}{R}{R}")
        self.assertEqual(result, {"C": 2, "R": 2})
        
    def test_complex_costs(self):
        """Test parsing of complex mana costs."""
        # Multiple colors
        result = ManaCostParser.parse_cost_string("{1}{W}{U}{B}")
        self.assertEqual(result, {"C": 1, "W": 1, "U": 1, "B": 1})
        
        # Variable costs
        result = ManaCostParser.parse_cost_string("{X}{R}")
        self.assertEqual(result, {"X": 1, "R": 1})
        
    def test_cmc_calculation(self):
        """Test CMC calculation."""
        self.assertEqual(ManaCostParser.calculate_cmc("{3}{R}{R}"), 5)
        self.assertEqual(ManaCostParser.calculate_cmc("{W}{U}{B}{R}{G}"), 5)
        self.assertEqual(ManaCostParser.calculate_cmc("{X}{R}"), 1)  # X is 0 for CMC
        self.assertEqual(ManaCostParser.calculate_cmc(""), 0)


class TestManaPool(unittest.TestCase):
    """Test mana pool functionality."""
    
    def setUp(self):
        self.pool = ManaPool()
    
    def test_add_mana(self):
        """Test adding mana to pool."""
        self.pool.add("R", 2)
        self.pool.add("G", 1)
        
        self.assertEqual(self.pool.pool["R"], 2)
        self.assertEqual(self.pool.pool["G"], 1)
        
    def test_can_pay(self):
        """Test mana payment checking."""
        self.pool.add("R", 2)
        self.pool.add("G", 1)
        self.pool.add("C", 3)
        
        # Can pay exact costs
        self.assertTrue(self.pool.can_pay({"R": 1, "G": 1}))
        self.assertTrue(self.pool.can_pay({"C": 2}))
        
        # Cannot pay more than available
        self.assertFalse(self.pool.can_pay({"R": 3}))
        self.assertFalse(self.pool.can_pay({"B": 1}))
        
        # Colored mana can pay generic costs
        self.assertTrue(self.pool.can_pay({"C": 5}))  # 2R + 1G + 3C = 6 total
        
    def test_pay_costs(self):
        """Test actually paying costs."""
        self.pool.add("R", 2)
        self.pool.add("C", 2)
        
        # Pay exact cost
        self.assertTrue(self.pool.pay({"R": 1}))
        self.assertEqual(self.pool.pool["R"], 1)
        
        # Pay generic - uses colorless first, then colored
        self.assertTrue(self.pool.pay({"C": 2}))
        self.assertEqual(self.pool.pool["C"], 0)  # Used up all colorless first
        self.assertEqual(self.pool.pool["R"], 1)   # Still have 1 red left


class TestKeywordAbilities(unittest.TestCase):
    """Test keyword ability parsing."""
    
    def test_basic_keywords(self):
        """Test parsing of basic keyword abilities."""
        card = Card(
            id="test1",
            name="Test Creature", 
            types=["Creature"],
            mana_cost=2,
            text="Flying, Trample, Haste"
        )
        
        abilities = KeywordAbilities.parse_keywords(card)
        ability_texts = [ability.text for ability in abilities]
        
        self.assertIn("Flying", ability_texts)
        self.assertIn("Trample", ability_texts)
        self.assertIn("Haste", ability_texts)
        
    def test_tap_ability_parsing(self):
        """Test parsing of tap abilities."""
        card = Card(
            id="test2",
            name="Test Land",
            types=["Land"],
            mana_cost=0,
            text="{T}: Add {G}."
        )
        
        ability = KeywordAbilities.parse_tap_ability(card)
        self.assertIsNotNone(ability)
        self.assertEqual(ability.text, "{T}: Add {G}.")
        
    def test_mana_production_parsing(self):
        """Test parsing mana production from text."""
        result = KeywordAbilities.parse_mana_production("Add {G}")
        self.assertEqual(result, {"G": 1})
        
        result = KeywordAbilities.parse_mana_production("Add {W} or {U}")
        # This should find both W and U
        self.assertIn("W", result)
        self.assertIn("U", result)


class TestTriggeredAbilities(unittest.TestCase):
    """Test triggered ability parsing."""
    
    def test_etb_triggers(self):
        """Test ETB ability parsing."""
        card = Card(
            id="test3",
            name="Test Creature",
            types=["Creature"],
            mana_cost=3,
            text="When Test Creature enters the battlefield, draw a card."
        )
        
        abilities = TriggeredAbilityParser.parse_triggered_abilities(card)
        self.assertEqual(len(abilities), 1)
        self.assertIn(TriggerEvent.ENTERS_BATTLEFIELD, abilities[0].trigger_events)
        
    def test_death_triggers(self):
        """Test death trigger parsing."""
        card = Card(
            id="test4",
            name="Test Creature",
            types=["Creature"], 
            mana_cost=2,
            text="When Test Creature dies, deal 1 damage to any target."
        )
        
        abilities = TriggeredAbilityParser.parse_triggered_abilities(card)
        self.assertEqual(len(abilities), 1)
        self.assertIn(TriggerEvent.DIES, abilities[0].trigger_events)
        
    def test_optional_triggers(self):
        """Test optional trigger detection."""
        card = Card(
            id="test5",
            name="Test Creature",
            types=["Creature"],
            mana_cost=3,
            text="When Test Creature enters the battlefield, you may draw a card."
        )
        
        abilities = TriggeredAbilityParser.parse_triggered_abilities(card)
        self.assertEqual(len(abilities), 1)
        self.assertTrue(abilities[0].optional)


class TestPlayabilityChecker(unittest.TestCase):
    """Test card playability checking."""
    
    def setUp(self):
        self.game = MockGame()
        self.checker = PlayabilityChecker(self.game)
        self.player = self.game.players[0]
        
    def test_mana_requirements(self):
        """Test mana requirement checking."""
        card = Card(
            id="test6",
            name="Lightning Bolt",
            types=["Instant"],
            mana_cost=1,
            mana_cost_str="{R}"
        )
        
        # Add card to hand
        self.player.hand.append(card)
        
        # No mana - cannot play
        can_play, reason = self.checker.can_play_card(self.player, card)
        self.assertFalse(can_play)
        self.assertIn("mana", reason.lower())
        
        # Add mana - can play
        self.player.mana_pool.add("R", 1)
        can_play, reason = self.checker.can_play_card(self.player, card)
        self.assertTrue(can_play)
        
    def test_timing_restrictions(self):
        """Test timing restrictions."""
        # Sorcery in main phase
        sorcery = Card(
            id="test7",
            name="Test Sorcery",
            types=["Sorcery"],
            mana_cost=2,
            mana_cost_str="{2}"
        )
        
        self.player.hand.append(sorcery)
        self.player.mana_pool.add("C", 2)
        
        # Main phase - can play
        self.game.phase = "MAIN1"
        can_play, _ = self.checker.can_play_card(self.player, sorcery)
        self.assertTrue(can_play)
        
        # Combat phase - cannot play
        self.game.phase = "COMBAT"
        can_play, reason = self.checker.can_play_card(self.player, sorcery)
        self.assertFalse(can_play)
        self.assertIn("main phase", reason.lower())
        
    def test_land_timing(self):
        """Test land play restrictions."""
        land = Card(
            id="test8",
            name="Forest",
            types=["Land"],
            mana_cost=0
        )
        
        self.player.hand.append(land)
        
        # Can play first land
        can_play, _ = self.checker.can_play_card(self.player, land)
        self.assertTrue(can_play)
        
        # Cannot play second land
        self.player.lands_played_this_turn = 1
        can_play, reason = self.checker.can_play_card(self.player, land)
        self.assertFalse(can_play)
        self.assertIn("already played", reason.lower())
    
    def test_zone_restrictions(self):
        """Test zone-based restrictions."""
        card = Card(
            id="test9",
            name="Test Spell",
            types=["Instant"],
            mana_cost=1
        )
        
        # Not in hand - cannot play
        can_play, reason = self.checker.can_play_card(self.player, card)
        self.assertFalse(can_play)
        self.assertIn("playable zone", reason.lower())
        
        # In hand - can play (with mana)
        self.player.hand.append(card)
        self.player.mana_pool.add("C", 1)
        can_play, _ = self.checker.can_play_card(self.player, card)
        self.assertTrue(can_play)


class TestStackSystem(unittest.TestCase):
    """Test stack system functionality."""
    
    def setUp(self):
        self.game = MockGame()
        self.stack_controller = StackController(self.game)
        self.player = self.game.players[0]
        
    def test_spell_on_stack(self):
        """Test adding spells to stack."""
        card = Card(
            id="test10",
            name="Lightning Bolt",
            types=["Instant"],
            mana_cost=1,
            mana_cost_str="{R}"
        )
        
        self.player.hand.append(card)
        self.player.mana_pool.add("R", 1)
        
        # Cast spell
        success = self.stack_controller.cast_spell(self.player, card)
        self.assertTrue(success)
        
        # Check stack has the spell
        self.assertFalse(self.stack_controller.is_stack_empty())
        self.assertEqual(self.stack_controller.get_stack_size(), 1)
        
        stack_info = self.stack_controller.get_stack_info()
        self.assertEqual(len(stack_info), 1)
        self.assertEqual(stack_info[0]["name"], "Lightning Bolt")
        
    def test_priority_system(self):
        """Test priority passing."""
        # Give initial priority
        self.stack_controller.priority_manager.give_priority(self.player)
        
        # Player has priority
        self.assertTrue(self.stack_controller.priority_manager.has_priority(self.player))
        
        # Pass priority
        all_passed = self.stack_controller.pass_priority(self.player)
        
        # Should advance to next player (simplified test)
        self.assertFalse(self.stack_controller.priority_manager.has_priority(self.player))
        
    def test_stack_resolution(self):
        """Test resolving stack objects."""
        stack = Stack()
        
        # Create mock stack object
        card = Card(
            id="test11",
            name="Test Instant",
            types=["Instant"],
            mana_cost=1
        )
        
        stack_obj = stack.add_spell(self.player, card)
        
        # Resolve
        resolved = stack.resolve_top(self.game)
        self.assertIsNotNone(resolved)
        self.assertTrue(stack.is_empty())


class TestGameplayIntegration(unittest.TestCase):
    """Test the integration layer."""
    
    def setUp(self):
        self.game = MockGame()
        self.controller = GameplayController(self.game)
        self.player = self.game.players[0]
        
        # Initialize player
        self.controller.initialize_player(self.player)
    
    def test_player_initialization(self):
        """Test player gets properly initialized."""
        self.assertIsNotNone(self.player.mana_pool)
        self.assertEqual(self.player.lands_played_this_turn, 0)
        self.assertEqual(self.player.max_lands_per_turn, 1)
        self.assertFalse(self.player.eliminated)
        
    def test_land_playing(self):
        """Test land playing through integration."""
        forest = Card(
            id="test12",
            name="Forest",
            types=["Land"],
            mana_cost=0,
            text="{T}: Add {G}."
        )
        
        self.player.hand.append(forest)
        
        # Play land
        success, message = self.controller.play_land(self.player, forest)
        self.assertTrue(success)
        self.assertIn("Forest", message)
        
        # Check land is on battlefield
        self.assertEqual(len(self.player.battlefield), 1)
        self.assertEqual(self.player.lands_played_this_turn, 1)
        
        # Cannot play another
        success, message = self.controller.play_land(self.player, forest)
        self.assertFalse(success)
        
    def test_mana_tapping(self):
        """Test tapping lands for mana."""
        # First, play a forest
        forest = Card(
            id="test13", 
            name="Forest",
            types=["Land"],
            mana_cost=0,
            text="{T}: Add {G}."
        )
        
        self.player.hand.append(forest)
        self.controller.play_land(self.player, forest)
        
        # Tap for mana
        forest_permanent = self.player.battlefield[0]
        success = self.controller.tap_for_mana(self.player, forest_permanent)
        self.assertTrue(success)
        
        # Check mana was added
        self.assertGreater(self.player.mana_pool.pool.get("G", 0), 0)
        
        # Check permanent is tapped
        self.assertTrue(getattr(forest_permanent, 'tapped', False))
        
    def test_spell_casting(self):
        """Test spell casting through integration."""
        bolt = Card(
            id="test14",
            name="Lightning Bolt", 
            types=["Instant"],
            mana_cost=1,
            mana_cost_str="{R}"
        )
        
        self.player.hand.append(bolt)
        self.player.mana_pool.add("R", 1)
        
        # Cast spell
        success, message = self.controller.cast_spell(self.player, bolt)
        self.assertTrue(success)
        self.assertIn("Lightning Bolt", message)
        
    def test_mana_cost_info(self):
        """Test mana cost information retrieval."""
        card = Card(
            id="test15",
            name="Test Spell",
            types=["Sorcery"],
            mana_cost=3,
            mana_cost_str="{2}{R}"
        )
        
        info = self.controller.get_mana_cost_info(card)
        
        self.assertEqual(info["cmc"], 3)
        self.assertEqual(info["cost_breakdown"], {"C": 2, "R": 1})
        self.assertEqual(info["cost_string"], "{2}{R}")


class TestComplexInteractions(unittest.TestCase):
    """Test complex card interactions."""
    
    def setUp(self):
        self.game = MockGame()
        self.controller = GameplayController(self.game)
        self.player = self.game.players[0]
        self.controller.initialize_player(self.player)
        
    def test_etb_creature_with_ability(self):
        """Test creature with ETB ability."""
        creature = Card(
            id="test16",
            name="Elvish Visionary",
            types=["Creature", "Elf", "Shaman"],
            mana_cost=2,
            mana_cost_str="{1}{G}",
            power=1,
            toughness=1,
            text="When Elvish Visionary enters the battlefield, draw a card."
        )
        
        # Add some cards to library for drawing
        for i in range(5):
            self.player.library.append(Card(
                id=f"lib_{i}",
                name=f"Library Card {i}",
                types=["Instant"],
                mana_cost=1
            ))
        
        self.player.hand.append(creature)
        self.player.mana_pool.add("G", 1)
        self.player.mana_pool.add("C", 1)
        
        initial_hand_size = len(self.player.hand)
        
        # Cast creature
        success, _ = self.controller.cast_spell(self.player, creature)
        self.assertTrue(success)
        
        # Resolve the spell by forcing stack resolution
        self.controller.stack_controller.force_resolve_stack()
        
        # Check creature is on battlefield
        self.assertEqual(len(self.player.battlefield), 1)
        
    def test_multiple_keyword_abilities(self):
        """Test creature with multiple keyword abilities."""
        dragon = Card(
            id="test17", 
            name="Lightning Dragon",
            types=["Creature", "Dragon"],
            mana_cost=6,
            mana_cost_str="{4}{R}{R}",
            power=5,
            toughness=5,
            text="Flying, Trample, Haste"
        )
        
        abilities = KeywordAbilities.parse_keywords(dragon)
        ability_texts = [ability.text for ability in abilities]
        
        self.assertIn("Flying", ability_texts)
        self.assertIn("Trample", ability_texts)
        self.assertIn("Haste", ability_texts)
        
    def test_mana_ability_vs_regular_ability(self):
        """Test difference between mana abilities and regular abilities."""
        card = Card(
            id="test18",
            name="Complex Permanent",
            types=["Artifact"],
            mana_cost=3,
            text="{T}: Add {C}. {2}, {T}: Draw a card."
        )
        
        # This would need more sophisticated parsing for multiple abilities
        # For now, test that tap ability parsing works for the first ability
        tap_ability = KeywordAbilities.parse_tap_ability(card)
        self.assertIsNotNone(tap_ability)


def run_all_tests():
    """Run all test suites."""
    test_modules = [
        TestManaCostParser,
        TestManaPool, 
        TestKeywordAbilities,
        TestTriggeredAbilities,
        TestPlayabilityChecker,
        TestStackSystem,
        TestGameplayIntegration,
        TestComplexInteractions
    ]
    
    suite = unittest.TestSuite()
    
    for test_module in test_modules:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_module)
        suite.addTests(tests)
        
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("Running MTG Card Mechanics Test Suite...")
    print("=" * 50)
    
    success = run_all_tests()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed.")
        
    print("\nTest suite complete.")
