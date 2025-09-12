"""Enhanced game board interface for MTG Commander.

Professional game board matching Magic: The Gathering interfaces
with proper battlefield zones, life counters, phase indicators, and stack visualization.
"""

import os
import math
from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QProgressBar, QScrollArea,
    QSplitter, QGroupBox, QTextEdit, QSpinBox, QMainWindow, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QRect, QPoint
from PySide6.QtGui import (
    QPixmap, QPainter, QBrush, QColor, QPen, QFont, 
    QLinearGradient, QRadialGradient, QPainterPath, QPolygon
)

from ui.theme import (
    MTGTheme, PRIMARY_BUTTON_STYLE, SUCCESS_BUTTON_STYLE, 
    DANGER_BUTTON_STYLE, BUTTON_STYLE, PLAYER_PANEL_STYLE
)
from ui.floating_game_log import FloatingGameLogManager
from ui.player_preferences import get_player_preferences

class LifeCounter(QWidget):
    """Professional life counter widget with avatar support."""
    
    life_changed = Signal(int, int)  # player_id, new_life
    
    def __init__(self, player_id=0, initial_life=40, player_name="Player", avatar_path=None, parent=None):
        super().__init__(parent)
        self.player_id = player_id
        self.current_life = initial_life
        self.player_name = player_name
        self.avatar_path = avatar_path or "data/avatars/white_planeswalker.png"  # Default avatar
        self.setFixedSize(180, 200)  # Taller to give more space for vertical elements
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the life counter UI with avatar."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)  # Consistent margins
        layout.setSpacing(8)  # Better spacing between elements
        layout.setAlignment(Qt.AlignCenter)  # Center all content
        
        # Avatar display - improved with square/rounded rectangle styling
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(64, 64)  # Optimal size for the space
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 8px;  /* Rounded rectangle, not circle */
                background: {MTGTheme.BACKGROUND_MEDIUM.name()};
            }}
        """)
        
        # Load and display avatar
        self.update_avatar()
        
        # Center the avatar with better alignment
        layout.addWidget(self.avatar_label, 0, Qt.AlignCenter)
        
        # Player name with better formatting
        self.name_label = QLabel(self.player_name)
        self.name_label.setFont(QFont("Arial", 11, QFont.Bold))  # Smaller font for better fit
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: {MTGTheme.TEXT_PRIMARY.name()};
                background: transparent;
                padding: 1px 4px;
                border-radius: 3px;
            }}
        """)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFixedHeight(20)  # Fixed height to control spacing
        layout.addWidget(self.name_label)
        
        # Life display with improved styling
        self.life_display = QLabel(str(self.current_life))
        self.life_display.setFont(QFont("Arial", 24, QFont.Bold))  # Slightly smaller for better fit
        self.life_display.setStyleSheet(f"""
            QLabel {{
                color: {MTGTheme.TEXT_PRIMARY.name()};
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 2px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 8px;
                padding: 6px 10px;
                margin: 1px;
            }}
        """)
        self.life_display.setAlignment(Qt.AlignCenter)
        self.life_display.setFixedHeight(45)  # Slightly smaller for better spacing
        layout.addWidget(self.life_display)
        
        # Info label with subtle styling
        self.info_label = QLabel("Life Total")
        self.info_label.setFont(QFont("Arial", 9))
        self.info_label.setStyleSheet(f"""
            QLabel {{
                color: {MTGTheme.TEXT_DISABLED.name()};
                background: transparent;
                padding: 2px;
            }}
        """)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
    def update_avatar(self):
        """Update the avatar display with square/rounded rectangle format."""
        try:
            import os
            if os.path.exists(self.avatar_path):
                pixmap = QPixmap(self.avatar_path)
                if not pixmap.isNull():
                    # Scale to fit the label with proper aspect ratio
                    size = 60  # Slightly smaller than label to fit border
                    scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.avatar_label.setPixmap(scaled_pixmap)
                else:
                    self.avatar_label.setText("AVT")
            else:
                self.avatar_label.setText("AVT")
        except Exception as e:
            self.avatar_label.setText("AVT")
            print(f"Error loading avatar {self.avatar_path}: {e}")
            
    def set_avatar(self, avatar_path):
        """Set a new avatar for this life counter."""
        self.avatar_path = avatar_path
        self.update_avatar()
        
    def update_life_from_game(self, new_life):
        """Update life display from game state (read-only)."""
        if new_life != self.current_life:
            self.current_life = new_life
            self.life_display.setText(str(self.current_life))
            self.update_display_color()
            
    def set_life(self, life):
        """Set life to a specific value."""
        self.current_life = max(0, life)
        self.life_display.setText(str(self.current_life))
        self.update_display_color()
        
    def update_display_color(self):
        """Update display color based on life total."""
        if self.current_life <= 5:
            color = MTGTheme.DANGER
            border_color = MTGTheme.DANGER
        elif self.current_life <= 10:
            color = MTGTheme.WARNING
            border_color = MTGTheme.WARNING
        else:
            color = MTGTheme.TEXT_PRIMARY
            border_color = MTGTheme.BORDER_LIGHT
            
        self.life_display.setStyleSheet(f"""
            QLabel {{
                color: {color.name()};
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 2px solid {border_color.name()};
                border-radius: 10px;
                padding: 8px 12px;
                margin: 2px;
                font-size: 28px;
                font-weight: bold;
            }}
        """)

class IntegratedPhaseBar(QWidget):
    """Integrated phase bar with turn indicator on the left and phase indicators across."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_phase = "untap"
        self.current_step = ""
        self.active_player = "Player 1"
        self.turn_number = 1
        self.mana_pool = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0, 'C': 0}
        self.setFixedHeight(50)  # Match phase bar height
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the integrated phase bar UI."""
        self.setStyleSheet("background: transparent;")
        
    def paintEvent(self, event):
        """Custom paint for integrated phase bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Mana pool area (left side)
        mana_width = 150
        mana_rect = QRect(8, 8, mana_width, self.height() - 16)
        
        # Draw mana pool background
        painter.setBrush(QBrush(MTGTheme.BACKGROUND_DARK))
        painter.setPen(QPen(MTGTheme.BORDER_LIGHT, 2))
        painter.drawRoundedRect(mana_rect, 6, 6)
        
        # Draw mana symbols
        mana_colors = ['W', 'U', 'B', 'R', 'G', 'C']
        color_map = {
            'W': MTGTheme.MANA_WHITE,
            'U': MTGTheme.MANA_BLUE,
            'B': MTGTheme.MANA_BLACK,
            'R': MTGTheme.MANA_RED,
            'G': MTGTheme.MANA_GREEN,
            'C': MTGTheme.MANA_COLORLESS
        }
        
        symbol_width = 20
        start_x = mana_rect.left() + 8
        for i, color in enumerate(mana_colors):
            symbol_rect = QRect(start_x + (i * 22), mana_rect.center().y() - 10, symbol_width, 20)
            
            # Draw mana symbol background
            bg_color = color_map.get(color, MTGTheme.BACKGROUND_MEDIUM)
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(MTGTheme.BORDER_DARK, 1))
            painter.drawEllipse(symbol_rect)
            
            # Draw mana amount
            text_color = MTGTheme.BACKGROUND_DARK if color != 'B' else MTGTheme.TEXT_PRIMARY
            painter.setPen(QPen(text_color))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.drawText(symbol_rect, Qt.AlignCenter, str(self.mana_pool.get(color, 0)))
        
        # Turn indicator area (next to mana pool)
        turn_width = 120
        turn_rect = QRect(mana_width + 16, 8, turn_width, self.height() - 16)
        
        # Draw turn indicator background
        painter.setBrush(QBrush(MTGTheme.BACKGROUND_DARK))
        painter.setPen(QPen(MTGTheme.BORDER_LIGHT, 2))
        painter.drawRoundedRect(turn_rect, 6, 6)
        
        # Draw turn text
        painter.setPen(QPen(MTGTheme.TEXT_PRIMARY))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(turn_rect, Qt.AlignCenter, 
                        f"{self.active_player}\nTurn {self.turn_number}")
        
        # Phase indicators (right side)
        phases = [
            ("Untap", "untap"),
            ("Upkeep", "upkeep"), 
            ("Draw", "draw"),
            ("Main", "main1"),
            ("Combat", "combat"),
            ("Main", "main2"),
            ("End", "end"),
            ("Cleanup", "cleanup")
        ]
        
        # Calculate available width for phases (after mana and turn areas)
        phase_start_x = mana_width + turn_width + 24  # 16 + 8 spacing
        available_width = self.width() - phase_start_x - 8
        phase_width = available_width // len(phases)
        
        for i, (display_name, phase_id) in enumerate(phases):
            x = phase_start_x + (i * phase_width)
            phase_rect = QRect(x, 8, phase_width - 2, self.height() - 16)
            
            # Highlight current phase
            is_current = (phase_id == self.current_phase or 
                         (phase_id == "main1" and self.current_phase in ["precombat_main", "main1"]) or
                         (phase_id == "main2" and self.current_phase in ["postcombat_main", "main2"]))
            
            if is_current:
                painter.setBrush(QBrush(MTGTheme.ACTIVE_HIGHLIGHT))
                painter.setPen(QPen(MTGTheme.HOVER_HIGHLIGHT, 2))
            else:
                painter.setBrush(QBrush(MTGTheme.BACKGROUND_MEDIUM))
                painter.setPen(QPen(MTGTheme.BORDER_DARK, 1))
                
            painter.drawRoundedRect(phase_rect, 4, 4)
            
            # Draw phase name
            painter.setPen(QPen(MTGTheme.TEXT_PRIMARY if is_current else MTGTheme.TEXT_SECONDARY))
            painter.setFont(QFont("Arial", 9, QFont.Bold if is_current else QFont.Normal))
            painter.drawText(phase_rect, Qt.AlignCenter, display_name)
                        
    def set_phase(self, phase, step="", active_player="Player 1", turn_number=1, mana_pool=None):
        """Update the current phase, turn, and mana information."""
        self.current_phase = phase
        self.current_step = step
        self.active_player = active_player
        self.turn_number = turn_number
        if mana_pool:
            self.mana_pool = mana_pool
        self.update()

class ManaPoolWidget(QWidget):
    """Mana pool display widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mana_pool = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0, 'C': 0}
        self.setFixedSize(180, 60)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup mana pool UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Mana symbols
        self.mana_labels = {}
        for color in ['W', 'U', 'B', 'R', 'G', 'C']:
            mana_widget = QWidget()
            mana_widget.setFixedSize(25, 25)
            
            # Color mapping
            color_map = {
                'W': MTGTheme.MANA_WHITE,
                'U': MTGTheme.MANA_BLUE, 
                'B': MTGTheme.MANA_BLACK,
                'R': MTGTheme.MANA_RED,
                'G': MTGTheme.MANA_GREEN,
                'C': MTGTheme.MANA_COLORLESS
            }
            
            bg_color = color_map.get(color, MTGTheme.BACKGROUND_MEDIUM)
            text_color = MTGTheme.BACKGROUND_DARK if color != 'B' else MTGTheme.TEXT_PRIMARY
            
            mana_widget.setStyleSheet(f"""
                QWidget {{
                    background: {bg_color.name()};
                    border: 1px solid {MTGTheme.BORDER_DARK.name()};
                    border-radius: 12px;
                }}
            """)
            
            # Add label
            label = QLabel("0")
            label.setFont(QFont("Arial", 10, QFont.Bold))
            label.setStyleSheet(f"color: {text_color.name()}; background: transparent;")
            label.setAlignment(Qt.AlignCenter)
            
            label_layout = QVBoxLayout(mana_widget)
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.addWidget(label)
            
            self.mana_labels[color] = label
            layout.addWidget(mana_widget)
            
    def update_mana_pool(self, mana_pool):
        """Update the mana pool display."""
        self.mana_pool = mana_pool
        for color, amount in mana_pool.items():
            if color in self.mana_labels:
                self.mana_labels[color].setText(str(amount))

class StackWidget(QWidget):
    """Stack visualization widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stack_items = []
        self.setMinimumSize(200, 100)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup stack widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Title
        title = QLabel("Stack")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()};")
        layout.addWidget(title)
        
        # Stack area
        self.stack_area = QScrollArea()
        self.stack_area.setStyleSheet(f"""
            QScrollArea {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 6px;
            }}
        """)
        
        self.stack_container = QWidget()
        self.stack_layout = QVBoxLayout(self.stack_container)
        self.stack_layout.setContentsMargins(4, 4, 4, 4)
        
        self.stack_area.setWidget(self.stack_container)
        layout.addWidget(self.stack_area)
        
        # Stack info - no controls needed here as they're handled by main UI
        info_layout = QHBoxLayout()
        info_label = QLabel("Stack resolves from top to bottom")
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet(f"color: {MTGTheme.TEXT_DISABLED.name()};")
        info_layout.addWidget(info_label)
        layout.addLayout(info_layout)
        
    def add_to_stack(self, spell_name, controller="Player"):
        """Add a spell to the stack."""
        self.stack_items.append({'name': spell_name, 'controller': controller})
        self.refresh_display()
        
    def resolve_top(self):
        """Resolve the top item of the stack."""
        if self.stack_items:
            self.stack_items.pop()
            self.refresh_display()
            
    def clear_stack(self):
        """Clear the entire stack."""
        self.stack_items.clear()
        self.refresh_display()
        
    def refresh_display(self):
        """Refresh the stack display."""
        # Clear existing items
        for i in reversed(range(self.stack_layout.count())):
            item = self.stack_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
                
        if not self.stack_items:
            return
            
        # Add stack items (top to bottom)
        for i, item in enumerate(reversed(self.stack_items)):
            item_widget = QFrame()
            item_widget.setStyleSheet(f"""
                QFrame {{
                    background: {MTGTheme.BACKGROUND_LIGHT.name()};
                    border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-radius: 4px;
                    padding: 4px;
                    margin: 2px;
                }}
            """)
            
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(4, 4, 4, 4)
            
            name_label = QLabel(item['name'])
            name_label.setFont(QFont("Arial", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()};")
            item_layout.addWidget(name_label)
            
            controller_label = QLabel(f"Controlled by {item['controller']}")
            controller_label.setFont(QFont("Arial", 8))
            controller_label.setStyleSheet(f"color: {MTGTheme.TEXT_SECONDARY.name()};")
            item_layout.addWidget(controller_label)
            
            if i == 0:  # Top of stack
                item_widget.setStyleSheet(f"""
                    QFrame {{
                        background: {MTGTheme.HOVER_HIGHLIGHT.name()};
                        border: 2px solid {MTGTheme.ACTIVE_HIGHLIGHT.name()};
                        border-radius: 4px;
                        padding: 4px;
                        margin: 2px;
                    }}
                """)
                
            self.stack_layout.addWidget(item_widget)

class BattlefieldZone(QWidget):
    """Enhanced battlefield zone for cards."""
    
    card_clicked = Signal(object)
    card_right_clicked = Signal(object)
    
    def __init__(self, zone_name="Battlefield", is_opponent=False, parent=None):
        super().__init__(parent)
        self.zone_name = zone_name
        self.is_opponent = is_opponent
        self.cards = []
        self.selected_cards = set()
        self.setMinimumHeight(50)  # Much smaller minimum height
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Make completely transparent by default
        self.setStyleSheet("BattlefieldZone { background: transparent; border: none; margin: 0px; padding: 0px; }")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup battlefield zone UI with no borders or scroll areas."""
        # Make the widget completely transparent
        self.setStyleSheet("BattlefieldZone { background: transparent; border: none; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Cards container - direct layout, no scroll area
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("QWidget { background: transparent; border: none; }")
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(4)  # Card spacing
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Make cards container expand to fit content
        self.cards_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout.addWidget(self.cards_container)
        
    def add_card(self, card):
        """Add a card to the battlefield zone."""
        self.cards.append(card)
        self.refresh_display()
        
    def remove_card(self, card):
        """Remove a card from the battlefield zone."""
        if card in self.cards:
            self.cards.remove(card)
            self.refresh_display()
            
    def refresh_display(self):
        """Refresh the battlefield display."""
        # Clear existing widgets safely
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                try:
                    # Disconnect all signals to prevent orphaned connections
                    if hasattr(widget, 'card_clicked'):
                        widget.card_clicked.disconnect()
                    if hasattr(widget, 'card_right_clicked'):
                        widget.card_right_clicked.disconnect()
                    if hasattr(widget, 'card_hovered'):
                        widget.card_hovered.disconnect()
                    if hasattr(widget, 'card_drag_started'):
                        widget.card_drag_started.disconnect()
                except Exception:
                    # Ignore disconnect errors - they're not critical
                    pass
                
                # Remove from layout immediately
                self.cards_layout.removeWidget(widget)
                # Mark for deletion
                widget.deleteLater()
                
        if not self.cards:
            return
            
        # Add cards to grid - dynamic layout based on available space
        if not self.cards:
            return
            
        # Calculate optimal grid layout
        card_count = len(self.cards)
        container_width = self.cards_container.width() if self.cards_container.width() > 0 else 400
        card_width = 90 + 4  # Card width + spacing
        cols = max(1, container_width // card_width)
        
        for i, card in enumerate(self.cards):
            row = i // cols
            col = i % cols
            
            card_widget = self.create_card_widget(card)
            self.cards_layout.addWidget(card_widget, row, col)
            
    def create_card_widget(self, card):
        """Create a modern interactive card widget."""
        from ui.card_widget import create_card_widget
        
        # Get API from parent if available
        api = getattr(self, 'api', None) or getattr(self.parent(), 'api', None)
        
        # Battlefield cards cannot be dragged back to hand
        widget = create_card_widget(card, QSize(90, 120), api=api, location="battlefield")
        
        # Connect signals to board handlers
        widget.card_clicked.connect(self.card_clicked.emit)
        widget.card_right_clicked.connect(lambda c, pos: self.card_right_clicked.emit(c))
        
        return widget
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasFormat("application/mtg-card"):
            # Only accept drops if this is not an opponent zone or if allowed
            if not self.is_opponent:
                event.acceptProposedAction()
                # Add visual feedback
                self.setStyleSheet("BattlefieldZone { background: rgba(76, 175, 80, 0.2); border: 2px solid #4CAF50; border-radius: 8px; }")
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasFormat("application/mtg-card") and not self.is_opponent:
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Remove visual feedback
        self.setStyleSheet("BattlefieldZone { background: transparent; border: none; margin: 0px; padding: 0px; }")
    
    def dropEvent(self, event):
        """Handle drop event with comprehensive error handling and auto-placement."""
        try:
            if not event.mimeData().hasFormat("application/mtg-card") or self.is_opponent:
                event.ignore()
                return
            
            # Get card data safely
            try:
                card_data = event.mimeData().data("application/mtg-card").data().decode()
                print(f"🔍 DROP: Extracting card data: {card_data}")
            except Exception as e:
                print(f"❌ DROP: Failed to extract card data: {e}")
                event.ignore()
                return
            
            # Handle the card drop through API
            try:
                if self.api and hasattr(self.api, 'handle_card_drop_to_battlefield'):
                    print(f"🔍 DROP: Processing card drop via API (auto-placement)...")
                    # Let the API automatically determine correct placement - don't specify zone
                    result = self.api.handle_card_drop_to_battlefield(card_data)
                    
                    if result:
                        print(f"✅ Card {card_data} played successfully (auto-placed in correct zone)")
                        
                        # Schedule refresh for card placement
                        try:
                            print(f"🔄 AUTO-REFRESH: Scheduling refresh after card placement...")
                            
                            # Find the game board parent to schedule refresh
                            parent = self.parent()
                            while parent and not hasattr(parent, 'schedule_refresh'):
                                parent = parent.parent()
                            
                            if parent and hasattr(parent, 'schedule_refresh'):
                                parent.schedule_refresh("card_played")
                                print(f"✅ AUTO-REFRESH: Refresh scheduled")
                            elif self.api and hasattr(self.api, '_force_immediate_ui_refresh'):
                                # Fallback to API refresh with delay
                                from PySide6.QtCore import QTimer
                                QTimer.singleShot(100, self.api._force_immediate_ui_refresh)
                                print(f"✅ AUTO-REFRESH: API refresh scheduled")
                                
                        except Exception as refresh_error:
                            print(f"❌ AUTO-REFRESH: Failed to schedule refresh: {refresh_error}")
                            # Continue anyway - the card was played successfully
                        
                        event.acceptProposedAction()
                    else:
                        print(f"❌ Could not play {card_data}")
                        event.ignore()
                else:
                    print(f"⚠️  Card dropped on {self.zone_name}: {card_data} (no API available)")
                    event.acceptProposedAction()
                    
            except Exception as e:
                print(f"❌ DROP ERROR: {e}")
                import traceback
                traceback.print_exc()
                event.ignore()
                
        except Exception as e:
            print(f"❌ DROP CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            event.ignore()
        finally:
            # Always remove visual feedback after drop
            try:
                self.setStyleSheet("BattlefieldZone { background: transparent; border: none; margin: 0px; padding: 0px; }")
            except Exception:
                pass

class CommanderZone(QWidget):
    """Specialized zone for displaying commanders with proper sizing."""
    
    card_clicked = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.commander = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup commander zone UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignCenter)
        
        # Commander card container
        self.card_container = QWidget()
        self.card_container.setFixedSize(100, 140)
        layout.addWidget(self.card_container, 0, Qt.AlignCenter)
        
    def set_commander(self, commander):
        """Set the commander card."""
        self.commander = commander
        self.refresh_display()
        
    def refresh_display(self):
        """Refresh the commander display."""
        # Clear existing widgets safely
        if self.card_container.layout():
            layout = self.card_container.layout()
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    layout.removeWidget(widget)
                    widget.deleteLater()
        else:
            # Create layout if it doesn't exist
            QVBoxLayout(self.card_container)
        
        if not self.commander:
            return
            
        # Use existing layout
        card_layout = self.card_container.layout()
        card_layout.setContentsMargins(2, 2, 2, 2)
        
        commander_widget = QFrame()
        commander_widget.setFixedSize(96, 136)
        commander_widget.setStyleSheet(f"""
            QFrame {{
                background: {MTGTheme.CARD_BACKGROUND.name()};
                border: 2px solid #DAA520;
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid {MTGTheme.HOVER_HIGHLIGHT.name()};
            }}
        """)
        
        widget_layout = QVBoxLayout(commander_widget)
        widget_layout.setContentsMargins(2, 2, 2, 2)
        
        # Commander image
        image_area = QLabel()
        image_area.setFixedSize(88, 128)
        image_area.setAlignment(Qt.AlignCenter)
        image_area.setStyleSheet(f"""
            QLabel {{
                background: {MTGTheme.BACKGROUND_MEDIUM.name()};
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
            }}
        """)
        
        # Try to load commander image
        try:
            from image_cache import ensure_card_image
            if hasattr(self.commander, 'id'):
                image_path = ensure_card_image(self.commander.id)
                if image_path and os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(88, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_area.setPixmap(scaled_pixmap)
                    else:
                        image_area.setText("CMD")
                else:
                    image_area.setText("CMD")
            else:
                image_area.setText("CMD")
        except:
            image_area.setText("CMD")
            
        widget_layout.addWidget(image_area)
        
        # Store commander reference and add click event
        commander_widget.commander = self.commander
        def mouse_press_event(event):
            if event.button() == Qt.LeftButton:
                self.card_clicked.emit(self.commander)
        commander_widget.mousePressEvent = mouse_press_event
        
        card_layout.addWidget(commander_widget, 0, Qt.AlignCenter)

class HandDisplay(QWidget):
    """Custom hand display widget with guaranteed thin complete border."""
    
    card_clicked = Signal(object)
    
    def __init__(self, show_card_backs=False, parent=None):
        super().__init__(parent)
        self.cards = []
        self.show_card_backs = show_card_backs  # True for opponent hand
        
        # Enable drag and drop for player hands
        if not show_card_backs:
            self.setAcceptDrops(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup hand display with no scroll bars, cards fit within area."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Cards container - direct layout, no scroll area
        self.cards_container = QWidget()
        # Border on all sides top and bottom
        self.cards_container.setStyleSheet(f"""
            QWidget {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border-top: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-bottom: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-left: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-right: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
            }}
        """)
        self.cards_layout = QHBoxLayout(self.cards_container)  # Horizontal layout for hand
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(3)  # Tighter spacing
        self.cards_layout.setAlignment(Qt.AlignLeft)
        
        layout.addWidget(self.cards_container)
        
    def refresh_display(self):
        """Refresh the hand display."""
        # Clear existing widgets safely
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                try:
                    # Disconnect signals to prevent orphaned connections
                    if hasattr(widget, 'card_clicked'):
                        widget.card_clicked.disconnect()
                    if hasattr(widget, 'card_right_clicked'):
                        widget.card_right_clicked.disconnect()
                    if hasattr(widget, 'card_hovered'):
                        widget.card_hovered.disconnect()
                except Exception:
                    pass
                
                self.cards_layout.removeWidget(widget)
                widget.deleteLater()
                
        if not self.cards:
            return
            
        # Add cards to horizontal layout
        for card in self.cards:
            card_widget = self.create_card_widget(card)
            self.cards_layout.addWidget(card_widget)
            
    def create_card_widget(self, card):
        """Create a card widget for display in hand."""
        from ui.card_widget import create_card_widget
        
        # Get API from parent if available
        api = getattr(self, 'api', None) or getattr(self.parent(), 'api', None)
        
        # Create interactive card widget for hand - these can be dragged
        widget = create_card_widget(card, QSize(70, 98), api=api, location="hand")
        
        # For opponent hands, modify to show card backs
        if self.show_card_backs:
            widget.image_area.clear()
            widget.image_area.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2a4d7a,
                        stop:0.5 #1e3a5f,
                        stop:1 #132944);
                    border: 2px solid #8b5a2b;
                    border-radius: 8px;
                    color: #d4af37;
                    font-weight: bold;
                    font-size: 10px;
                }}
            """)
            widget.image_area.setText("MTG")
            widget.name_label.setText("Hidden Card")
        
        # Connect to hand-specific handlers
        widget.card_clicked.connect(self.card_clicked.emit)
        
        return widget
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasFormat("application/mtg-card") and not self.show_card_backs:
            event.acceptProposedAction()
            # Add visual feedback for hand
            self.cards_container.setStyleSheet(f"""
                QWidget {{
                    background: {MTGTheme.BACKGROUND_DARK.name()};
                    border-top: 2px solid #2196F3;
                    border-bottom: 2px solid #2196F3;
                    border-left: 2px solid #2196F3;
                    border-right: 2px solid #2196F3;
                    border-radius: 4px;
                }}
            """)
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasFormat("application/mtg-card") and not self.show_card_backs:
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Remove visual feedback - restore original style
        self.cards_container.setStyleSheet(f"""
            QWidget {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border-top: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-bottom: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-left: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-right: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
            }}
        """)
    
    def dropEvent(self, event):
        """Handle drop event."""
        if event.mimeData().hasFormat("application/mtg-card") and not self.show_card_backs:
            try:
                card_data = event.mimeData().data("application/mtg-card").data().decode()
                
                # Handle returning card to hand through API
                if self.api and hasattr(self.api, 'handle_card_drop_to_hand'):
                    self.api.handle_card_drop_to_hand(card_data)
                else:
                    print(f"Card returned to hand: {card_data}")
                    
                event.acceptProposedAction()
                
            except Exception as e:
                print(f"Error handling drop to hand: {e}")
                event.ignore()
        else:
            event.ignore()
        
        # Always restore original style after drop
        self.dragLeaveEvent(None)

class HandArea(BattlefieldZone):
    """Custom battlefield zone specifically for the player's hand with thinner borders."""
    
    def setup_ui(self):
        """Setup hand area UI with thinner borders on all sides."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # Reduced margins
        
        # Cards area with thinner border on ALL sides
        self.cards_area = QScrollArea()
        self.cards_area.setWidgetResizable(True)
        self.cards_area.setStyleSheet(f"""
            QScrollArea {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
                margin: 0px;
                padding: 0px;
            }}
            QScrollArea QWidget {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {MTGTheme.BACKGROUND_MEDIUM.name()};
                width: 8px;
                border-radius: 4px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
                min-height: 20px;
                border: none;
            }}
        """)
        
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(4)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        
        self.cards_area.setWidget(self.cards_container)
        layout.addWidget(self.cards_area)

class EnhancedGameBoard(QMainWindow):
    """Enhanced game board interface matching professional MTG design."""
    
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.game = api.game if api else None
        
        # Initialize floating game log manager
        self.game_log_manager = FloatingGameLogManager(self)
        
        # Load player preferences
        self.preferences = get_player_preferences()
        
        self.setup_ui()
        
        # Initialize event-based refresh system (no automatic timer)
        self.refresh_pending = False
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self._execute_pending_refresh)
        
        # Connect to game events for refresh triggers
        if self.api:
            self._connect_game_events()
        
    def setup_ui(self):
        """Setup the enhanced game board UI with proper MTG zone layout."""
        # Create central widget for main window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)
        
        # Top section - Opponent zones (hand, command, graveyard, exile)
        opponent_zones = self.create_opponent_zones()
        main_layout.addWidget(opponent_zones)
        
        # Middle section - Battlefields with phase bar separator
        battlefields = self.create_battlefields_section()
        main_layout.addWidget(battlefields)
        
        # Bottom section - Player zones (hand, command, graveyard, exile)
        player_zones = self.create_player_zones()
        main_layout.addWidget(player_zones)
        
        # Stack overlay - only visible when stack has items
        self.create_stack_overlay()
        
        # Enable drag and drop for the main window to catch invalid drops
        self.setAcceptDrops(True)
        
    def create_zone_widget(self, label, zone_id, width=100, height=80):
        """Create a standardized zone widget with thin border."""
        zone = QFrame()
        zone.setFixedSize(width, height)
        zone.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 4px;
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
            }}
        """)
        
        layout = QVBoxLayout(zone)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Zone label - centered over the panel
        zone_label = QLabel(label)
        zone_label.setAlignment(Qt.AlignCenter)
        zone_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                font-weight: bold;
                color: {MTGTheme.TEXT_PRIMARY.name()};
                background: transparent;
                border: none;
                text-align: center;
            }}
        """)
        layout.addWidget(zone_label, 0, Qt.AlignCenter)
        
        # Zone content area
        zone_content = BattlefieldZone("", False)
        zone_content.api = self.api  # Pass API reference
        zone_content.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(zone_content)
        
        # Store reference for later access
        setattr(self, zone_id, zone_content)
        
        return zone
        
    def create_opponent_zones(self):
        """Create the opponent's complete play area with battlefield and side zones."""
        zones_widget = QWidget()
        zones_widget.setMinimumHeight(300)
        
        main_layout = QHBoxLayout(zones_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)
        
        # Left side: Opponent's other zones (vertical stack)
        side_zones = self.create_side_zones("opponent")
        main_layout.addWidget(side_zones, 1)
        
        # Right side: Opponent's battlefield (split into two zones)
        battlefield_container = self.create_split_battlefield("opponent")
        main_layout.addWidget(battlefield_container, 4)  # Takes most space
        
        return zones_widget
        
    def create_battlefields_section(self):
        """Create the middle section with just the phase bar separator."""
        # Just return the phase indicator bar as separator
        self.phase_indicator = self.create_phase_bar()
        return self.phase_indicator
        
    def create_player_zones(self):
        """Create the player's complete play area with battlefield and side zones."""
        zones_widget = QWidget()
        zones_widget.setMinimumHeight(300)
        
        main_layout = QHBoxLayout(zones_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)
        
        # Left side: Player's battlefield (split into two zones)
        battlefield_container = self.create_split_battlefield("player")
        main_layout.addWidget(battlefield_container, 4)  # Takes most space
        
        # Right side: Player's other zones (vertical stack)
        side_zones = self.create_side_zones("player")
        main_layout.addWidget(side_zones, 1)
        
        # Bottom: Player's hand (full width)
        hand_container = self.create_hand_zone("player")
        
        # Create container for battlefield + side zones and hand
        full_layout = QVBoxLayout()
        full_layout.setContentsMargins(0, 0, 0, 0)
        full_layout.setSpacing(4)
        
        battlefield_and_sides = QWidget()
        battlefield_and_sides.setLayout(main_layout)
        full_layout.addWidget(battlefield_and_sides, 1)
        full_layout.addWidget(hand_container)
        
        zones_widget.setLayout(full_layout)
        
        return zones_widget
        
    def create_split_battlefield(self, player_type):
        """Create a split battlefield with creatures/tokens and lands/artifacts/enchantments."""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                border: none;
                background: {MTGTheme.BACKGROUND_MEDIUM.name()};
            }}
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        
        
        # Creatures battlefield zone (direct card rendering)
        creatures_battlefield = BattlefieldZone("Creatures", player_type == "opponent")
        creatures_battlefield.api = self.api  # Pass API reference
        creatures_battlefield.setMinimumHeight(100)
        creatures_battlefield.card_clicked.connect(self.on_card_clicked)
        layout.addWidget(creatures_battlefield, 1)
        
        
        # Lands battlefield zone (direct card rendering)
        lands_battlefield = BattlefieldZone("Lands", player_type == "opponent")
        lands_battlefield.api = self.api  # Pass API reference
        lands_battlefield.setMinimumHeight(100)
        lands_battlefield.card_clicked.connect(self.on_card_clicked)
        layout.addWidget(lands_battlefield, 1)
        
        # Store references for game state updates
        prefix = "opponent_" if player_type == "opponent" else "player_"
        setattr(self, f"{prefix}creatures_battlefield", creatures_battlefield)
        setattr(self, f"{prefix}lands_battlefield", lands_battlefield)
        
        return container
        
    def create_side_zones(self, player_type):
        """Create the side zones with avatar/life over command, graveyard/exile side by side."""
        container = QWidget()
        container.setFixedWidth(200)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Avatar and life zone with actual life counter (over command zone)
        avatar_life_container = QFrame()
        avatar_life_container.setFixedSize(180, 100)
        avatar_life_container.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 4px;
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
            }}
        """)
        
        avatar_life_layout = QVBoxLayout(avatar_life_container)
        avatar_life_layout.setContentsMargins(4, 4, 4, 4)
        avatar_life_layout.setSpacing(2)
        
        
        # Create actual life counter
        player_id = 1 if player_type == "opponent" else 0
        player_name = "Opponent" if player_type == "opponent" else self.preferences.get_player_name()
        avatar_path = self.preferences.get_opponent_avatar_path() if player_type == "opponent" else self.preferences.get_player_avatar_path()
        
        life_counter = LifeCounter(player_id, 40, player_name, avatar_path)
        life_counter.setFixedSize(170, 70)  # Smaller to fit in compact zone
        avatar_life_layout.addWidget(life_counter, 0, Qt.AlignCenter)
        
        # Store life counter reference
        if not hasattr(self, 'life_counters'):
            self.life_counters = [None, None]
        self.life_counters[player_id] = life_counter
        
        layout.addWidget(avatar_life_container)
        
        # Commander zone
        commander_container = QFrame()
        commander_container.setFixedSize(180, 140)  # Wider to match other zones
        commander_container.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 4px;
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
            }}
        """)
        
        commander_layout = QVBoxLayout(commander_container)
        commander_layout.setContentsMargins(4, 4, 4, 4)
        commander_layout.setSpacing(2)
        
        # Commander label
        commander_label = QLabel("commander")
        commander_label.setAlignment(Qt.AlignCenter)
        commander_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                font-weight: bold;
                color: {MTGTheme.TEXT_PRIMARY.name()};
                background: transparent;
                border: none;
            }}
        """)
        commander_layout.addWidget(commander_label)
        
        # Commander zone widget
        commander_zone = CommanderZone()
        commander_zone.card_clicked.connect(self.on_commander_clicked)
        commander_layout.addWidget(commander_zone)
        
        # Store reference
        setattr(self, f"{player_type}_commander_zone_new", commander_zone)
        
        layout.addWidget(commander_container)
        
        # Graveyard and Exile side by side
        graveyard_exile_container = QWidget()
        graveyard_exile_layout = QHBoxLayout(graveyard_exile_container)
        graveyard_exile_layout.setContentsMargins(0, 0, 0, 0)
        graveyard_exile_layout.setSpacing(4)
        
        # Graveyard zone (left side)
        graveyard = self.create_zone_widget("graveyard", f"{player_type}_graveyard_new", 86, 80)
        graveyard_exile_layout.addWidget(graveyard)
        
        # Exile zone (right side)
        exile = self.create_zone_widget("exile", f"{player_type}_exile_new", 86, 80)
        graveyard_exile_layout.addWidget(exile)
        
        layout.addWidget(graveyard_exile_container)
        
        return container
        
    def create_hand_zone(self, player_type):
        """Create the hand zone."""
        container = QFrame()
        container.setFixedHeight(114)  # Proper fit for cards (98 + 16 padding)
        container.setStyleSheet("""
            QFrame {
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        
        # Hand display
        is_opponent = player_type == "opponent"
        hand_display = HandDisplay(show_card_backs=is_opponent)
        hand_display.api = self.api  # Pass API reference
        hand_display.setFixedHeight(106)  # Match card height plus padding
        if not is_opponent:
            hand_display.card_clicked.connect(self.on_hand_card_clicked)
        
        layout.addWidget(hand_display)
        
        # Store reference
        if is_opponent:
            self.opponent_hand_display = hand_display
        else:
            self.hand_area = hand_display
        
        return container
        
    def is_creature_or_token(self, card):
        """Determine if a card is a creature or token for battlefield splitting."""
        try:
            # Check if it's a permanent with a card
            actual_card = card.card if hasattr(card, 'card') else card
            
            # Debug: Print card info for troubleshooting
            card_name = getattr(actual_card, 'name', 'Unknown')
            
            # Check multiple possible type attributes
            card_types = []
            
            # Method 1: Check 'types' list (most common)
            if hasattr(actual_card, 'types') and actual_card.types:
                card_types.extend([t.lower() for t in actual_card.types])
            
            # Method 2: Check 'type_line' string
            if hasattr(actual_card, 'type_line') and actual_card.type_line:
                card_types.extend([t.strip().lower() for t in actual_card.type_line.split()])
            
            # Method 3: Check 'type' attribute
            if hasattr(actual_card, 'type') and actual_card.type:
                if isinstance(actual_card.type, list):
                    card_types.extend([t.lower() for t in actual_card.type])
                else:
                    card_types.extend([t.strip().lower() for t in str(actual_card.type).split()])
            
            # Check for creature or token types
            is_creature = any(t in ['creature', 'token'] for t in card_types)
            
            # Check for non-creature types that should NOT be categorized as creatures
            is_land = any(t == 'land' for t in card_types)
            is_artifact = any(t == 'artifact' for t in card_types)
            is_enchantment = any(t == 'enchantment' for t in card_types)
            is_planeswalker = any(t == 'planeswalker' for t in card_types)
            
            # If it's explicitly a non-creature permanent, don't categorize as creature
            # even if it has P/T (some lands/artifacts can have P/T due to abilities)
            if is_land or is_artifact or is_enchantment or is_planeswalker:
                if not is_creature:  # Unless it's also explicitly a creature
                    result = False
                else:
                    result = True  # Artifact Creature, Land Creature, etc.
            else:
                # For other cards, check if it has power/toughness (likely creature)
                has_pt = hasattr(actual_card, 'power') and hasattr(actual_card, 'toughness')
                result = is_creature or has_pt
            
            return result
            
        except Exception as e:
            print(f"❌ CATEGORIZE ERROR for card: {e}")
            return False
        
        
    def create_phase_bar(self):
        """Create the phase bar that separates battlefields with turn indicator."""
        # Create the IntegratedPhaseBar directly without parent manipulation
        phase_bar = IntegratedPhaseBar(parent=None)
        phase_bar.setFixedHeight(50)  # Shorter height
        phase_bar.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {MTGTheme.BACKGROUND_LIGHT.name()},
                    stop:1 {MTGTheme.BACKGROUND_MEDIUM.name()});
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 4px;
                margin: 2px 0px;
            }}
        """)
        
        return phase_bar
        
    def create_stack_overlay(self):
        """Create the stack overlay that appears only when stack has items."""
        self.stack_overlay = QFrame(self)
        self.stack_overlay.setStyleSheet(f"""
            QFrame {{
                background: rgba(0, 0, 0, 200);
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 6px;
            }}
        """)
        self.stack_overlay.setFixedSize(250, 300)
        self.stack_overlay.hide()  # Hidden by default
        
        # Position overlay in top-right of center area
        self.stack_overlay.move(self.width() - 270, 20)
        
        # Create stack widget inside overlay
        overlay_layout = QVBoxLayout(self.stack_overlay)
        overlay_layout.setContentsMargins(8, 8, 8, 8)
        
        # Stack title
        stack_title = QLabel("Stack")
        stack_title.setFont(QFont("Arial", 12, QFont.Bold))
        stack_title.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()};")
        overlay_layout.addWidget(stack_title)
        
        # Stack widget
        self.stack_widget = StackWidget()
        overlay_layout.addWidget(self.stack_widget)
        
        
        
        
        
        
    def apply_simple_hand_border(self):
        """Apply custom styling to hand area after initialization."""
        if hasattr(self, 'hand_area') and self.hand_area and hasattr(self.hand_area, 'cards_area'):
            # Force apply the thinner border styling
            self.hand_area.cards_area.setStyleSheet(f"""
                QScrollArea {{
                    background: {MTGTheme.BACKGROUND_DARK.name()};
                    border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-radius: 6px;
                }}
                QScrollArea QWidget {{
                    background: transparent;
                }}
                QScrollBar:vertical {{
                    background: {MTGTheme.BACKGROUND_MEDIUM.name()};
                    width: 12px;
                    border-radius: 6px;
                }}
                QScrollBar::handle:vertical {{
                    background: {MTGTheme.BORDER_LIGHT.name()};
                    border-radius: 6px;
                    min-height: 20px;
                }}
            """)
    
    def force_hand_styling(self):
        """Aggressively force hand area styling to ensure complete thin border."""
        if hasattr(self, 'hand_area') and self.hand_area:
            # Force override all possible styling sources with complete border
            hand_style = f"""
                QScrollArea {{
                    background: {MTGTheme.BACKGROUND_DARK.name()};
                    border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-top: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-bottom: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-left: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-right: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-radius: 4px;
                    margin: 0px;
                    padding: 1px;
                }}
                QScrollArea QWidget {{
                    background: transparent;
                    border: none;
                }}
            """
            
            # Apply to the hand area itself
            if hasattr(self.hand_area, 'cards_area'):
                self.hand_area.cards_area.setStyleSheet(hand_style)
                print(f"🖌️ Forced complete hand border: 1px solid on ALL sides")
            
            # Also apply to the outer container
            if hasattr(self.hand_area, 'setStyleSheet'):
                self.hand_area.setStyleSheet(f"""
                    HandArea {{
                        border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                        border-radius: 4px;
                    }}
                """)
    
    def apply_simple_hand_border(self):
        """Apply simple thin border to hand area that actually works."""
        if hasattr(self, 'hand_area') and self.hand_area and hasattr(self.hand_area, 'cards_area'):
            # Direct styling override with thin border on all sides
            self.hand_area.cards_area.setStyleSheet(f"""
                QScrollArea {{
                    background: {MTGTheme.BACKGROUND_DARK.name()};
                    border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-radius: 4px;
                }}
                QScrollArea QWidget {{
                    background: {MTGTheme.BACKGROUND_DARK.name()};
                }}
            """)
            print(f"🎲 Applied simple hand border: 1px solid {MTGTheme.BORDER_LIGHT.name()}")    
    
    def fix_hand_containment(self):
        """Fix hand area to ensure cards stay within the border container."""
        if hasattr(self, 'hand_area') and self.hand_area:
            # Force the cards container to have reasonable margins for visibility
            if hasattr(self.hand_area, 'cards_container') and self.hand_area.cards_container:
                # Override the grid layout to use visible but contained spacing
                if hasattr(self.hand_area, 'cards_layout'):
                    self.hand_area.cards_layout.setContentsMargins(2, 2, 2, 2)
                    self.hand_area.cards_layout.setSpacing(2)
                    
            # Make sure the scroll area is properly sized
            if hasattr(self.hand_area, 'cards_area'):
                self.hand_area.cards_area.setMinimumHeight(120)  # Ensure minimum height for cards
                    
            print("🔧 Fixed hand area containment with proper card visibility")
    
    def force_life_counter_alignment(self):
        """Force proper alignment and styling of life counters."""
        if hasattr(self, 'life_counters') and self.life_counters:
            for i, counter in enumerate(self.life_counters):
                if counter:
                    # Force avatar update to ensure proper display
                    if hasattr(counter, 'update_avatar'):
                        counter.update_avatar()
                    
                    # Ensure the counter is centered in its parent
                    if hasattr(counter.parent(), 'layout'):
                        parent_layout = counter.parent().layout()
                        if parent_layout:
                            parent_layout.setAlignment(counter, Qt.AlignCenter)
                    
                    # Force layout update
                    counter.update()
                    
                    print(f"🎯 Updated embedded life counter {i}: {counter.player_name} - Size: {counter.size().width()}x{counter.size().height()}")
        
    # Event handlers
    def update_life_totals(self):
        # Update life totals from game state (fix swapped display)
        if self.game and self.game.players:
            # life_counters[0] should show player 0's life, life_counters[1] should show player 1's life
            for i, player in enumerate(self.game.players):
                if i < len(self.life_counters):
                    current_life = getattr(player, 'life', 40)
                    self.life_counters[i].update_life_from_game(current_life)
        
    def on_card_clicked(self, card):
        """Handle card clicks on battlefield."""
        self.log_message(f"Clicked: {getattr(card, 'name', 'Unknown Card')}")
        self.schedule_refresh("card_clicked")
        
    def on_hand_card_clicked(self, card):
        """Handle hand card clicks."""
        self.log_message(f"Selected from hand: {getattr(card, 'name', 'Unknown Card')}")
        self.schedule_refresh("hand_card_clicked")
        
    def on_opponent_hand_card_clicked(self, card):
        """Handle opponent hand card clicks."""
        self.log_message(f"Opponent hand card clicked (hidden)", "info")
        # No refresh needed for opponent hand clicks
        
    def on_commander_clicked(self, card):
        """Handle commander card clicks."""
        self.log_message(f"Commander clicked: {getattr(card, 'name', 'Unknown Commander')}", "player")
        self.schedule_refresh("commander_clicked")
        
    def on_graveyard_card_clicked(self, card):
        """Handle graveyard card clicks."""
        self.log_message(f"Graveyard card clicked: {getattr(card, 'name', 'Unknown Card')}", "info")
        self.schedule_refresh("graveyard_card_clicked")
        
    def refresh_display(self):
        """Refresh all display elements from game state."""
        self.update_life_totals()
        self.refresh_game_state()
        
            
    def update_player_avatars(self):
        """Update player avatars from preferences."""
        try:
            # Update player life counter
            if self.life_counters and len(self.life_counters) > 0 and self.life_counters[0]:
                self.life_counters[0].set_avatar(self.preferences.get_player_avatar_path())
                
            # Update opponent life counter  
            if self.life_counters and len(self.life_counters) > 1 and self.life_counters[1]:
                self.life_counters[1].set_avatar(self.preferences.get_opponent_avatar_path())
                
        except Exception as e:
            print(f"Error updating avatars: {e}")
    
    def log_message(self, message, entry_type="info"):
        """Add message to floating game log."""
        self.game_log_manager.add_log_entry(message, entry_type)
        
    def refresh_game_state(self):
        """Refresh the game state display with comprehensive error handling."""
        if not self.api or not self.game:
            print(f"⚠️  REFRESH: No API or game available")
            return
            
        try:
            print(f"🔄 REFRESH: Starting game state refresh...")
            # Update life totals from game state
            self.update_life_totals()
            
            # Update phase indicator
            current_phase = getattr(self.api.controller, 'current_phase', 'unknown')
            current_step = getattr(self.api.controller, 'current_step', '')
            active_player_id = getattr(self.game, 'active_player', 0)
            active_player_name = "Unknown"
            turn_number = getattr(self.game, 'turn_number', 1)
            
            if self.game.players and 0 <= active_player_id < len(self.game.players):
                active_player_name = getattr(self.game.players[active_player_id], 'name', f'Player {active_player_id+1}')
                
            # Update mana pool data
            mana_dict = {}
            if self.game.players:
                player = self.game.players[0]
                if hasattr(player, 'mana_pool'):
                    for color in ['W', 'U', 'B', 'R', 'G', 'C']:
                        mana_dict[color] = getattr(player.mana_pool, color.lower(), 0)
                        
            self.phase_indicator.set_phase(current_phase, current_step, active_player_name, turn_number, mana_dict)
            
            # Update stack overlay visibility
            self.update_stack_overlay()
            
            # Mana pool is now displayed in the phase bar
                    
            # Update split battlefields
            if self.game.players:
                # Player battlefields (split into creatures and lands)
                player_cards = getattr(self.game.players[0], 'battlefield', [])
                # Categorize cards for battlefield zones
                creatures = []
                lands_etc = []
                
                for card in player_cards:
                    is_creature = self.is_creature_or_token(card)
                    if is_creature:
                        creatures.append(card)
                    else:
                        lands_etc.append(card)
                
                if hasattr(self, 'player_creatures_battlefield'):
                    creature_cards = [perm.card if hasattr(perm, 'card') else perm for perm in creatures]
                    self.player_creatures_battlefield.cards = creature_cards
                    self.player_creatures_battlefield.refresh_display()
                
                if hasattr(self, 'player_lands_battlefield'):
                    land_cards = [perm.card if hasattr(perm, 'card') else perm for perm in lands_etc]
                    self.player_lands_battlefield.cards = land_cards
                    self.player_lands_battlefield.refresh_display()
                
                # Player hand
                player_hand = getattr(self.game.players[0], 'hand', [])
                if hasattr(self, 'hand_area'):
                    self.hand_area.cards = player_hand
                    self.hand_area.refresh_display()
                
                # Opponent battlefields (split into creatures and lands)
                if len(self.game.players) > 1:
                    opponent_cards = getattr(self.game.players[1], 'battlefield', [])
                    opp_creatures = [card for card in opponent_cards if self.is_creature_or_token(card)]
                    opp_lands_etc = [card for card in opponent_cards if not self.is_creature_or_token(card)]
                    
                    if hasattr(self, 'opponent_creatures_battlefield'):
                        self.opponent_creatures_battlefield.cards = [perm.card if hasattr(perm, 'card') else perm for perm in opp_creatures]
                        self.opponent_creatures_battlefield.refresh_display()
                    
                    if hasattr(self, 'opponent_lands_battlefield'):
                        self.opponent_lands_battlefield.cards = [perm.card if hasattr(perm, 'card') else perm for perm in opp_lands_etc]
                        self.opponent_lands_battlefield.refresh_display()
                    
                    # Opponent hand
                    opponent_hand = getattr(self.game.players[1], 'hand', [])
                    if hasattr(self, 'opponent_hand_display'):
                        self.opponent_hand_display.cards = opponent_hand
                        self.opponent_hand_display.refresh_display()
                    
                # Update new zone structure - Player zones
                player_commander = getattr(self.game.players[0], 'commander', None)
                if hasattr(self, 'player_commander_zone_new'):
                    self.player_commander_zone_new.set_commander(player_commander)
                    self.player_commander_zone_new.refresh_display()
                
                player_graveyard = getattr(self.game.players[0], 'graveyard', [])
                if hasattr(self, 'player_graveyard_new'):
                    self.player_graveyard_new.cards = player_graveyard
                    self.player_graveyard_new.refresh_display()
                
                player_exile = getattr(self.game.players[0], 'exile', [])
                if hasattr(self, 'player_exile_new'):
                    self.player_exile_new.cards = player_exile
                    self.player_exile_new.refresh_display()
                
                # Update new zone structure - Opponent zones
                if len(self.game.players) > 1:
                    opponent_commander = getattr(self.game.players[1], 'commander', None)
                    if hasattr(self, 'opponent_commander_zone_new'):
                        self.opponent_commander_zone_new.set_commander(opponent_commander)
                        self.opponent_commander_zone_new.refresh_display()
                    
                    opponent_graveyard = getattr(self.game.players[1], 'graveyard', [])
                    if hasattr(self, 'opponent_graveyard_new'):
                        self.opponent_graveyard_new.cards = opponent_graveyard
                        self.opponent_graveyard_new.refresh_display()
                    
                    opponent_exile = getattr(self.game.players[1], 'exile', [])
                    if hasattr(self, 'opponent_exile_new'):
                        self.opponent_exile_new.cards = opponent_exile
                        self.opponent_exile_new.refresh_display()
                    
        except Exception as e:
            print(f"❌ REFRESH: Game state refresh error: {e}")
            import traceback
            traceback.print_exc()
            # Continue anyway to prevent crashes
            
    def update_stack_overlay(self):
        """Update stack overlay visibility based on stack contents."""
        try:
            # Check if stack has items
            stack_has_items = False
            if hasattr(self.api, 'game') and hasattr(self.api.game, 'stack'):
                stack = self.api.game.stack
                if hasattr(stack, 'stack') and stack.stack:
                    stack_has_items = len(stack.stack) > 0
                elif hasattr(stack, '__len__'):
                    stack_has_items = len(stack) > 0
            
            # Also check stack widget's items
            if hasattr(self, 'stack_widget') and hasattr(self.stack_widget, 'stack_items'):
                if self.stack_widget.stack_items:
                    stack_has_items = True
            
            # Show/hide overlay based on stack contents
            if hasattr(self, 'stack_overlay'):
                if stack_has_items:
                    self.stack_overlay.show()
                    # Position overlay in top-right corner
                    self.stack_overlay.move(self.width() - 270, 20)
                else:
                    self.stack_overlay.hide()
                    
        except Exception:
            pass  # Silently handle stack overlay errors
            
    def highlight_valid_drop_targets(self, card_types, is_dragging):
        """Highlight valid drop targets based on card types being dragged."""
        if not is_dragging:
            # Clear all highlights
            self._clear_all_highlights()
            return
        
        # Determine valid targets based on card types
        is_creature = "Creature" in card_types
        is_land = "Land" in card_types
        is_artifact = "Artifact" in card_types
        is_enchantment = "Enchantment" in card_types
        is_planeswalker = "Planeswalker" in card_types
        
        # Highlight appropriate battlefield zones
        if is_creature or is_artifact or is_enchantment or is_planeswalker:
            # Permanent cards go to battlefield
            if hasattr(self, 'player_creatures_battlefield') and is_creature:
                self._highlight_zone(self.player_creatures_battlefield, "#00ff00", "Valid: Creatures")
            elif hasattr(self, 'player_lands_battlefield') and (is_artifact or is_enchantment or is_planeswalker):
                self._highlight_zone(self.player_lands_battlefield, "#00ff00", "Valid: Non-creatures")
        
        if is_land:
            # Lands go to lands battlefield
            if hasattr(self, 'player_lands_battlefield'):
                self._highlight_zone(self.player_lands_battlefield, "#00ff00", "Valid: Lands")
        
        # Hand is always a valid drop target for returning cards
        if hasattr(self, 'hand_area'):
            self._highlight_zone(self.hand_area, "#0099ff", "Return to Hand")
    
    def _highlight_zone(self, zone, color, tooltip_text=""):
        """Apply highlight styling to a zone."""
        try:
            if hasattr(zone, 'setStyleSheet'):
                zone.setStyleSheet(f"""
                    QFrame {{
                        border: 3px solid {color};
                        border-radius: 6px;
                        background: rgba({self._hex_to_rgb(color)}, 0.1);
                    }}
                """)
            if hasattr(zone, 'setToolTip') and tooltip_text:
                zone.setToolTip(tooltip_text)
        except Exception as e:
            print(f"Error highlighting zone: {e}")
    
    def _clear_all_highlights(self):
        """Clear all zone highlights."""
        zones_to_clear = [
            'player_creatures_battlefield', 'player_lands_battlefield', 
            'opponent_creatures_battlefield', 'opponent_lands_battlefield',
            'hand_area', 'opponent_hand_display'
        ]
        
        for zone_name in zones_to_clear:
            if hasattr(self, zone_name):
                zone = getattr(self, zone_name)
                try:
                    if hasattr(zone, 'setStyleSheet'):
                        # Restore original styling
                        zone.setStyleSheet(f"""
                            QFrame {{
                                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                                border-radius: 4px;
                                background: {MTGTheme.BACKGROUND_DARK.name()};
                            }}
                        """)
                    if hasattr(zone, 'setToolTip'):
                        zone.setToolTip("")
                except Exception as e:
                    print(f"Error clearing highlight for {zone_name}: {e}")
    
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB string."""
        hex_color = hex_color.lstrip('#')
        return ', '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))
    
    def _connect_game_events(self):
        """Connect to game events that should trigger UI refresh."""
        try:
            # Connect to API events if available
            if hasattr(self.api, 'card_played'):
                self.api.card_played.connect(self.schedule_refresh)
            if hasattr(self.api, 'phase_changed'):
                self.api.phase_changed.connect(self.schedule_refresh)
            if hasattr(self.api, 'turn_changed'):
                self.api.turn_changed.connect(self.schedule_refresh)
        except Exception as e:
            print(f"Warning: Could not connect all game events: {e}")
    
    def schedule_refresh(self, reason="game_event"):
        """Schedule a UI refresh to happen on the next event loop."""
        if not self.refresh_pending:
            self.refresh_pending = True
            self.refresh_timer.start(50)  # 50ms delay to batch multiple changes
            print(f"🔄 REFRESH: Scheduled refresh due to {reason}")
    
    def _execute_pending_refresh(self):
        """Execute the pending refresh."""
        self.refresh_pending = False
        self.refresh_game_state()
    
    def on_card_played(self, card):
        """Handle card being played - trigger refresh."""
        self.schedule_refresh("card_played")
    
    def on_card_moved(self, card, from_zone, to_zone):
        """Handle card moving between zones - trigger refresh."""
        self.schedule_refresh(f"card_moved_{from_zone}_to_{to_zone}")
    
    def on_mouse_click(self, card=None):
        """Handle mouse click - minimal refresh if needed."""
        # Only refresh if there are actual state changes to display
        if hasattr(self, 'game') and self.game:
            # Check if game state has changed since last refresh
            self.schedule_refresh("mouse_click")
    
    def resizeEvent(self, event):
        """Handle window resize to reposition overlays."""
        super().resizeEvent(event)
        
        # Reposition stack overlay
        if hasattr(self, 'stack_overlay') and self.stack_overlay.isVisible():
            self.stack_overlay.move(self.width() - 270, 20)
    
    def dragEnterEvent(self, event):
        """Handle drag enter on main window (catch-all for invalid drops)."""
        if event.mimeData().hasFormat("application/mtg-card"):
            # Accept the drag but we'll reject it in dropEvent
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move on main window."""
        if event.mimeData().hasFormat("application/mtg-card"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle drop on main window (invalid drop zone - return card to hand)."""
        try:
            if event.mimeData().hasFormat("application/mtg-card"):
                card_data = event.mimeData().data("application/mtg-card").data().decode()
                card_name = "Unknown Card"
                
                # Try to get card name for better feedback
                try:
                    if self.api and self.game and self.game.players:
                        for card in self.game.players[0].hand:
                            if getattr(card, 'id', '') == card_data:
                                card_name = getattr(card, 'name', 'Unknown Card')
                                break
                except Exception:
                    pass
                
                print(f"🔄 Card '{card_name}' dropped on invalid area - returned to hand")
                
                # Always ignore drops on main window (card returns to hand automatically)
                event.ignore()
            else:
                event.ignore()
        except Exception as e:
            print(f"Error handling main window drop: {e}")
            event.ignore()

def create_enhanced_game_board(api):
    """Create an enhanced game board widget."""
    board = EnhancedGameBoard(api)
    print("🎮 Enhanced game board created with:")
    print(f"   - Life counter font size: {board.life_counters[0].life_display.font().pointSize() if board.life_counters and board.life_counters[0] else 'N/A'}pt")
    print(f"   - Hand area border: {'1px' if isinstance(board.hand_area, HandArea) else '2px (fallback)'}")
    
    # Optional: Try to enhance the existing board with interactive card features
    try:
        _add_card_interactions_to_existing_board(board)
        print("   - Enhanced with interactive card features")
    except Exception as e:
        print(f"   - Card interactions unavailable: {e}")
        
    return board


def _add_card_interactions_to_existing_board(board):
    """Add interactive card features to the existing game board without changing layout."""
    # Enhanced interactions are now built into the create_card_widget method
    # which uses the modern InteractiveCardWidget from ui.card_widget
    
    # Add any additional board-level enhancements here
    try:
        # Set up any board-level drag and drop or interaction handlers
        if hasattr(board, 'setAcceptDrops'):
            board.setAcceptDrops(True)
            
        # Additional enhancements can be added here as needed
        pass
        
    except Exception as e:
        # Silently handle any enhancement errors to avoid breaking the UI
        print(f"Note: Some card interactions may be limited: {e}")
