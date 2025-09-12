#!/usr/bin/env python3
"""
Comprehensive test for drop operations on all zones to isolate crash causes.
This test systematically tries dropping different card types onto each zone
to identify which combinations cause crashes.
"""

import sys
import os
import tempfile
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import Qt, QMimeData, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent

# Import from existing modules
from engine.game_init import create_initial_game, parse_args
from ui.game_app_api import GameAppAPI
from ui.enhanced_battlefield import ZoneWidget, BattlefieldZone, HandZone, GraveyardZone
from main import MainWindow

def create_real_game():
    """Create a real game setup for testing."""
    try:
        # Use the actual game creation
        args = parse_args()
        args.no_log = False
        game, ai_ids = create_initial_game(args)
        
        return game, ai_ids
        
    except Exception as e:
        print(f"❌ Failed to create real game: {e}")
        return None, None

def get_test_cards_from_hand(player):
    """Get different card types from player's hand for testing."""
    if not hasattr(player, 'hand') or not player.hand:
        print(f"⚠️  Player has no cards in hand")
        return []
    
    # Get a variety of cards from hand (different types if available)
    test_cards = []
    
    # Try to find different card types
    for card in player.hand:
        if len(test_cards) >= 7:  # Limit test cards
            break
        test_cards.append(card)
    
    print(f"🔍 Found {len(test_cards)} test cards from hand")
    for i, card in enumerate(test_cards):
        card_name = getattr(card, 'name', 'Unknown')
        card_types = getattr(card, 'types', [])
        print(f"   {i+1}. {card_name} ({', '.join(card_types)})")
    
    return test_cards

def create_mock_drop_event(card):
    """Create a mock drop event for testing."""
    try:
        # Create QMimeData with card information
        mime_data = QMimeData()
        mime_data.setData("application/mtg-card", str(getattr(card, 'id', 'unknown')).encode())
        
        # Create a mock QDropEvent
        class MockDropEvent:
            def __init__(self, mime_data):
                self._mime_data = mime_data
                self._accepted = False
                
            def mimeData(self):
                return self._mime_data
                
            def acceptProposedAction(self):
                self._accepted = True
                
            def ignore(self):
                self._accepted = False
                
            def isAccepted(self):
                return self._accepted
        
        return MockDropEvent(mime_data)
        
    except Exception as e:
        print(f"❌ Failed to create mock drop event: {e}")
        return None

def test_zone_drop(zone_widget, card, zone_name):
    """Test dropping a card onto a specific zone."""
    try:
        print(f"🧪 Testing drop: {card.name} ({', '.join(card.types)}) → {zone_name}")
        
        # Create mock drop event
        drop_event = create_mock_drop_event(card)
        if not drop_event:
            return False, "Failed to create drop event"
        
        # Test the drop
        try:
            zone_widget.dropEvent(drop_event)
            success = drop_event.isAccepted()
            result = "Success" if success else "Rejected"
            print(f"   ✅ Result: {result}")
            return True, result
            
        except Exception as zone_error:
            error_msg = f"Zone drop error: {zone_error}"
            print(f"   ❌ {error_msg}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Test setup error: {e}"
        print(f"   ❌ {error_msg}")
        return False, error_msg

def run_comprehensive_zone_tests():
    """Run comprehensive tests on all zone types."""
    print("🚀 Starting comprehensive zone drop tests...")
    
    # Create test setup using real game
    game, ai_ids = create_real_game()
    if not game:
        print("❌ Failed to create test game")
        return
    
    # Create main window and API
    try:
        args = parse_args()
        main_window = MainWindow(game, ai_ids, args)
        api = main_window.api
        
        # Start basic game setup
        api.ensure_ai_opponent()
        print(f"✅ Game setup completed")
        
        # Get test cards from player's hand
        if not game.players or not game.players[0].hand:
            print("❌ No cards available for testing")
            return
            
        test_cards = get_test_cards_from_hand(game.players[0])
        if not test_cards:
            print("❌ No test cards available")
            return
        
    except Exception as e:
        print(f"❌ Failed to create game setup: {e}")
        traceback.print_exc()
        return
    
    # Create test zones
    test_zones = []
    zone_configs = [
        ("battlefield", BattlefieldZone, "Test Player"),
        ("hand", HandZone, "Test Player"), 
        ("graveyard", GraveyardZone, "Test Player"),
    ]
    
    for zone_name, zone_class, player_name in zone_configs:
        try:
            zone_widget = zone_class(player_name, api=api)
            test_zones.append((zone_name, zone_widget))
            print(f"✅ Created {zone_name} zone")
        except Exception as e:
            print(f"❌ Failed to create {zone_name} zone: {e}")
            continue
    
    # Add test cards to player hand for drop testing
    game.players[0].hand = test_cards
    
    # Run tests for each card-zone combination
    test_results = []
    total_tests = 0
    successful_tests = 0
    crashed_tests = 0
    
    print(f"\n🧪 Running {len(test_cards)} cards × {len(test_zones)} zones = {len(test_cards) * len(test_zones)} tests...")
    
    for card in test_cards:
        for zone_name, zone_widget in test_zones:
            total_tests += 1
            
            try:
                success, result = test_zone_drop(zone_widget, card, zone_name)
                if success:
                    successful_tests += 1
                test_results.append({
                    'card_name': card.name,
                    'card_types': ', '.join(card.types),
                    'zone_name': zone_name,
                    'success': success,
                    'result': result
                })
            except Exception as critical_error:
                crashed_tests += 1
                error_msg = f"CRITICAL ERROR: {critical_error}"
                print(f"💥 CRASH during {card.name} → {zone_name}: {error_msg}")
                traceback.print_exc()
                test_results.append({
                    'card_name': card.name,
                    'card_types': ', '.join(card.types),
                    'zone_name': zone_name,
                    'success': False,
                    'result': error_msg
                })
    
    # Print summary
    print(f"\n📊 TEST SUMMARY")
    print(f"═══════════════")
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests - crashed_tests}")
    print(f"Crashed: {crashed_tests}")
    
    # Print detailed results
    print(f"\n📋 DETAILED RESULTS")
    print(f"═══════════════════")
    
    for result in test_results:
        status_icon = "✅" if result['success'] else "❌"
        print(f"{status_icon} {result['card_name']} ({result['card_types']}) → {result['zone_name']}: {result['result']}")
    
    # Identify problematic combinations
    crashes = [r for r in test_results if "CRITICAL ERROR" in r.get('result', '')]
    if crashes:
        print(f"\n🔥 CRASH-CAUSING COMBINATIONS:")
        print(f"════════════════════════════")
        for crash in crashes:
            print(f"💥 {crash['card_name']} → {crash['zone_name']}: {crash['result']}")
    
    print(f"\n🏁 Zone drop testing completed!")
    
    return test_results

if __name__ == "__main__":
    # Create Qt application for testing
    app = QApplication(sys.argv)
    
    try:
        # Run the comprehensive tests
        test_results = run_comprehensive_zone_tests()
        
        print(f"\n🎯 Test completed. Check output above for crash-causing combinations.")
        
    except Exception as e:
        print(f"❌ Test framework error: {e}")
        traceback.print_exc()
    
    # Don't start event loop, just exit
    sys.exit(0)
