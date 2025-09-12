#!/usr/bin/env python3
"""Test enhanced automatic card placement to battlefield zones."""

import sys
import os
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def test_auto_placement_system():
    """Test the enhanced auto-placement system after card drops."""
    print("🚀 Testing Enhanced Auto-Placement System...")
    print("="*50)
    
    try:
        # Import the main application components
        from engine.game_init import create_initial_game, parse_args
        from ui.theme import apply_modern_theme
        from main import MainWindow
        
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
        args = parse_args()
        args.no_log = False  # Enable logging to see debug output
        
        print("📋 Creating initial game...")
        game, ai_ids = create_initial_game(args)
        print(f"✅ Initial game created with {len(game.players)} players")
        
        # Create main window
        print("📋 Creating main window...")
        main_window = MainWindow(game, ai_ids, args)
        main_window.show()
        
        # Get the API for direct testing
        api = main_window.api
        print("✅ Main window and API created")
        
        # Initialize the game to get cards in hand
        print("🔍 Initializing game...")
        api.ensure_ai_opponent()
        api.start_game_without_roll()
        api.open_game_window()
        
        print("✅ Game initialized")
        
        # Test auto-placement with detailed logging
        print("\n📋 Testing auto-placement with enhanced debugging...")
        
        if hasattr(api.game, 'players') and api.game.players and api.game.players[0].hand:
            print(f"🔍 Player has {len(api.game.players[0].hand)} cards in hand")
            
            # Test land play
            land_cards = [card for card in api.game.players[0].hand if "Land" in getattr(card, 'types', [])]
            creature_cards = [card for card in api.game.players[0].hand if "Creature" in getattr(card, 'types', [])]
            
            print(f"🔍 Found {len(land_cards)} lands and {len(creature_cards)} creatures")
            
            # Test 1: Play a land
            if land_cards:
                test_card = land_cards[0]
                card_id = getattr(test_card, 'id', None)
                card_name = getattr(test_card, 'name', 'Unknown')
                
                print(f"\n🧪 TEST 1: Playing land '{card_name}' (ID: {card_id})")
                print(f"🔍 Current battlefield before play:")
                
                # Check current battlefield state
                if api.game.players[0].battlefield:
                    for i, perm in enumerate(api.game.players[0].battlefield):
                        card = perm.card if hasattr(perm, 'card') else perm
                        print(f"   {i+1}. {getattr(card, 'name', 'Unknown')} - {getattr(card, 'types', [])}")
                else:
                    print("   (Battlefield is empty)")
                
                try:
                    # Simulate the drop event
                    result = api.handle_card_drop_to_battlefield(card_id, "Lands")
                    print(f"🎯 Land play result: {result}")
                    
                    # Check battlefield state after play
                    print(f"🔍 Battlefield after land play:")
                    if api.game.players[0].battlefield:
                        for i, perm in enumerate(api.game.players[0].battlefield):
                            card = perm.card if hasattr(perm, 'card') else perm
                            print(f"   {i+1}. {getattr(card, 'name', 'Unknown')} - {getattr(card, 'types', [])}")
                    else:
                        print("   (Battlefield still empty)")
                        
                except Exception as e:
                    print(f"❌ Land play failed: {e}")
                    traceback.print_exc()
            
            # Add some mana for creature test
            print(f"\n🔍 Adding mana for creature test...")
            try:
                # Add mana to player's mana pool
                player = api.game.players[0]
                if not hasattr(player, 'mana_pool'):
                    from engine.mana import ManaPool
                    player.mana_pool = ManaPool()
                
                # Add some mana
                for color in ['W', 'U', 'B', 'R', 'G']:
                    player.mana_pool.add(color, 2)
                print(f"✅ Added mana to player's pool")
                
            except Exception as e:
                print(f"❌ Failed to add mana: {e}")
            
            # Test 2: Try to play a creature (if we have mana)
            if creature_cards:
                test_creature = creature_cards[0]
                card_id = getattr(test_creature, 'id', None)
                card_name = getattr(test_creature, 'name', 'Unknown')
                mana_cost = getattr(test_creature, 'mana_cost', 0)
                
                print(f"\n🧪 TEST 2: Attempting to play creature '{card_name}' (ID: {card_id}, Cost: {mana_cost})")
                
                try:
                    result = api.handle_card_drop_to_battlefield(card_id, "Creatures")
                    print(f"🎯 Creature play result: {result}")
                    
                    # Check battlefield state after creature play
                    print(f"🔍 Battlefield after creature play attempt:")
                    if api.game.players[0].battlefield:
                        for i, perm in enumerate(api.game.players[0].battlefield):
                            card = perm.card if hasattr(perm, 'card') else perm
                            print(f"   {i+1}. {getattr(card, 'name', 'Unknown')} - {getattr(card, 'types', [])}")
                    else:
                        print("   (Battlefield still empty)")
                        
                except Exception as e:
                    print(f"❌ Creature play failed: {e}")
                    traceback.print_exc()
        
        print(f"\n📋 Auto-placement tests completed")
        print(f"📋 App will run for 5 seconds to verify UI updates...")
        
        # Let app run to see final state
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(5000)  # 5 seconds
        
        # Run the application
        result = app.exec()
        print(f"🔍 Application finished with exit code: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Critical test failure: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_auto_placement_system())
