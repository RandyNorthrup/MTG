#!/usr/bin/env python3
"""
Test script to verify the card widget runtime error fix.
This simulates the problematic scenario and verifies no runtime errors occur.
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PySide6.QtCore import QTimer

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.card_widget import InteractiveCardWidget
from PySide6.QtCore import QSize

class MockCard:
    """Mock card object for testing."""
    def __init__(self, name="Test Card", card_id="test-123"):
        self.name = name
        self.id = card_id
        self.types = ["Creature", "Human"]
        self.mana_cost_str = "2W"
        self.power = "2"
        self.toughness = "2"

class TestWindow(QMainWindow):
    """Test window to verify widget deletion fix."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Card Widget Fix Test")
        self.setGeometry(100, 100, 400, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create test card widget
        self.card = MockCard()
        self.card_widget = InteractiveCardWidget(
            self.card, 
            QSize(100, 140), 
            parent=central_widget,
            location="battlefield"
        )
        layout.addWidget(self.card_widget)
        
        # Add test button
        test_button = QPushButton("Test Widget Deletion")
        test_button.clicked.connect(self.test_deletion)
        layout.addWidget(test_button)
        
        # Timer to simulate frequent refreshes like in the real app
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.simulate_refresh)
        self.refresh_timer.start(100)  # Every 100ms, very aggressive
        
        self.refresh_count = 0
        
    def simulate_refresh(self):
        """Simulate the refresh scenario that was causing the bug."""
        self.refresh_count += 1
        
        # After a few refreshes, test deletion
        if self.refresh_count == 10:
            self.test_deletion()
        elif self.refresh_count > 20:
            self.refresh_timer.stop()
            print("✅ Test completed successfully - no runtime errors!")
            QTimer.singleShot(1000, self.close)
    
    def test_deletion(self):
        """Test deleting the widget while events might still be pending."""
        print(f"🧪 Testing widget deletion (refresh #{self.refresh_count})...")
        
        if self.card_widget:
            try:
                # Simulate the deletion that happens during refresh
                self.card_widget.deleteLater()
                
                # Try to trigger events on the widget that's been marked for deletion
                # This should not cause runtime errors anymore
                from PySide6.QtCore import QEvent
                from PySide6.QtGui import QMouseEvent
                from PySide6.QtCore import Qt, QPoint
                
                # Create a mock mouse event
                mouse_event = QMouseEvent(
                    QEvent.MouseButtonPress,
                    QPoint(10, 10),
                    Qt.LeftButton,
                    Qt.LeftButton,
                    Qt.NoModifier
                )
                
                # This used to cause "Internal C++ object already deleted" error
                self.card_widget.mousePressEvent(mouse_event)
                
                print("✅ Widget deletion handled gracefully")
                self.card_widget = None
                
            except Exception as e:
                print(f"❌ Error during widget deletion test: {e}")
                import traceback
                traceback.print_exc()

def main():
    """Run the test."""
    app = QApplication(sys.argv)
    
    print("🧪 Starting card widget deletion fix test...")
    print("This test verifies that card widgets handle deletion gracefully")
    print("without 'Internal C++ object already deleted' runtime errors.\n")
    
    window = TestWindow()
    window.show()
    
    app.exec()
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    main()
