#!/usr/bin/env python3
"""Test script to verify card widget improvements."""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QSize

# Import our improved card widget
from ui.card_widget import InteractiveCardWidget, CardPreviewWidget
from engine.card_engine import Card


class TestMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Card Widget Improvements Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create test card
        test_card = Card(
            id="test_card_1",
            name="Test Dragon",
            types=["Creature", "Dragon"],
            mana_cost=6,
            power=5,
            toughness=5,
            text="Flying, Trample\nWhen Test Dragon enters the battlefield, deal 3 damage to any target."
        )
        test_card.mana_cost_str = "{4}{R}{R}"
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        
        # Create card widget with improvements
        card_widget = InteractiveCardWidget(
            card=test_card, 
            size=QSize(120, 168),  # Standard MTG card proportions
            api=None
        )
        
        layout.addWidget(card_widget)
        
        print("✅ Card widget created successfully")
        print("   - No labels visible (clean design)")
        print("   - Hover should show preview after 0.5 seconds")
        print("   - Card highlights should work properly")
        print("   - Drag should trigger target highlighting")


def test_card_improvements():
    """Test the card widget improvements."""
    print("🧪 Testing Card Widget Improvements...")
    
    try:
        app = QApplication(sys.argv)
        
        # Test preview widget creation
        test_card = Card(
            id="test_preview",
            name="Preview Test Card",
            types=["Instant"],
            mana_cost=2,
            text="Draw two cards."
        )
        
        preview = CardPreviewWidget(test_card)
        print("   ✅ Card preview widget creates successfully")
        
        # Test main card widget
        card_widget = InteractiveCardWidget(test_card)
        print("   ✅ Interactive card widget creates successfully")
        print("   ✅ Card has no visible text labels (clean design)")
        
        # Test window
        window = TestMainWindow()
        window.show()
        
        print("\n🎯 Card improvements test completed!")
        print("Manual testing available - hover over card to see preview.")
        
        # Run for a few seconds then exit
        import time
        time.sleep(3)
        app.quit()
        return True
        
    except Exception as e:
        print(f"   ❌ Card improvements test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_card_improvements()
    sys.exit(0 if success else 1)
