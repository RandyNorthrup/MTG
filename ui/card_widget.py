"""Modern MTG card widget with complete game integration."""

import os
from enum import Enum
from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QMenu, QScrollArea, QGridLayout
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QPoint, QRect, QPropertyAnimation, QEasingCurve, Property, QMimeData, QRectF
from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QFont, QDrag, QCursor, QTransform

from ui.theme import MTGTheme


class CardPreviewWidget(QFrame):
    """Large preview widget for card hover."""
    
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(250, 350)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup preview UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
                border: 2px solid {MTGTheme.BORDER_MEDIUM.name()};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Card name
        name_label = QLabel(getattr(self.card, 'name', 'Unknown Card'))
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {MTGTheme.TEXT_PRIMARY.name()};
                background: transparent;
                border: none;
            }}
        """)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(name_label)
        
        # Mana cost
        if hasattr(self.card, 'mana_cost_str'):
            cost_label = QLabel(getattr(self.card, 'mana_cost_str', ''))
            cost_label.setFont(QFont("Arial", 10))
            cost_label.setStyleSheet(f"""
                QLabel {{
                    color: {MTGTheme.TEXT_SECONDARY.name()};
                    background: transparent;
                    border: none;
                }}
            """)
            cost_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(cost_label)
        
        # Card image (larger)
        image_area = QLabel()
        image_area.setFixedSize(220, 160)
        image_area.setStyleSheet(f"""
            QLabel {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 8px;
            }}
        """)
        image_area.setAlignment(Qt.AlignCenter)
        image_area.setText("🎴")
        image_area.setScaledContents(True)
        layout.addWidget(image_area)
        
        # Card type
        card_types = "/".join(getattr(self.card, 'types', ['Unknown']))
        type_label = QLabel(card_types)
        type_label.setFont(QFont("Arial", 9))
        type_label.setStyleSheet(f"""
            QLabel {{
                color: {MTGTheme.TEXT_PRIMARY.name()};
                background: transparent;
                border: none;
            }}
        """)
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setWordWrap(True)
        layout.addWidget(type_label)
        
        # Power/Toughness for creatures
        if "Creature" in getattr(self.card, 'types', []):
            power = getattr(self.card, 'power', '?')
            toughness = getattr(self.card, 'toughness', '?')
            pt_label = QLabel(f"{power}/{toughness}")
            pt_label.setFont(QFont("Arial", 10, QFont.Bold))
            pt_label.setStyleSheet(f"""
                QLabel {{
                    color: {MTGTheme.TEXT_PRIMARY.name()};
                    background: {MTGTheme.BACKGROUND_MEDIUM.name()};
                    border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-radius: 4px;
                    padding: 2px 6px;
                }}
            """)
            pt_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(pt_label)
        
        # Card text (if available)
        if hasattr(self.card, 'text') and self.card.text:
            text_area = QLabel(self.card.text)
            text_area.setFont(QFont("Arial", 8))
            text_area.setStyleSheet(f"""
                QLabel {{
                    color: {MTGTheme.TEXT_SECONDARY.name()};
                    background: {MTGTheme.BACKGROUND_MEDIUM.name()};
                    border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                    border-radius: 4px;
                    padding: 4px;
                }}
            """)
            text_area.setWordWrap(True)
            text_area.setAlignment(Qt.AlignTop)
            text_area.setMaximumHeight(80)
            layout.addWidget(text_area)
        
        # Try to load card image
        self._load_preview_image(image_area)
    
    def _load_preview_image(self, image_label):
        """Load card image for preview."""
        try:
            card_id = getattr(self.card, 'id', '')
            if card_id:
                from image_cache import ensure_card_image
                image_path = ensure_card_image(card_id)
                if image_path and os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(
                            image_label.size(), 
                            Qt.KeepAspectRatio, 
                            Qt.SmoothTransformation
                        )
                        image_label.setPixmap(scaled)
                        image_label.setText("")
        except Exception as e:
            print(f"Could not load preview image: {e}")


class CardState(Enum):
    """Card visual states."""
    NORMAL = "normal"
    HOVERED = "hovered"
    SELECTED = "selected"
    TAPPED = "tapped"
    SUMMONING_SICK = "summoning_sick"
    ATTACKING = "attacking"
    BLOCKING = "blocking"
    DRAGGING = "dragging"


class InteractiveCardWidget(QFrame):
    """Modern interactive MTG card widget."""
    
    # Signals
    card_clicked = Signal(object)
    card_double_clicked = Signal(object)
    card_right_clicked = Signal(object, QPoint)
    card_hovered = Signal(object, bool)
    card_tapped = Signal(object)
    card_untapped = Signal(object)
    card_drag_started = Signal(object, QPoint)
    card_dropped = Signal(object, str, QPoint)
    ability_activated = Signal(object, str)
    
    def __init__(self, card, size=QSize(100, 140), parent=None, api=None):
        super().__init__(parent)
        self.card = card
        self.api = api
        self.base_size = size
        self._current_scale = 1.0
        self._rotation_angle = 0.0
        
        # State
        self.state = CardState.NORMAL
        self.is_hovered = False
        self.is_selected = False
        self.is_tapped = False
        self.is_summoning_sick = False
        self.is_attacking = False
        self.is_blocking = False
        self.is_dragging = False
        
        # Settings
        self.hover_scale = 1.1
        self.drag_threshold = 8
        self.tap_angle = 90.0
        
        # Mouse tracking
        self.drag_start_pos = QPoint()
        self.mouse_pressed = False
        
        self.setFixedSize(size)
        self.setAcceptDrops(True)
        
        self._setup_ui()
        self._setup_animations()
        self._setup_context_menu()
        
        # Hover timer
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_hover_preview)
        
        # Preview widget reference
        self.preview_widget = None
    
    def _setup_ui(self):
        """Setup the card UI."""
        # Clean card widget with just border and background
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {MTGTheme.BORDER_MEDIUM.name()};
                border-radius: 8px;
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
            }}
        """)
        
        # Simple layout with just the card image filling the entire widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        
        # Card image takes full space
        self.image_area = QLabel()
        self.image_area.setStyleSheet(f"""
            QLabel {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 1px solid {MTGTheme.BORDER_LIGHT.name()};
                border-radius: 6px;
            }}
        """)
        self.image_area.setAlignment(Qt.AlignCenter)
        self.image_area.setText("🎴")
        self.image_area.setScaledContents(True)
        layout.addWidget(self.image_area, 1)
        
        self._load_card_image()
    
    def _setup_animations(self):
        """Setup animations."""
        self.scale_animation = QPropertyAnimation(self, b"current_scale")
        self.scale_animation.setDuration(150)
        self.scale_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.rotation_animation = QPropertyAnimation(self, b"rotation_angle")
        self.rotation_animation.setDuration(300)
        self.rotation_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def _setup_context_menu(self):
        """Setup context menu."""
        self.context_menu = QMenu(self)
        
        self.context_menu.addAction("Inspect Card", self._show_card_details)
        
        if self.card and hasattr(self.card, 'text') and self.card.text:
            self.context_menu.addSeparator()
            
            if "{T}:" in self.card.text:
                self.context_menu.addAction("Tap for ability", self._activate_tap_ability)
                
            if "Land" in getattr(self.card, 'types', []):
                self.context_menu.addAction("Tap for mana", self._tap_for_mana)
                
            if "Creature" in getattr(self.card, 'types', []) and not self.is_summoning_sick:
                self.context_menu.addAction("Attack", self._declare_attacker)
    
    def _load_card_image(self):
        """Load card image if available."""
        try:
            if hasattr(self, 'api') and self.api:
                card_id = getattr(self.card, 'id', '')
                if card_id:
                    from image_cache import ensure_card_image
                    image_path = ensure_card_image(card_id)
                    if image_path and os.path.exists(image_path):
                        pixmap = QPixmap(image_path)
                        if not pixmap.isNull():
                            scaled = pixmap.scaled(
                                self.image_area.size(), 
                                Qt.KeepAspectRatio, 
                                Qt.SmoothTransformation
                            )
                            self.image_area.setPixmap(scaled)
                            self.image_area.setText("")
        except Exception as e:
            print(f"Could not load image for {getattr(self.card, 'name', 'card')}: {e}")
    
    # Properties for animations
    @Property(float)
    def current_scale(self):
        return self._current_scale
    
    @current_scale.setter
    def current_scale(self, value):
        self._current_scale = value
        self.update()
        
    @Property(float) 
    def rotation_angle(self):
        return self._rotation_angle
        
    @rotation_angle.setter
    def rotation_angle(self, value):
        self._rotation_angle = value
        self.update()
    
    def paintEvent(self, event):
        """Custom paint with transformations."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Apply transformations
        center = QRectF(self.rect()).center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.scale(self.current_scale, self.current_scale)
        transform.rotate(self.rotation_angle)
        transform.translate(-center.x(), -center.y())
        painter.setTransform(transform)
        
        # Draw state indicators
        self._draw_state_indicators(painter)
        
        # Reset transform for child widgets
        painter.setTransform(QTransform())
        super().paintEvent(event)
    
    def _draw_state_indicators(self, painter):
        """Draw visual state indicators."""
        rect = QRectF(self.rect())
        
        # Hover highlight - subtle glow
        if self.is_hovered and not self.is_dragging:
            painter.setBrush(QBrush())
            painter.setPen(QPen(MTGTheme.HOVER_HIGHLIGHT, 2))
            painter.drawRoundedRect(rect.adjusted(0, 0, 0, 0), 8, 8)
            
        # Selection highlight - bright border
        if self.is_selected:
            painter.setBrush(QBrush())
            painter.setPen(QPen(QColor(0, 150, 255), 3))
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 8, 8)
            
        # Summoning sickness overlay - yellow tint
        if self.is_summoning_sick:
            painter.setBrush(QBrush(QColor(255, 255, 0, 40)))
            painter.setPen(QPen(QColor(255, 255, 0, 120), 1))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
            
        # Attacking state - red glow
        if self.is_attacking:
            painter.setBrush(QBrush(QColor(255, 100, 100, 60)))
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 8, 8)
            
        # Blocking state - blue glow
        if self.is_blocking:
            painter.setBrush(QBrush(QColor(100, 100, 255, 60)))
            painter.setPen(QPen(QColor(0, 0, 255), 3))
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 8, 8)
            
        # Dragging state - semi-transparent overlay
        if self.is_dragging:
            painter.setBrush(QBrush(QColor(255, 255, 255, 100)))
            painter.setPen(QPen())
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 8, 8)
    
    # Event handlers
    def enterEvent(self, event):
        """Handle mouse enter."""
        if not self.is_dragging:
            self.is_hovered = True
            self.card_hovered.emit(self.card, True)
            self._animate_scale(self.hover_scale)
            self.hover_timer.start(500)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self.is_hovered = False
        self.card_hovered.emit(self.card, False)
        self.hover_timer.stop()
        
        # Force hide preview if it exists
        self._hide_preview()
        
        if not self.is_dragging:
            self._animate_scale(1.0)
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            self.drag_start_pos = event.pos()
            self.is_selected = True
            self.update()
            
        elif event.button() == Qt.RightButton:
            global_pos = self.mapToGlobal(event.pos())
            self.card_right_clicked.emit(self.card, global_pos)
            self.context_menu.exec(global_pos)
            
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move."""
        if (event.buttons() & Qt.LeftButton and self.mouse_pressed and
            (event.pos() - self.drag_start_pos).manhattanLength() > self.drag_threshold):
            
            self._start_drag(event)
            
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = False
            
            if not self.is_dragging:
                self.card_clicked.emit(self.card)
                
        super().mouseReleaseEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        """Handle double-click."""
        if event.button() == Qt.LeftButton:
            self.card_double_clicked.emit(self.card)
            
            # Default actions
            if self._can_play_card():
                self._play_card()
            elif self._can_tap_for_mana():
                self._tap_for_mana()
                
        super().mouseDoubleClickEvent(event)
    
    def _start_drag(self, event):
        """Start drag operation."""
        self.is_dragging = True
        self.state = CardState.DRAGGING
        
        # Hide any preview before starting drag
        self._hide_preview()
        
        # Notify parent window about drag start for target highlighting
        self._notify_drag_start()
        
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Add card data and type info for smart targeting
        card_id = getattr(self.card, 'id', '')
        card_types = getattr(self.card, 'types', [])
        
        mime_data.setText(f"card:{card_id}")
        mime_data.setData("application/mtg-card", card_id.encode() if card_id else b"")
        mime_data.setData("application/mtg-card-types", "|".join(card_types).encode())
        drag.setMimeData(mime_data)
        
        # Create drag pixmap
        try:
            drag_pixmap = QPixmap(self.size())
            drag_pixmap.fill(Qt.transparent)
            painter = QPainter(drag_pixmap)
            painter.setOpacity(0.8)
            self.render(painter, QPoint(), self.rect())
            painter.end()
        except Exception as e:
            print(f"Error creating drag pixmap: {e}")
            # Create a simple fallback pixmap
            drag_pixmap = QPixmap(80, 112)
            drag_pixmap.fill(Qt.gray)
        
        drag.setPixmap(drag_pixmap.scaled(80, 112, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(QPoint(40, 56))
        
        self.card_drag_started.emit(self.card, self.mapToGlobal(event.pos()))
        
        try:
            result = drag.exec(Qt.MoveAction | Qt.CopyAction)
        except Exception as e:
            print(f"Drag operation failed: {e}")
            result = Qt.IgnoreAction
        
        # Drag finished - safely clean up
        try:
            self.is_dragging = False
            self.state = CardState.NORMAL
            self.is_selected = False
            
            # Notify parent window about drag end
            self._notify_drag_end()
            
            self.update()
        except RuntimeError as e:
            # Widget was deleted during drag operation
            if "Internal C++ object" in str(e) and "already deleted" in str(e):
                return  # Widget no longer exists, safe to exit
            else:
                print(f"Error cleaning up after drag: {e}")
        except Exception as e:
            print(f"Unexpected error during drag cleanup: {e}")
    
    def _animate_scale(self, target_scale):
        """Animate scaling."""
        self.scale_animation.stop()
        self.scale_animation.setStartValue(self.current_scale)
        self.scale_animation.setEndValue(target_scale)
        self.scale_animation.start()
    
    # Public methods
    def tap_card(self, animated=True):
        """Tap the card."""
        if self.is_tapped:
            return
            
        self.is_tapped = True
        self.card_tapped.emit(self.card)
        
        if animated:
            self.rotation_animation.stop()
            self.rotation_animation.setStartValue(self.rotation_angle)
            self.rotation_animation.setEndValue(self.tap_angle)
            self.rotation_animation.start()
        else:
            self.rotation_angle = self.tap_angle
            self.update()
            
    def untap_card(self, animated=True):
        """Untap the card."""
        if not self.is_tapped:
            return
            
        self.is_tapped = False
        self.card_untapped.emit(self.card)
        
        if animated:
            self.rotation_animation.stop()
            self.rotation_animation.setStartValue(self.rotation_angle)
            self.rotation_animation.setEndValue(0.0)
            self.rotation_animation.start()
        else:
            self.rotation_angle = 0.0
            self.update()
    
    def set_summoning_sick(self, sick=True):
        """Set summoning sickness state."""
        self.is_summoning_sick = sick
        self.update()
        
    def set_attacking(self, attacking=True):
        """Set attacking state."""
        self.is_attacking = attacking
        self.update()
        
    def set_blocking(self, blocking=True):
        """Set blocking state."""
        self.is_blocking = blocking
        self.update()
    
    def closeEvent(self, event):
        """Handle widget cleanup on close."""
        self._hide_preview()
        if hasattr(self, 'hover_timer'):
            self.hover_timer.stop()
        super().closeEvent(event)
    
    def __del__(self):
        """Cleanup on destruction."""
        try:
            self._hide_preview()
        except:
            pass
    
    # Private action methods
    def _show_hover_preview(self):
        """Show hover preview."""
        if not self.card or self.is_dragging or not self.is_hovered:
            return
        
        # Clean up any existing preview first
        self._hide_preview()
        
        try:
            # Create preview window
            self.preview_widget = CardPreviewWidget(self.card, parent=self.window())
            
            # Position preview near the card but not overlapping
            card_global_pos = self.mapToGlobal(self.pos())
            preview_x = card_global_pos.x() + self.width() + 10
            preview_y = card_global_pos.y()
            
            # Adjust if preview would go off screen
            screen_geometry = self.screen().geometry()
            if preview_x + self.preview_widget.width() > screen_geometry.right():
                preview_x = card_global_pos.x() - self.preview_widget.width() - 10
                
            if preview_y + self.preview_widget.height() > screen_geometry.bottom():
                preview_y = screen_geometry.bottom() - self.preview_widget.height()
                
            self.preview_widget.move(preview_x, preview_y)
            self.preview_widget.show()
            
        except Exception as e:
            print(f"Error showing card preview: {e}")
            self._hide_preview()
    
    def _hide_preview(self):
        """Hide and cleanup hover preview."""
        try:
            if hasattr(self, 'preview_widget') and self.preview_widget:
                self.preview_widget.hide()
                self.preview_widget.deleteLater()
                self.preview_widget = None
        except Exception as e:
            print(f"Error hiding card preview: {e}")
            # Force cleanup
            self.preview_widget = None
        
    def _show_card_details(self):
        """Show card details."""
        if self.api and hasattr(self.api, 'show_card_details'):
            self.api.show_card_details(self.card)
    
    def _can_play_card(self):
        """Check if card can be played."""
        if not self.api:
            return False
            
        try:
            player = self.api.get_current_player()
            if hasattr(self.api, 'controller') and hasattr(self.api.controller, 'can_play_card'):
                can_play, _ = self.api.controller.can_play_card(player, self.card)
                return can_play
        except:
            pass
            
        return False
        
    def _play_card(self):
        """Play the card."""
        if self.api and hasattr(self.api, 'play_card'):
            self.api.play_card(self.card)
            
    def _can_tap_for_mana(self):
        """Check if card can tap for mana."""
        return (not self.is_tapped and 
                "Land" in getattr(self.card, 'types', []) and
                hasattr(self.card, 'text') and
                any(color in self.card.text.upper() for color in ['W', 'U', 'B', 'R', 'G', 'C']))
        
    def _tap_for_mana(self):
        """Tap for mana."""
        if self._can_tap_for_mana() and self.api:
            try:
                player = self.api.get_current_player()
                if hasattr(player, 'battlefield'):
                    for perm in player.battlefield:
                        if hasattr(perm, 'card') and perm.card == self.card:
                            success = self.api.tap_for_mana(player, perm)
                            if success:
                                self.tap_card()
                            break
            except Exception as e:
                print(f"Error tapping for mana: {e}")
                
    def _activate_tap_ability(self):
        """Activate tap ability."""
        if not self.is_tapped and hasattr(self.card, 'text') and "{T}:" in self.card.text:
            self.ability_activated.emit(self.card, "tap_ability")
            self.tap_card()
            
    def _declare_attacker(self):
        """Declare as attacker."""
        if ("Creature" in getattr(self.card, 'types', []) and 
            not self.is_summoning_sick and not self.is_tapped):
            
            self.set_attacking(True)
    
    def _notify_drag_start(self):
        """Notify parent widgets about drag start."""
        try:
            # Find the game board window
            parent = self.parent()
            while parent and not hasattr(parent, 'highlight_valid_drop_targets'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'highlight_valid_drop_targets'):
                card_types = getattr(self.card, 'types', [])
                parent.highlight_valid_drop_targets(card_types, True)
        except Exception as e:
            print(f"Error notifying drag start: {e}")
    
    def _notify_drag_end(self):
        """Notify parent widgets about drag end."""
        try:
            # Find the game board window
            parent = self.parent()
            while parent and not hasattr(parent, 'highlight_valid_drop_targets'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'highlight_valid_drop_targets'):
                parent.highlight_valid_drop_targets([], False)
        except Exception as e:
            print(f"Error notifying drag end: {e}")


class CardContainer(QScrollArea):
    """Modern container for multiple cards with drag-drop support."""
    
    card_added = Signal(object)
    card_removed = Signal(object)
    
    def __init__(self, zone_name="Cards", allow_drops=True, parent=None):
        super().__init__(parent)
        self.zone_name = zone_name
        self.allow_drops = allow_drops
        self.cards = []
        self.card_widgets = []
        
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.container = QWidget()
        self.layout = QGridLayout(self.container)
        self.layout.setSpacing(6)
        self.layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.setWidget(self.container)
        
        self.setStyleSheet(f"""
            QScrollArea {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 2px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 8px;
            }}
            QScrollArea QWidget {{
                background: transparent;
            }}
        """)
        
        if allow_drops:
            self.setAcceptDrops(True)
    
    def add_card(self, card, position=None):
        """Add a card to the container."""
        if position is None:
            position = len(self.cards)
            
        self.cards.insert(position, card)
        
        card_widget = InteractiveCardWidget(card)
        card_widget.card_clicked.connect(lambda c: self._on_card_clicked(c, card_widget))
        card_widget.card_double_clicked.connect(lambda c: self._on_card_double_clicked(c, card_widget))
        
        self.card_widgets.insert(position, card_widget)
        
        self._refresh_layout()
        self.card_added.emit(card)
    
    def remove_card(self, card):
        """Remove a card from the container."""
        if card in self.cards:
            index = self.cards.index(card)
            self.cards.remove(card)
            
            widget = self.card_widgets.pop(index)
            widget.deleteLater()
            
            self._refresh_layout()
            self.card_removed.emit(card)
    
    def clear_cards(self):
        """Clear all cards."""
        self.cards.clear()
        for widget in self.card_widgets:
            widget.deleteLater()
        self.card_widgets.clear()
        self._refresh_layout()
    
    def _refresh_layout(self):
        """Refresh the layout."""
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if item:
                self.layout.removeItem(item)
                
        cols = max(1, self.width() // 100)
        for i, widget in enumerate(self.card_widgets):
            row = i // cols
            col = i % cols
            self.layout.addWidget(widget, row, col)
    
    def _on_card_clicked(self, card, widget):
        """Handle card click."""
        for w in self.card_widgets:
            if w != widget:
                w.is_selected = False
                w.update()
                
        widget.is_selected = not widget.is_selected
        widget.update()
    
    def _on_card_double_clicked(self, card, widget):
        """Handle card double click."""
        pass
    
    def dragEnterEvent(self, event):
        """Handle drag enter."""
        if self.allow_drops and event.mimeData().hasFormat("application/mtg-card"):
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Handle drop."""
        if self.allow_drops and event.mimeData().hasFormat("application/mtg-card"):
            event.acceptProposedAction()


def create_card_widget(card, size=QSize(100, 140), api=None):
    """Factory function to create a card widget."""
    return InteractiveCardWidget(card, size, api=api)


def create_card_container(zone_name="Cards", allow_drops=True):
    """Factory function to create a card container."""
    return CardContainer(zone_name, allow_drops)
