#!/usr/bin/env python3
"""Debug test for drag-and-drop functionality."""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QLabel, QFrame
)
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent

# Import our components
from ui.card_widget import InteractiveCardWidget
from ui.enhanced_game_board import BattlefieldZone
from engine.card_engine import Card


class MockAPI:
    """Mock API for testing."""
    def __init__(self):
        pass
    
    def handle_card_drop_to_battlefield(self, card_data, zone_name):
        print(f"✅ DROP SUCCESSFUL: Card {card_data} dropped on {zone_name}")
    
    def handle_card_drop_to_hand(self, card_data):
        print(f"✅ DROP SUCCESSFUL: Card {card_data} returned to hand")


class DebugBattlefieldZone(BattlefieldZone):
    """Debug version of battlefield zone with extra logging."""
    
    def __init__(self, zone_name, is_opponent=False):
        super().__init__(zone_name, is_opponent)
        self.setAcceptDrops(True)
        print(f"🔧 Created battlefield zone: {zone_name} (opponent: {is_opponent})")
    
    def dragEnterEvent(self, event):
        print(f"🔍 DRAG ENTER: Zone '{self.zone_name}'")
        print(f"   - Has MTG card format: {event.mimeData().hasFormat('application/mtg-card')}")
        print(f"   - Is opponent: {self.is_opponent}")
        print(f"   - Available formats: {[fmt for fmt in event.mimeData().formats()]}")
        super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        print(f"🔍 DRAG MOVE: Zone '{self.zone_name}'")
        super().dragMoveEvent(event)
    
    def dragLeaveEvent(self, event):
        print(f"🔍 DRAG LEAVE: Zone '{self.zone_name}'")
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        print(f"🔍 DROP EVENT: Zone '{self.zone_name}'")
        print(f"   - Has MTG card format: {event.mimeData().hasFormat('application/mtg-card')}")
        try:
            card_data = event.mimeData().data("application/mtg-card").data().decode()
            print(f"   - Card data: {card_data}")
        except Exception as e:
            print(f"   - Error reading card data: {e}")
        super().dropEvent(event)


class DebugCardWidget(InteractiveCardWidget):
    """Debug version of card widget with extra logging."""
    
    def _start_drag(self, event):
        print(f"🔍 STARTING DRAG: Card '{self.card.name}'")
        print(f"   - Card ID: {getattr(self.card, 'id', 'NO_ID')}")
        print(f"   - Card types: {getattr(self.card, 'types', [])}")
        super()._start_drag(event)


class DragDropTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drag & Drop Debug Test")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create mock API
        self.api = MockAPI()
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🧪 Drag & Drop Debug Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Try dragging the test cards to the battlefield zones\n"
            "2. Watch the console output for debug information\n"
            "3. Valid drops should show success messages"
        )
        instructions.setStyleSheet("margin: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px;")
        main_layout.addWidget(instructions)
        
        # Create test layout
        test_layout = QHBoxLayout()
        
        # Left side - Cards to drag
        cards_section = QWidget()
        cards_layout = QVBoxLayout(cards_section)
        cards_layout.addWidget(QLabel("📦 Cards (Drag these):"))
        
        # Create test cards
        test_cards = [
            Card(id="dragon_1", name="Test Dragon", types=["Creature", "Dragon"], mana_cost=5),
            Card(id="forest_1", name="Forest", types=["Land"], mana_cost=0),
            Card(id="sword_1", name="Magic Sword", types=["Artifact", "Equipment"], mana_cost=3),
        ]
        
        for card in test_cards:
            card_widget = DebugCardWidget(card, QSize(100, 140), api=self.api)
            cards_layout.addWidget(card_widget)
        
        test_layout.addWidget(cards_section)
        
        # Right side - Drop zones
        zones_section = QWidget()
        zones_layout = QVBoxLayout(zones_section)
        zones_layout.addWidget(QLabel("🎯 Drop Zones:"))
        
        # Create battlefield zones
        creature_zone = DebugBattlefieldZone("Creatures", False)
        creature_zone.api = self.api
        creature_zone.setFixedSize(300, 150)
        creature_zone.setStyleSheet("background: #e8f5e8; border: 2px dashed #4CAF50; border-radius: 8px;")
        zones_layout.addWidget(QLabel("Creature Battlefield:"))
        zones_layout.addWidget(creature_zone)
        
        lands_zone = DebugBattlefieldZone("Lands", False)
        lands_zone.api = self.api
        lands_zone.setFixedSize(300, 150)
        lands_zone.setStyleSheet("background: #fff3e0; border: 2px dashed #FF9800; border-radius: 8px;")
        zones_layout.addWidget(QLabel("Lands Battlefield:"))
        zones_layout.addWidget(lands_zone)
        
        test_layout.addWidget(zones_section)
        
        main_layout.addLayout(test_layout)


def test_drag_drop():
    """Test drag and drop functionality."""
    print("🚀 Starting Drag & Drop Debug Test...")
    print("="*50)
    
    try:
        app = QApplication(sys.argv)
        
        window = DragDropTestWindow()
        window.show()
        
        print("✅ Test window created successfully")
        print("📋 Ready for manual testing:")
        print("   1. Try dragging cards to the battlefield zones")
        print("   2. Watch console output for debug information")
        print("   3. Look for 'DROP SUCCESSFUL' messages")
        
        app.exec()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_drag_drop()
    sys.exit(0 if success else 1)
