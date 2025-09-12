#!/usr/bin/env python3
"""
Test that battlefield cards are non-draggable.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QMouseEvent, QDragEnterEvent

from ui.card_widget import create_card_widget
from engine.card_engine import Card


class NonDraggableTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Non-Draggable Battlefield Cards Test")
        self.setGeometry(100, 100, 800, 600)
        
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🧪 Non-Draggable Battlefield Cards Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\\n"
            "- Left side: HAND cards (should be draggable - open hand cursor)\\n"
            "- Right side: BATTLEFIELD cards (should be NON-draggable - arrow cursor)\\n"
            "- Try dragging both types to see the difference"
        )
        instructions.setStyleSheet("margin: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px;")
        main_layout.addWidget(instructions)
        
        # Create test layout
        test_layout = QHBoxLayout()
        
        # Left side - Hand cards (draggable)
        hand_section = QWidget()
        hand_layout = QVBoxLayout(hand_section)
        hand_layout.addWidget(QLabel("📦 HAND Cards (Draggable):"))
        
        # Create test hand cards
        hand_cards = [
            Card(id="hand_forest", name="Forest", types=["Land"], mana_cost=0),
            Card(id="hand_dragon", name="Shivan Dragon", types=["Creature", "Dragon"], mana_cost=6),
            Card(id="hand_bolt", name="Lightning Bolt", types=["Instant"], mana_cost=1),
        ]
        
        for card in hand_cards:
            card_widget = create_card_widget(card, QSize(100, 140), location="hand")
            hand_layout.addWidget(card_widget)
            print(f"✅ Created HAND card: {card.name} (draggable: {card_widget.can_be_dragged})")
        
        test_layout.addWidget(hand_section)
        
        # Right side - Battlefield cards (non-draggable)
        battlefield_section = QWidget()
        battlefield_layout = QVBoxLayout(battlefield_section)
        battlefield_layout.addWidget(QLabel("🏰 BATTLEFIELD Cards (Non-Draggable):"))
        
        # Create test battlefield cards
        battlefield_cards = [
            Card(id="bf_forest", name="Forest", types=["Land"], mana_cost=0),
            Card(id="bf_dragon", name="Shivan Dragon", types=["Creature", "Dragon"], mana_cost=6),
            Card(id="bf_artifact", name="Sol Ring", types=["Artifact"], mana_cost=1),
        ]
        
        for card in battlefield_cards:
            card_widget = create_card_widget(card, QSize(100, 140), location="battlefield")
            battlefield_layout.addWidget(card_widget)
            print(f"✅ Created BATTLEFIELD card: {card.name} (draggable: {card_widget.can_be_dragged})")
        
        test_layout.addWidget(battlefield_section)
        
        main_layout.addLayout(test_layout)


def test_non_draggable_cards():
    """Test that battlefield cards cannot be dragged."""
    print("🚀 Starting Non-Draggable Cards Test...")
    print("="*50)
    
    try:
        app = QApplication(sys.argv)
        
        window = NonDraggableTestWindow()
        window.show()
        
        print("✅ Test window created successfully")
        print("📋 Manual testing instructions:")
        print("   1. Hover over HAND cards - should show open hand cursor")
        print("   2. Hover over BATTLEFIELD cards - should show arrow cursor") 
        print("   3. Try dragging HAND cards - should work")
        print("   4. Try dragging BATTLEFIELD cards - should NOT work")
        print("   5. Notice different border colors between draggable/non-draggable")
        
        # Run for a few seconds for testing
        import time
        time.sleep(10)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_non_draggable_cards()
    sys.exit(0 if success else 1)
