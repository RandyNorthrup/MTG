"""Enhanced battlefield layout and zone management.

Features:
- Interactive battlefield with proper card positioning
- Drag-and-drop zone validation
- Visual feedback for valid/invalid actions
- Animated card movement between zones
- Proper spacing and organization
- Support for multiple players and battlefield layouts
"""

import os
from typing import List, Dict, Optional, Tuple, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy, QSpacerItem, QGraphicsEffect
)
from PySide6.QtCore import (
    Qt, QSize, QTimer, Signal, QRect, QPoint, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup
)
from PySide6.QtGui import (
    QPixmap, QPainter, QBrush, QColor, QPen, QFont,
    QLinearGradient, QRadialGradient, QDropEvent, QDragEnterEvent
)

from ui.theme import MTGTheme
from ui.card_widget import create_card_widget


class FlowLayout(QHBoxLayout):
    """Horizontal flow layout that wraps cards nicely."""
    
    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self.setSpacing(spacing)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
    def add_card_widget(self, card_widget):
        """Add a card widget with proper spacing."""
        self.addWidget(card_widget)
        
    def remove_card_widget(self, card_widget):
        """Remove a card widget."""
        self.removeWidget(card_widget)
        card_widget.setParent(None)


class ZoneWidget(QFrame):
    """Base class for game zones (hand, battlefield, graveyard, etc.)."""
    
    card_added = Signal(object, str)  # card, zone_name
    card_removed = Signal(object, str)  # card, zone_name
    card_activated = Signal(object, str)  # card, action
    
    def __init__(self, zone_name, title=None, parent=None, api=None):
        super().__init__(parent)
        self.zone_name = zone_name
        self.title = title or zone_name.title()
        self.api = api
        self.card_widgets = {}  # card_id -> widget mapping
        self.cards = []  # List of actual card objects
        
        self.setAcceptDrops(True)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the zone UI."""
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {MTGTheme.BORDER_MEDIUM.name()};
                border-radius: 8px;
                background: {MTGTheme.BACKGROUND_DARK.name()};
                margin: 2px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        # Zone title
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {MTGTheme.TEXT_PRIMARY.name()};
                background: {MTGTheme.BACKGROUND_MEDIUM.name()};
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
            }}
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Scroll area for cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
                background: transparent;
            }}
        """)
        
        # Cards container
        self.cards_container = QWidget()
        self.cards_layout = FlowLayout(self.cards_container)
        self.scroll_area.setWidget(self.cards_container)
        
        layout.addWidget(self.scroll_area, 1)
        
        # Status label (card count, etc.)
        self.status_label = QLabel("0 cards")
        self.status_label.setFont(QFont("Arial", 8))
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {MTGTheme.TEXT_DISABLED.name()};
                background: transparent;
                padding: 2px 4px;
            }}
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
    def add_card(self, card, animated=True):
        """Add a card to this zone."""
        if card in self.cards:
            return  # Already in zone
            
        # Create card widget using the card_widget module with proper location
        card_widget = create_card_widget(card, QSize(100, 140), api=self.api, location=self.zone_name)
        card_widget.setParent(self.cards_container)
        # Connect available signals
        if hasattr(card_widget, 'card_clicked'):
            card_widget.card_clicked.connect(lambda c: self._on_card_clicked(c))
        if hasattr(card_widget, 'card_double_clicked'):
            card_widget.card_double_clicked.connect(lambda c: self._on_card_double_clicked(c))
        if hasattr(card_widget, 'card_tapped'):
            card_widget.card_tapped.connect(lambda c: self._on_card_tapped(c))
        
        # Add to zone
        self.cards.append(card)
        self.card_widgets[getattr(card, 'id', str(id(card)))] = card_widget
        
        if animated:
            self._animate_card_entry(card_widget)
        else:
            self.cards_layout.add_card_widget(card_widget)
            
        self._update_status()
        self.card_added.emit(card, self.zone_name)
        
    def remove_card(self, card, animated=True):
        """Remove a card from this zone."""
        if card not in self.cards:
            return
            
        card_id = getattr(card, 'id', str(id(card)))
        card_widget = self.card_widgets.get(card_id)
        
        if card_widget:
            if animated:
                self._animate_card_exit(card_widget)
            else:
                self.cards_layout.remove_card_widget(card_widget)
                card_widget.deleteLater()
                
            del self.card_widgets[card_id]
            
        self.cards.remove(card)
        self._update_status()
        self.card_removed.emit(card, self.zone_name)
        
    def get_card_widget(self, card):
        """Get the widget for a specific card."""
        card_id = getattr(card, 'id', str(id(card)))
        return self.card_widgets.get(card_id)
        
    def tap_card(self, card, animated=True):
        """Tap a card in this zone."""
        card_widget = self.get_card_widget(card)
        if card_widget:
            card_widget.tap_card(animated)
            
    def untap_card(self, card, animated=True):
        """Untap a card in this zone."""
        card_widget = self.get_card_widget(card)
        if card_widget:
            card_widget.untap_card(animated)
            
    def untap_all(self, animated=True):
        """Untap all cards in this zone."""
        for card in self.cards:
            self.untap_card(card, animated)
            
    def set_card_summoning_sick(self, card, sick=True):
        """Set summoning sickness for a card."""
        card_widget = self.get_card_widget(card)
        if card_widget:
            card_widget.set_summoning_sick(sick)
            
    def _update_status(self):
        """Update the status label."""
        count = len(self.cards)
        self.status_label.setText(f"{count} card{'s' if count != 1 else ''}")
        
    def _animate_card_entry(self, card_widget):
        """Animate a card entering the zone."""
        # Start with card scaled down and transparent
        card_widget.current_scale = 0.5
        card_widget.setWindowOpacity(0.0)
        
        self.cards_layout.add_card_widget(card_widget)
        
        # Animate scale and opacity
        scale_anim = QPropertyAnimation(card_widget, b"current_scale")
        scale_anim.setDuration(300)
        scale_anim.setStartValue(0.5)
        scale_anim.setEndValue(1.0)
        scale_anim.setEasingCurve(QEasingCurve.OutBack)
        
        opacity_anim = QPropertyAnimation(card_widget, b"windowOpacity")
        opacity_anim.setDuration(250)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Start animations
        scale_anim.start()
        opacity_anim.start()
        
    def _animate_card_exit(self, card_widget):
        """Animate a card leaving the zone."""
        # Animate scale down and fade out
        scale_anim = QPropertyAnimation(card_widget, b"current_scale")
        scale_anim.setDuration(200)
        scale_anim.setStartValue(card_widget.current_scale)
        scale_anim.setEndValue(0.1)
        scale_anim.setEasingCurve(QEasingCurve.InBack)
        
        opacity_anim = QPropertyAnimation(card_widget, b"windowOpacity")
        opacity_anim.setDuration(200)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.InCubic)
        
        # When animation finishes, remove the widget
        opacity_anim.finished.connect(lambda: self._finish_card_exit(card_widget))
        
        scale_anim.start()
        opacity_anim.start()
        
    def _finish_card_exit(self, card_widget):
        """Finish removing a card widget."""
        self.cards_layout.remove_card_widget(card_widget)
        card_widget.deleteLater()
        
    def _on_card_clicked(self, card):
        """Handle card clicked."""
        self.card_activated.emit(card, "clicked")
        
    def _on_card_double_clicked(self, card):
        """Handle card double-clicked."""
        self.card_activated.emit(card, "double_clicked")
        
    def _on_card_tapped(self, card):
        """Handle card tapped."""
        self.card_activated.emit(card, "tapped")
        
    def _on_ability_activated(self, card, ability):
        """Handle ability activated."""
        self.card_activated.emit(card, f"ability_{ability}")
        
    def dragEnterEvent(self, event):
        """Handle drag enter for the zone."""
        if event.mimeData().hasFormat("application/mtg-card"):
            if self._can_accept_card(event):
                self._highlight_drop_zone(True)
                event.acceptProposedAction()
            else:
                self._highlight_drop_zone(False)
                event.ignore()
        else:
            event.ignore()
            
    def dragLeaveEvent(self, event):
        """Handle drag leave."""
        self._highlight_drop_zone(None)
        
    def dropEvent(self, event):
        """Handle drop event."""
        try:
            if event.mimeData().hasFormat("application/mtg-card"):
                # Handle the drop and check result
                success = self._handle_card_drop(event)
                if success:
                    event.acceptProposedAction()
                    print(f"✅ ZONE: Successfully handled drop to {self.zone_name}")
                else:
                    event.ignore()
                    print(f"❌ ZONE: Failed to handle drop to {self.zone_name}")
            else:
                event.ignore()
                print(f"⚠️  ZONE: Invalid drop data format")
        except Exception as e:
            print(f"❌ ZONE: Drop event error: {e}")
            import traceback
            traceback.print_exc()
            event.ignore()
        finally:
            # Always remove visual feedback after drop
            try:
                self._highlight_drop_zone(None)
            except Exception:
                pass
        
    def _can_accept_card(self, event):
        """Check if this zone can accept the dragged card."""
        # Override in subclasses for zone-specific logic
        return True
        
    def _highlight_drop_zone(self, valid):
        """Highlight the drop zone."""
        if valid is True:
            self.setStyleSheet(f"""
                QFrame {{
                    border: 3px solid {MTGTheme.SUCCESS.name()};
                    border-radius: 8px;
                    background: {MTGTheme.SUCCESS.name()}20;
                    margin: 2px;
                }}
            """)
        elif valid is False:
            self.setStyleSheet(f"""
                QFrame {{
                    border: 3px solid {MTGTheme.DANGER.name()};
                    border-radius: 8px;
                    background: {MTGTheme.DANGER.name()}20;
                    margin: 2px;
                }}
            """)
        else:
            # Reset to normal
            self.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {MTGTheme.BORDER_MEDIUM.name()};
                    border-radius: 8px;
                    background: {MTGTheme.BACKGROUND_DARK.name()};
                    margin: 2px;
                }}
            """)
            
    def _handle_card_drop(self, event):
        """Handle a card being dropped in this zone with comprehensive error handling."""
        try:
            # Extract card information safely
            if not event.mimeData().hasFormat("application/mtg-card"):
                print(f"❌ ZONE-DROP: Invalid mime data format")
                return False
                
            try:
                card_data = event.mimeData().data("application/mtg-card").data().decode()
                print(f"🔍 ZONE-DROP: Extracted card data: {card_data}")
            except Exception as e:
                print(f"❌ ZONE-DROP: Failed to extract card data: {e}")
                return False
            
            # Handle based on zone type
            if self.zone_name == "hand":
                print(f"🔍 ZONE-DROP: Handling drop to hand")
                return self._handle_drop_to_hand(card_data)
            elif self.zone_name == "battlefield":
                print(f"🔍 ZONE-DROP: Handling drop to battlefield")
                return self._handle_drop_to_battlefield(card_data)
            elif self.zone_name == "graveyard":
                print(f"🔍 ZONE-DROP: Handling drop to graveyard")
                return self._handle_drop_to_graveyard(card_data)
            else:
                print(f"⚠️  ZONE-DROP: Unknown zone type: {self.zone_name}")
                return False
                
        except Exception as e:
            print(f"❌ ZONE-DROP ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _handle_drop_to_hand(self, card_data):
        """Handle drop to hand zone."""
        try:
            if self.api and hasattr(self.api, 'handle_card_drop_to_hand'):
                return self.api.handle_card_drop_to_hand(card_data)
            else:
                print(f"⚠️  No API available for hand drop")
                return False
        except Exception as e:
            print(f"❌ Hand drop error: {e}")
            return False
            
    def _handle_drop_to_battlefield(self, card_data):
        """Handle drop to battlefield zone."""
        try:
            if self.api and hasattr(self.api, 'handle_card_drop_to_battlefield'):
                # Let API auto-place the card in the correct battlefield zone
                return self.api.handle_card_drop_to_battlefield(card_data)
            else:
                print(f"⚠️  No API available for battlefield drop")
                return False
        except Exception as e:
            print(f"❌ Battlefield drop error: {e}")
            return False
            
    def _handle_drop_to_graveyard(self, card_data):
        """Handle drop to graveyard zone."""
        try:
            # Graveyard typically doesn't accept direct drops
            print(f"⚠️  Direct drops to graveyard not supported")
            return False
        except Exception as e:
            print(f"❌ Graveyard drop error: {e}")
            return False


class HandZone(ZoneWidget):
    """Player's hand zone with horizontal card layout."""
    
    def __init__(self, player_name="Player", parent=None, api=None):
        super().__init__("hand", f"{player_name}'s Hand", parent, api)
        self.setMinimumHeight(160)
        
    def setup_ui(self):
        """Setup hand-specific UI."""
        super().setup_ui()
        
        # Make scroll area horizontal
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Adjust card size for hand display
        self.card_size = QSize(80, 112)
        
    def _can_accept_card(self, event):
        """Hand typically doesn't accept drops from other zones."""
        return False


class BattlefieldZone(ZoneWidget):
    """Battlefield zone with grid layout for permanents."""
    
    def __init__(self, player_name="Player", parent=None, api=None):
        super().__init__("battlefield", f"{player_name}'s Battlefield", parent, api)
        self.setMinimumHeight(200)
        
        # Track different types of permanents
        self.lands = []
        self.creatures = []
        self.other_permanents = []
        
    def setup_ui(self):
        """Setup battlefield-specific UI."""
        super().setup_ui()
        
        # Remove the default flow layout and create a custom grid
        self.cards_layout.deleteLater()
        
        # Create sections for different permanent types
        battlefield_widget = QWidget()
        battlefield_layout = QVBoxLayout(battlefield_widget)
        
        # Lands row
        self.lands_frame = QFrame()
        self.lands_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
                background: {MTGTheme.BACKGROUND_MEDIUM.name()}20;
                margin: 2px;
            }}
        """)
        self.lands_layout = FlowLayout(self.lands_frame)
        lands_label = QLabel("Lands")
        lands_label.setFont(QFont("Arial", 9, QFont.Bold))
        lands_label.setStyleSheet(f"color: {MTGTheme.TEXT_DISABLED.name()}; border: none; padding: 2px;")
        
        lands_container = QVBoxLayout()
        lands_container.addWidget(lands_label)
        lands_container.addWidget(self.lands_frame)
        battlefield_layout.addLayout(lands_container)
        
        # Creatures row
        self.creatures_frame = QFrame()
        self.creatures_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
                background: {MTGTheme.BACKGROUND_MEDIUM.name()}20;
                margin: 2px;
            }}
        """)
        self.creatures_layout = FlowLayout(self.creatures_frame)
        creatures_label = QLabel("Creatures")
        creatures_label.setFont(QFont("Arial", 9, QFont.Bold))
        creatures_label.setStyleSheet(f"color: {MTGTheme.TEXT_DISABLED.name()}; border: none; padding: 2px;")
        
        creatures_container = QVBoxLayout()
        creatures_container.addWidget(creatures_label)
        creatures_container.addWidget(self.creatures_frame)
        battlefield_layout.addLayout(creatures_container)
        
        # Other permanents row
        self.other_frame = QFrame()
        self.other_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 4px;
                background: {MTGTheme.BACKGROUND_MEDIUM.name()}20;
                margin: 2px;
            }}
        """)
        self.other_layout = FlowLayout(self.other_frame)
        other_label = QLabel("Other Permanents")
        other_label.setFont(QFont("Arial", 9, QFont.Bold))
        other_label.setStyleSheet(f"color: {MTGTheme.TEXT_DISABLED.name()}; border: none; padding: 2px;")
        
        other_container = QVBoxLayout()
        other_container.addWidget(other_label)
        other_container.addWidget(self.other_frame)
        battlefield_layout.addLayout(other_container)
        
        self.scroll_area.setWidget(battlefield_widget)
        
    def add_card(self, card, animated=True):
        """Add a card to the appropriate section of the battlefield."""
        if card in self.cards:
            return
            
        # Create card widget
        card_widget = EnhancedCardWidget(card, api=self.api, parent=self.cards_container)
        card_widget.card_clicked.connect(lambda c: self._on_card_clicked(c))
        card_widget.card_double_clicked.connect(lambda c: self._on_card_double_clicked(c))
        card_widget.card_tapped.connect(lambda c: self._on_card_tapped(c))
        card_widget.ability_activated.connect(lambda c, a: self._on_ability_activated(c, a))
        
        # Determine which section to add to
        card_types = getattr(card, 'types', [])
        if "Land" in card_types:
            self.lands.append(card)
            self.lands_layout.add_card_widget(card_widget)
        elif "Creature" in card_types:
            self.creatures.append(card)
            self.creatures_layout.add_card_widget(card_widget)
            # New creatures have summoning sickness
            card_widget.set_summoning_sick(True)
        else:
            self.other_permanents.append(card)
            self.other_layout.add_card_widget(card_widget)
            
        self.cards.append(card)
        self.card_widgets[getattr(card, 'id', str(id(card)))] = card_widget
        
        if animated:
            self._animate_card_entry(card_widget)
            
        self._update_status()
        self.card_added.emit(card, self.zone_name)
        
    def _can_accept_card(self, event):
        """Battlefield can accept playable permanents."""
        # Would check if the dragged card can be played as a permanent
        return True


class GraveyardZone(ZoneWidget):
    """Graveyard zone showing cards in a stack."""
    
    def __init__(self, player_name="Player", parent=None, api=None):
        super().__init__("graveyard", f"{player_name}'s Graveyard", parent, api)
        self.setMinimumHeight(120)
        self.setMaximumWidth(150)
        
    def setup_ui(self):
        """Setup graveyard-specific UI."""
        super().setup_ui()
        
        # Show only the top card in a stack
        self.setMaximumWidth(120)
        
    def _can_accept_card(self, event):
        """Graveyard typically doesn't accept drops."""
        return False


class EnhancedBattlefieldLayout(QWidget):
    """Complete battlefield layout with all zones for a player."""
    
    card_played = Signal(object)  # card
    card_activated = Signal(object, str)  # card, action
    mana_tapped = Signal(object)  # permanent
    
    def __init__(self, player_name="Player", parent=None, api=None):
        super().__init__(parent)
        self.player_name = player_name
        self.api = api
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the complete battlefield layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        
        # Main battlefield area
        self.battlefield = BattlefieldZone(self.player_name, parent=self, api=self.api)
        layout.addWidget(self.battlefield, 3)  # Takes most space
        
        # Bottom row with hand and other zones
        bottom_layout = QHBoxLayout()
        
        # Hand (takes most of the bottom space)
        self.hand = HandZone(self.player_name, parent=self, api=self.api)
        bottom_layout.addWidget(self.hand, 4)
        
        # Graveyard and other zones
        zones_layout = QVBoxLayout()
        
        self.graveyard = GraveyardZone(self.player_name, parent=self, api=self.api)
        zones_layout.addWidget(self.graveyard)
        
        # Could add exile, command zone, etc.
        
        bottom_layout.addLayout(zones_layout, 1)
        layout.addLayout(bottom_layout, 2)
        
    def connect_signals(self):
        """Connect signals from zones."""
        self.hand.card_activated.connect(self._handle_hand_activation)
        self.battlefield.card_activated.connect(self._handle_battlefield_activation)
        
    def add_card_to_hand(self, card, animated=True):
        """Add a card to the hand."""
        self.hand.add_card(card, animated)
        
    def add_card_to_battlefield(self, card, animated=True):
        """Add a card to the battlefield."""
        self.battlefield.add_card(card, animated)
        
    def add_card_to_graveyard(self, card, animated=True):
        """Add a card to the graveyard."""
        self.graveyard.add_card(card, animated)
        
    def move_card_to_battlefield(self, card, animated=True):
        """Move a card from hand to battlefield."""
        self.hand.remove_card(card, animated=False)  # Remove from hand immediately
        
        # Small delay before adding to battlefield for better visual flow
        if animated:
            QTimer.singleShot(100, lambda: self.battlefield.add_card(card, True))
        else:
            self.battlefield.add_card(card, False)
            
        self.card_played.emit(card)
        
    def tap_permanent(self, card):
        """Tap a permanent on the battlefield."""
        self.battlefield.tap_card(card)
        self.mana_tapped.emit(card)
        
    def untap_all(self):
        """Untap all permanents (start of turn)."""
        self.battlefield.untap_all()
        
        # Remove summoning sickness
        for card in self.battlefield.creatures:
            self.battlefield.set_card_summoning_sick(card, False)
            
    def _handle_hand_activation(self, card, action):
        """Handle card activation from hand."""
        if action == "double_clicked":
            # Try to play the card
            self._try_play_card(card)
        else:
            self.card_activated.emit(card, action)
            
    def _handle_battlefield_activation(self, card, action):
        """Handle card activation from battlefield."""
        self.card_activated.emit(card, action)
        
    def _try_play_card(self, card):
        """Attempt to play a card from hand."""
        if self.api and hasattr(self.api, 'can_play_card'):
            try:
                player = self.api.get_current_player()
                can_play, reason = self.api.can_play_card(card)
                
                if can_play:
                    # For lands, move directly to battlefield
                    if "Land" in getattr(card, 'types', []):
                        self.move_card_to_battlefield(card)
                    else:
                        # For spells, would go through casting system
                        self.api.cast_spell(card)
                else:
                    print(f"Cannot play {card.name}: {reason}")
            except Exception as e:
                print(f"Error playing card: {e}")
