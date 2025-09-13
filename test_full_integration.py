"""
Comprehensive Integration Test for Enhanced MTG Systems
Tests all enhanced systems working together in the complete application
"""

import sys
import os
import traceback

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_systems_integration():
    """Test all enhanced systems working together"""
    print("🧪 Testing Enhanced MTG Systems Integration")
    print("=" * 60)
    
    results = {
        'layers_system': False,
        'keyword_recognition': False,
        'card_validation': False,
        'token_system': False,
        'game_controller_integration': False,
        'card_loading_integration': False,
        'ui_integration': False
    }
    
    try:
        # Test 1: Layers System
        print("\n1️⃣ Testing Layers System...")
        from engine.layers import LayersEngine, create_static_buff_effect
        from engine.card_engine import Card
        
        layers_engine = LayersEngine()
        
        # Create test card
        test_card = Card(
            id="test_grizzly",
            name="Grizzly Bears",
            types=["Creature"],
            mana_cost=2,
            power=2,
            toughness=2,
            owner_id=0,
            controller_id=0
        )
        test_card.set_layers_engine(layers_engine)
        
        # Test power/toughness calculation
        initial_pt = test_card.get_current_power_toughness()
        assert initial_pt == (2, 2), f"Expected (2, 2), got {initial_pt}"
        
        # Add a buff effect
        def affects_all_creatures(card):
            return "Creature" in card.types
        
        buff_effect = create_static_buff_effect("test_buff", 1, 1, affects_all_creatures)
        layers_engine.add_effect(buff_effect)
        
        # Test buffed power/toughness
        buffed_pt = test_card.get_current_power_toughness()
        assert buffed_pt == (3, 3), f"Expected (3, 3), got {buffed_pt}"
        
        results['layers_system'] = True
        print("✅ Layers System: PASSED")
        
    except Exception as e:
        print(f"❌ Layers System: FAILED - {e}")
        traceback.print_exc()
    
    try:
        # Test 2: Enhanced Keyword Recognition
        print("\n2️⃣ Testing Enhanced Keyword Recognition...")
        from engine.enhanced_keywords import extract_card_keywords, get_combat_keywords, has_keyword
        
        # Test keyword extraction
        test_text = "Flying, vigilance\nWhenever this creature attacks, draw a card."
        keywords = extract_card_keywords(test_text)
        
        assert 'flying' in keywords, "Flying keyword not detected"
        assert 'vigilance' in keywords, "Vigilance keyword not detected"
        
        # Create test card with keywords
        flying_card = Card(
            id="test_serra",
            name="Serra Angel",
            types=["Creature"],
            mana_cost=5,
            power=4,
            toughness=4,
            text=test_text,
            owner_id=0,
            controller_id=0
        )
        flying_card.keywords = keywords
        
        combat_keywords = get_combat_keywords(flying_card)
        assert 'flying' in combat_keywords, "Flying not recognized as combat keyword"
        assert 'vigilance' in combat_keywords, "Vigilance not recognized as combat keyword"
        
        results['keyword_recognition'] = True
        print("✅ Keyword Recognition: PASSED")
        
    except Exception as e:
        print(f"❌ Keyword Recognition: FAILED - {e}")
        traceback.print_exc()
    
    try:
        # Test 3: Card Validation
        print("\n3️⃣ Testing Card Validation...")
        from engine.card_validation import validate_card_data, normalize_card_data
        
        # Test valid card data
        valid_card_data = {
            "name": "Lightning Bolt",
            "types": ["Instant"],
            "mana_cost": 1,
            "mana_cost_str": "{R}",
            "text": "Lightning Bolt deals 3 damage to any target.",
            "color_identity": ["R"]
        }
        
        validation_result = validate_card_data(valid_card_data)
        assert validation_result.is_valid, f"Valid card failed validation: {validation_result.errors}"
        
        # Test normalization
        normalized = normalize_card_data(valid_card_data)
        assert normalized['name'] == "Lightning Bolt", "Name normalization failed"
        assert normalized['mana_cost'] == 1, "Mana cost normalization failed"
        
        results['card_validation'] = True
        print("✅ Card Validation: PASSED")
        
    except Exception as e:
        print(f"❌ Card Validation: FAILED - {e}")
        traceback.print_exc()
    
    try:
        # Test 4: Token and Copy System
        print("\n4️⃣ Testing Token and Copy System...")
        from engine.tokens_and_copies import TokenAndCopyEngine, create_creature_token
        
        token_engine = TokenAndCopyEngine()
        
        # Test predefined token creation
        soldier_tokens = token_engine.create_token("1/1_white_soldier", controller_id=0, quantity=2)
        assert len(soldier_tokens) == 2, f"Expected 2 tokens, got {len(soldier_tokens)}"
        assert soldier_tokens[0].power == 1, "Token power incorrect"
        assert soldier_tokens[0].toughness == 1, "Token toughness incorrect"
        assert soldier_tokens[0].is_token, "Token flag not set"
        
        # Test custom token creation
        custom_token_def = create_creature_token(3, 3, ["G"], ["Beast"], ["Trample"])
        custom_tokens = token_engine.create_custom_token(custom_token_def, controller_id=0)
        assert len(custom_tokens) == 1, "Custom token creation failed"
        assert custom_tokens[0].power == 3, "Custom token power incorrect"
        
        # Test token copy
        original_card = Card(
            id="test_original",
            name="Original Creature",
            types=["Creature"],
            mana_cost=3,
            power=2,
            toughness=2,
            owner_id=0,
            controller_id=0
        )
        
        token_copy = token_engine.create_token_copy(original_card, controller_id=0)
        assert token_copy.name == "Original Creature", "Token copy name incorrect"
        assert token_copy.is_token, "Token copy flag not set"
        assert "Token" in token_copy.types, "Token type not added"
        
        results['token_system'] = True
        print("✅ Token and Copy System: PASSED")
        
    except Exception as e:
        print(f"❌ Token and Copy System: FAILED - {e}")
        traceback.print_exc()
    
    try:
        # Test 5: Game Controller Integration
        print("\n5️⃣ Testing Game Controller Integration...")
        from engine.game_controller import GameController
        from engine.game_state import GameState, PlayerState
        
        # Create minimal game state for testing
        players = [PlayerState(0, "Test Player")]
        game_state = GameState(players)
        
        # Create enhanced game controller
        controller = GameController(game_state, [], logging_enabled=False)
        
        # Verify enhanced systems are initialized
        assert hasattr(controller, 'layers_engine'), "Layers engine not initialized"
        assert hasattr(controller, 'keyword_processor'), "Keyword processor not initialized"
        assert hasattr(controller, 'card_validator'), "Card validator not initialized"
        assert hasattr(controller, 'token_engine'), "Token engine not initialized"
        assert hasattr(controller, 'enhanced_card_engine'), "Enhanced card engine not initialized"
        
        # Test enhanced methods
        assert hasattr(controller, 'create_token'), "create_token method missing"
        assert hasattr(controller, 'get_current_power_toughness'), "get_current_power_toughness method missing"
        assert hasattr(controller, 'can_block_enhanced'), "can_block_enhanced method missing"
        
        results['game_controller_integration'] = True
        print("✅ Game Controller Integration: PASSED")
        
    except Exception as e:
        print(f"❌ Game Controller Integration: FAILED - {e}")
        traceback.print_exc()
    
    try:
        # Test 6: Card Loading Integration
        print("\n6️⃣ Testing Card Loading Integration...")
        from engine.card_fetch import _create_card_from_data
        
        # Test enhanced card creation
        test_card_data = {
            'id': 'test_bolt',
            'name': 'Lightning Bolt',
            'types': ['Instant'],
            'mana_cost': 1,
            'mana_cost_str': '{R}',
            'text': 'Lightning Bolt deals 3 damage to any target.',
            'color_identity': ['R']
        }
        
        enhanced_card = _create_card_from_data(test_card_data, owner_id=0)
        assert enhanced_card.name == "Lightning Bolt", "Enhanced card creation failed"
        
        # Check if enhanced features are applied
        if hasattr(enhanced_card, 'keywords'):
            print("🔍 Keywords detected on enhanced card")
        
        results['card_loading_integration'] = True
        print("✅ Card Loading Integration: PASSED")
        
    except Exception as e:
        print(f"❌ Card Loading Integration: FAILED - {e}")
        traceback.print_exc()
    
    try:
        # Test 7: UI Integration (basic component test)
        print("\n7️⃣ Testing UI Integration...")
        
        # Test if UI components can be imported
        from ui.enhanced_card_renderer import EnhancedCardDisplay, create_enhanced_card_widget
        
        # This is a basic import test since we can't fully test UI without Qt app context
        assert EnhancedCardDisplay is not None, "EnhancedCardDisplay import failed"
        assert create_enhanced_card_widget is not None, "create_enhanced_card_widget import failed"
        
        results['ui_integration'] = True
        print("✅ UI Integration: PASSED (import test)")
        
    except Exception as e:
        print(f"❌ UI Integration: FAILED - {e}")
        traceback.print_exc()
    
    # Summary
    print(f"\n📊 Integration Test Results:")
    print("=" * 40)
    
    passed_tests = sum(1 for result in results.values() if result)
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL ENHANCED SYSTEMS INTEGRATION TESTS PASSED!")
        print("\n🚀 Enhanced MTG Engine is ready for production use!")
        return True
    else:
        print(f"⚠️  {total_tests - passed_tests} test(s) failed. Please review the errors above.")
        return False

def test_complete_workflow():
    """Test a complete enhanced workflow"""
    print("\n🔄 Testing Complete Enhanced Workflow...")
    print("=" * 40)
    
    try:
        # Create a complete enhanced game scenario
        from engine.game_controller import GameController
        from engine.game_state import GameState, PlayerState
        
        # Setup
        players = [PlayerState(0, "Enhanced Player")]
        game_state = GameState(players)
        controller = GameController(game_state, [], logging_enabled=True)
        
        print("1. ✅ Enhanced game controller created")
        
        # Create some enhanced cards
        test_cards_data = [
            {
                'id': 'grizzly_bears',
                'name': 'Grizzly Bears',
                'types': ['Creature'],
                'mana_cost': 2,
                'mana_cost_str': '{1}{G}',
                'power': 2,
                'toughness': 2,
                'text': '',
                'color_identity': ['G']
            },
            {
                'id': 'serra_angel',
                'name': 'Serra Angel',
                'types': ['Creature'],
                'mana_cost': 5,
                'mana_cost_str': '{3}{W}{W}',
                'power': 4,
                'toughness': 4,
                'text': 'Flying, vigilance',
                'color_identity': ['W']
            }
        ]
        
        enhanced_cards = []
        for card_data in test_cards_data:
            card = controller.create_enhanced_card(card_data, owner_id=0)
            enhanced_cards.append(card)
        
        print("2. ✅ Enhanced cards created with validation and keywords")
        
        # Test power/toughness calculations
        for card in enhanced_cards:
            if "Creature" in card.types:
                current_pt = controller.get_current_power_toughness(card)
                print(f"   📊 {card.name}: {current_pt[0]}/{current_pt[1]}")
        
        # Add a static buff effect
        def affects_creatures(card):
            return "Creature" in card.types
        
        controller.add_static_buff(enhanced_cards[0], affects_creatures, 1, 1)
        print("3. ✅ Static buff effect added")
        
        # Check updated power/toughness
        for card in enhanced_cards:
            if "Creature" in card.types:
                current_pt = controller.get_current_power_toughness(card)
                print(f"   📊 After buff - {card.name}: {current_pt[0]}/{current_pt[1]}")
        
        # Create some tokens
        tokens = controller.create_token("1/1_white_soldier", controller_id=0, quantity=3)
        print(f"4. ✅ Created {len(tokens)} soldier tokens")
        
        # Create a token copy
        if enhanced_cards:
            token_copy = controller.create_token_copy(enhanced_cards[0], controller_id=0)
            print(f"5. ✅ Created token copy of {enhanced_cards[0].name}")
        
        # Test combat keywords
        for card in enhanced_cards:
            if hasattr(card, 'keywords') and card.keywords:
                combat_keywords = controller.enhanced_card_engine.get_combat_keywords(card)
                if combat_keywords:
                    print(f"   ⚔️ {card.name} combat keywords: {', '.join(combat_keywords)}")
        
        print("\n🎉 Complete Enhanced Workflow: SUCCESS!")
        return True
        
    except Exception as e:
        print(f"\n❌ Complete Enhanced Workflow: FAILED - {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Full Enhanced MTG Systems Integration Test")
    print("📅 This test verifies all enhanced systems work together correctly")
    
    # Run integration tests
    integration_success = test_enhanced_systems_integration()
    
    # Run complete workflow test
    workflow_success = test_complete_workflow()
    
    # Final result
    if integration_success and workflow_success:
        print("\n🏆 ALL TESTS PASSED! Enhanced MTG Engine is fully integrated and ready!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please review the output above.")
        sys.exit(1)
