"""Floating game log window for MTG Commander.

Professional floating window that can be toggled on/off and can snap/unsnap from the main game window.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTextEdit, QMainWindow, QDockWidget
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QFont, QIcon

from ui.theme import MTGTheme


class FloatingGameLogWindow(QMainWindow):
    """Floating game log window that can dock/undock from main window."""
    
    window_closed = Signal()
    docking_changed = Signal(bool)  # True if docked, False if floating
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.is_docked = False
        self.dock_widget = None
        self.setup_ui()
        self.setup_window_properties()
        
    def setup_window_properties(self):
        """Setup window properties for floating behavior."""
        self.setWindowTitle("MTG Commander - Game Log")
        self.setMinimumSize(300, 200)
        self.resize(400, 600)
        
        # Make window stay on top when floating
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowStaysOnTopHint |
            Qt.WindowTitleHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        
        # Apply theme styling
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
                border: 2px solid {MTGTheme.BORDER_DARK.name()};
            }}
        """)
        
    def setup_ui(self):
        """Setup the floating log window UI."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Game Log")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()};")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Dock/Undock button
        self.dock_button = QPushButton("Dock to Main")
        self.dock_button.setStyleSheet(f"""
            QPushButton {{
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                color: {MTGTheme.TEXT_PRIMARY.name()};
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {MTGTheme.HOVER_HIGHLIGHT.name()};
            }}
            QPushButton:pressed {{
                background: {MTGTheme.ACTIVE_HIGHLIGHT.name()};
            }}
        """)
        self.dock_button.clicked.connect(self.toggle_docking)
        header_layout.addWidget(self.dock_button)
        
        # Clear log button
        clear_button = QPushButton("Clear")
        clear_button.setStyleSheet(f"""
            QPushButton {{
                background: {MTGTheme.DANGER.name()};
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {MTGTheme.DANGER.darker().name()};
            }}
        """)
        clear_button.clicked.connect(self.clear_log)
        header_layout.addWidget(clear_button)
        
        layout.addLayout(header_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setStyleSheet(f"""
            QTextEdit {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 4px;
                color: {MTGTheme.TEXT_SECONDARY.name()};
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                background: {MTGTheme.BACKGROUND_MEDIUM.name()};
                width: 12px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {MTGTheme.HOVER_HIGHLIGHT.name()};
            }}
        """)
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)
        
        # Initialize with welcome message
        self.add_log_entry("Game log initialized", "system")
        
    def add_log_entry(self, message, entry_type="info"):
        """Add an entry to the log with proper MTG gameplay formatting."""
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%I:%M %p")  # MTG format: "6:21 PM"
        
        # Enhanced color coding based on MTG gameplay patterns
        color_map = {
            "system": MTGTheme.TEXT_DISABLED.name(),
            "info": MTGTheme.TEXT_SECONDARY.name(),
            "warning": MTGTheme.WARNING.name(),
            "error": MTGTheme.DANGER.name(),
            "success": MTGTheme.SUCCESS.name(),
            "player": MTGTheme.TEXT_PRIMARY.name(),
            "opponent": MTGTheme.HOVER_HIGHLIGHT.name(),
            "turn": MTGTheme.ACTIVE_HIGHLIGHT.name(),
            "cast": MTGTheme.MANA_BLUE.name(),
            "combat": MTGTheme.DANGER.name(),
            "ability": MTGTheme.MANA_GREEN.name(),
            "draw": MTGTheme.INFO.name(),
            "land": MTGTheme.MANA_GREEN.darker().name(),
            "commander": MTGTheme.WARNING.name()
        }
        
        color = color_map.get(entry_type, MTGTheme.TEXT_SECONDARY.name())
        
        # Format the message with proper MTG timestamp format
        formatted_message = f'<span style="color: {color};">{timestamp}: {message}</span>'
        
        # Special formatting for different action types
        if "draws a card" in message:
            formatted_message = f'<span style="color: {MTGTheme.INFO.name()};">{timestamp}: {message}</span>'
        elif "plays " in message and (" Island" in message or " Forest" in message or " Mountain" in message or " Plains" in message or " Swamp" in message):
            formatted_message = f'<span style="color: {MTGTheme.MANA_GREEN.darker().name()};">{timestamp}: {message}</span>'
        elif "casts " in message:
            formatted_message = f'<span style="color: {MTGTheme.MANA_BLUE.name()};">{timestamp}: {message}</span>'
        elif "is being attacked by" in message:
            formatted_message = f'<span style="color: {MTGTheme.DANGER.name()};">{timestamp}: {message}</span>'
        elif "Turn " in message and ":" in message:
            formatted_message = f'<span style="color: {MTGTheme.ACTIVE_HIGHLIGHT.name()}; font-weight: bold;">{timestamp}: {message}</span>'
        elif "triggered ability" in message:
            formatted_message = f'<span style="color: {MTGTheme.MANA_GREEN.name()};">{timestamp}: {message}</span>'
        elif "commander" in message.lower():
            formatted_message = f'<span style="color: {MTGTheme.WARNING.name()};">{timestamp}: {message}</span>'
        
        self.log_display.append(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def log_turn_start(self, turn_number, player_name):
        """Log the start of a new turn."""
        self.add_log_entry(f"Turn {turn_number}: {player_name}", "turn")
        
    def log_card_draw(self, player_name, count=1):
        """Log a card draw event."""
        if count == 1:
            self.add_log_entry(f"{player_name} draws a card.", "draw")
        else:
            self.add_log_entry(f"{player_name} draws {count} cards.", "draw")
            
    def log_land_play(self, player_name, land_name):
        """Log a land being played."""
        self.add_log_entry(f"{player_name} plays {land_name}.", "land")
        
    def log_spell_cast(self, player_name, spell_name):
        """Log a spell being cast."""
        self.add_log_entry(f"{player_name} casts {spell_name}.", "cast")
        
    def log_ability_trigger(self, player_name, ability_source, ability_description):
        """Log a triggered ability."""
        self.add_log_entry(f"{player_name} puts triggered ability from {ability_source} onto the stack ({ability_description}).", "ability")
        
    def log_combat_attack(self, attacker, defender, creatures):
        """Log combat attacks."""
        if isinstance(creatures, list):
            creature_list = ", ".join(creatures)
        else:
            creature_list = str(creatures)
        self.add_log_entry(f"{defender} is being attacked by {creature_list}", "combat")
        
    def log_commander_damage(self, player_name, commander_name, damage, total_damage):
        """Log commander damage."""
        self.add_log_entry(f"{player_name} has been dealt {damage} total damage by {commander_name}.", "commander")
        
    def log_life_change(self, player_name, old_life, new_life):
        """Log life total changes."""
        change = new_life - old_life
        if change > 0:
            self.add_log_entry(f"{player_name} gains {change} life. (Life: {new_life})", "success")
        else:
            self.add_log_entry(f"{player_name} loses {abs(change)} life. (Life: {new_life})", "warning")
        
    def clear_log(self):
        """Clear the log display."""
        self.log_display.clear()
        self.add_log_entry("Log cleared", "system")
        
    def toggle_docking(self):
        """Toggle between docked and floating states."""
        if self.main_window is None:
            return
            
        if self.is_docked:
            self.undock_from_main()
        else:
            self.dock_to_main()
            
    def dock_to_main(self):
        """Dock this window outside the main window (snap to edge)."""
        if self.main_window is None or self.is_docked:
            return
            
        # Position window to snap to the right edge of main window
        main_geometry = self.main_window.geometry()
        
        # Calculate position for right edge docking
        dock_x = main_geometry.right() + 5  # Small gap
        dock_y = main_geometry.top()
        dock_height = main_geometry.height()
        
        # Set fixed position and size for "docked" appearance
        self.setGeometry(dock_x, dock_y, 350, dock_height)
        
        # Remove window decorations to look more integrated
        self.setWindowFlags(
            Qt.Window | 
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        
        # Update state
        self.is_docked = True
        self.dock_button.setText("Undock")
        
        # Ensure window is visible
        self.show()
        self.raise_()
        
        self.docking_changed.emit(True)
        self.add_log_entry("Game log docked outside main window", "system")
        
    def undock_from_main(self):
        """Undock this window from the main window."""
        if self.main_window is None or not self.is_docked:
            return
            
        # Restore normal window flags and decorations
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowStaysOnTopHint |
            Qt.WindowTitleHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        
        # Restore normal size and position
        self.resize(400, 600)
        self.position_near_main_window()
        
        # Update state
        self.is_docked = False
        self.dock_button.setText("Dock to Main")
        
        # Show as floating window
        self.show()
        self.raise_()
        self.activateWindow()
        
        self.docking_changed.emit(False)
        self.add_log_entry("Game log undocked from main window", "system")
        
    def closeEvent(self, event):
        """Handle window close event."""
        self.window_closed.emit()
        event.accept()
        
    def position_near_main_window(self):
        """Position the floating window next to the main window."""
        if self.main_window is None:
            return
            
        # Get main window geometry
        main_geometry = self.main_window.geometry()
        
        # Position to the right of main window
        x = main_geometry.right() + 10
        y = main_geometry.top()
        
        # Make sure it fits on screen
        screen = self.screen()
        if screen:
            screen_geometry = screen.availableGeometry()
            if x + self.width() > screen_geometry.right():
                x = main_geometry.left() - self.width() - 10
            if y + self.height() > screen_geometry.bottom():
                y = screen_geometry.bottom() - self.height()
                
        self.move(x, y)


class FloatingGameLogManager:
    """Manager for the floating game log window."""
    
    def __init__(self, main_window=None):
        self.main_window = main_window
        self.log_window = None
        self.is_visible = False
        
    def toggle_log_window(self):
        """Toggle the game log window visibility."""
        if self.log_window is None:
            self.create_log_window()
            
        if self.is_visible:
            self.hide_log_window()
        else:
            self.show_log_window()
            
    def create_log_window(self):
        """Create the floating game log window."""
        self.log_window = FloatingGameLogWindow(self.main_window)
        self.log_window.window_closed.connect(self.on_log_window_closed)
        self.log_window.docking_changed.connect(self.on_docking_changed)
        
    def show_log_window(self):
        """Show the game log window."""
        if self.log_window is None:
            self.create_log_window()
            
        if not self.log_window.is_docked:
            self.log_window.position_near_main_window()
            self.log_window.show()
            self.log_window.raise_()
            self.log_window.activateWindow()
        else:
            # If docked, just make sure the dock is visible
            if self.log_window.dock_widget:
                self.log_window.dock_widget.show()
                
        self.is_visible = True
        
    def hide_log_window(self):
        """Hide the game log window."""
        if self.log_window is None:
            return
            
        if not self.log_window.is_docked:
            self.log_window.hide()
        else:
            # If docked, hide the dock widget
            if self.log_window.dock_widget:
                self.log_window.dock_widget.hide()
                
        self.is_visible = False
        
    def add_log_entry(self, message, entry_type="info"):
        """Add an entry to the log."""
        if self.log_window:
            self.log_window.add_log_entry(message, entry_type)
            
    def log_turn_start(self, turn_number, player_name):
        """Log the start of a new turn."""
        if self.log_window:
            self.log_window.log_turn_start(turn_number, player_name)
            
    def log_card_draw(self, player_name, count=1):
        """Log a card draw event."""
        if self.log_window:
            self.log_window.log_card_draw(player_name, count)
            
    def log_land_play(self, player_name, land_name):
        """Log a land being played."""
        if self.log_window:
            self.log_window.log_land_play(player_name, land_name)
            
    def log_spell_cast(self, player_name, spell_name):
        """Log a spell being cast."""
        if self.log_window:
            self.log_window.log_spell_cast(player_name, spell_name)
            
    def log_ability_trigger(self, player_name, ability_source, ability_description):
        """Log a triggered ability."""
        if self.log_window:
            self.log_window.log_ability_trigger(player_name, ability_source, ability_description)
            
    def log_combat_attack(self, attacker, defender, creatures):
        """Log combat attacks."""
        if self.log_window:
            self.log_window.log_combat_attack(attacker, defender, creatures)
            
    def log_commander_damage(self, player_name, commander_name, damage, total_damage):
        """Log commander damage."""
        if self.log_window:
            self.log_window.log_commander_damage(player_name, commander_name, damage, total_damage)
            
    def log_life_change(self, player_name, old_life, new_life):
        """Log life total changes."""
        if self.log_window:
            self.log_window.log_life_change(player_name, old_life, new_life)
            
    def on_log_window_closed(self):
        """Handle when log window is closed."""
        self.is_visible = False
        
    def on_docking_changed(self, is_docked):
        """Handle when log window docking state changes."""
        # Update visibility state based on docking
        if is_docked and self.log_window and self.log_window.dock_widget:
            self.is_visible = self.log_window.dock_widget.isVisible()
        elif not is_docked and self.log_window:
            self.is_visible = self.log_window.isVisible()
