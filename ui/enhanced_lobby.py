"""Enhanced lobby interface for MTG Commander.

Modern lobby system matching professional Magic: The Gathering interfaces
with player avatars, deck selection, match queuing, and visual polish.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QSplitter, QGroupBox,
    QScrollArea, QFrame, QGridLayout, QComboBox, QProgressBar,
    QStackedWidget, QTextEdit
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QFont, QPainterPath

from ui.theme import (
    MTGTheme, PRIMARY_BUTTON_STYLE, SUCCESS_BUTTON_STYLE, 
    DANGER_BUTTON_STYLE, LIST_STYLE, GROUP_BOX_STYLE, INPUT_STYLE
)
from ui.player_preferences import get_player_preferences

class PlayerAvatar(QWidget):
    """Modern player avatar widget with status indicators."""
    
    def __init__(self, player_name="", is_ready=False, is_ai=False, avatar_index=0, parent=None):
        super().__init__(parent)
        self.player_name = player_name
        self.is_ready = is_ready
        self.is_ai = is_ai
        self.avatar_index = avatar_index
        self.avatar_pixmap = None
        self.load_avatar()
        self.setFixedSize(120, 140)
        
    def set_player_info(self, name, is_ready=False, is_ai=False, avatar_index=None):
        """Update player information."""
        self.player_name = name
        self.is_ready = is_ready
        self.is_ai = is_ai
        if avatar_index is not None and avatar_index != self.avatar_index:
            self.avatar_index = avatar_index
            self.load_avatar()
        self.update()
    
    def load_avatar(self):
        """Load the avatar image for this player."""
        try:
            prefs = get_player_preferences()
            avatar_path = prefs.get_avatar_path(self.avatar_index)
            if os.path.exists(avatar_path):
                self.avatar_pixmap = QPixmap(avatar_path)
            else:
                self.avatar_pixmap = None
        except Exception as e:
            print(f"Error loading avatar: {e}")
            self.avatar_pixmap = None
        
    def paintEvent(self, event):
        """Custom paint for avatar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        if self.player_name:
            bg_color = MTGTheme.BACKGROUND_LIGHT if not self.is_ai else QColor(40, 60, 40)
            if self.is_ready:
                bg_color = MTGTheme.SUCCESS if not self.is_ai else QColor(60, 120, 60)
        else:
            bg_color = MTGTheme.BACKGROUND_MEDIUM
            
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(MTGTheme.BORDER_LIGHT, 2))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)
        
        # Avatar rectangle (not circle)
        avatar_rect = self.rect().adjusted(20, 15, -20, -50)
        
        # Draw avatar background
        painter.setBrush(QBrush(MTGTheme.HOVER_HIGHLIGHT if self.player_name else MTGTheme.BACKGROUND_DARK))
        painter.setPen(QPen(MTGTheme.BORDER_DARK, 2))
        painter.drawRoundedRect(avatar_rect, 8, 8)  # Rounded rectangle instead of circle
        
        # Draw avatar image or fallback
        if self.avatar_pixmap and not self.avatar_pixmap.isNull() and self.player_name:
            # Scale and draw the avatar image to fit the rectangle
            scaled_pixmap = self.avatar_pixmap.scaled(
                avatar_rect.size().width() - 4,  # Account for border
                avatar_rect.size().height() - 4, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            # Center the scaled image
            offset_x = (avatar_rect.width() - scaled_pixmap.width()) // 2
            offset_y = (avatar_rect.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(avatar_rect.x() + offset_x, avatar_rect.y() + offset_y, scaled_pixmap)
        else:
            # Draw initials or placeholder text on solid background
            if self.player_name:
                painter.setPen(QPen(MTGTheme.TEXT_PRIMARY))
                painter.setFont(QFont("Arial", 20, QFont.Bold))
                initials = "".join(word[0].upper() for word in self.player_name.split()[:2])
                painter.drawText(avatar_rect, Qt.AlignCenter, initials)
            else:
                painter.setPen(QPen(MTGTheme.TEXT_DISABLED))
                painter.setFont(QFont("Arial", 24))
                painter.drawText(avatar_rect, Qt.AlignCenter, "+")
            
        # Name and status
        name_rect = self.rect().adjusted(5, 95, -5, -25)
        painter.setPen(QPen(MTGTheme.TEXT_PRIMARY if self.player_name else MTGTheme.TEXT_DISABLED))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        display_name = self.player_name if self.player_name else "Empty Slot"
        painter.drawText(name_rect, Qt.AlignCenter | Qt.TextWordWrap, display_name)
        
        # Status indicator
        status_rect = self.rect().adjusted(5, 115, -5, -5)
        if self.player_name:
            if self.is_ai:
                status_text = "AI Ready" if self.is_ready else "AI Player"
                status_color = MTGTheme.INFO
            else:
                status_text = "Ready" if self.is_ready else "Not Ready"
                status_color = MTGTheme.SUCCESS if self.is_ready else MTGTheme.WARNING
        else:
            status_text = "Waiting..."
            status_color = MTGTheme.TEXT_DISABLED
            
        painter.setPen(QPen(status_color))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(status_rect, Qt.AlignCenter, status_text)

class DeckSelector(QWidget):
    """Deck selection widget with preview."""
    
    deck_changed = Signal(str)  # Emits deck path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_deck = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the deck selector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Deck selection header
        header = QLabel("Select Your Deck")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        header.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()};")
        layout.addWidget(header)
        
        # Deck dropdown
        self.deck_combo = QComboBox()
        self.deck_combo.setStyleSheet(INPUT_STYLE)
        self.deck_combo.currentTextChanged.connect(self.on_deck_selected)
        layout.addWidget(self.deck_combo)
        
        # Deck preview
        preview_group = QGroupBox("Deck Preview")
        preview_group.setStyleSheet(GROUP_BOX_STYLE)
        preview_layout = QVBoxLayout(preview_group)
        
        # Commander preview
        self.commander_label = QLabel("Commander: Not Selected")
        self.commander_label.setStyleSheet(f"color: {MTGTheme.TEXT_SECONDARY.name()}; font-weight: bold;")
        preview_layout.addWidget(self.commander_label)
        
        # Deck stats
        self.stats_label = QLabel("Total Cards: 0")
        self.stats_label.setStyleSheet(f"color: {MTGTheme.TEXT_SECONDARY.name()};")
        preview_layout.addWidget(self.stats_label)
        
        # Deck list preview
        self.deck_list = QListWidget()
        self.deck_list.setStyleSheet(LIST_STYLE)
        self.deck_list.setMaximumHeight(200)
        preview_layout.addWidget(self.deck_list)
        
        layout.addWidget(preview_group)
        
        # Refresh decks
        self.refresh_decks()
        
    def refresh_decks(self):
        """Refresh available decks from the decks directory."""
        self.deck_combo.clear()
        decks_dir = os.path.join('data', 'decks')
        
        if os.path.exists(decks_dir):
            deck_files = [f for f in os.listdir(decks_dir) if f.endswith('.txt')]
            for deck_file in sorted(deck_files):
                self.deck_combo.addItem(deck_file[:-4])  # Remove .txt extension
                
    def on_deck_selected(self, deck_name):
        """Handle deck selection."""
        if not deck_name:
            return
            
        deck_path = os.path.join('data', 'decks', f'{deck_name}.txt')
        if os.path.exists(deck_path):
            self.current_deck = deck_path
            self.load_deck_preview(deck_path)
            self.deck_changed.emit(deck_path)
            
    def load_deck_preview(self, deck_path):
        """Load and display deck preview."""
        try:
            with open(deck_path, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                
            commander = None
            cards = []
            
            # Parse deck file - commander is typically the last non-empty line or marked with 'Commander:'
            for line in lines:
                if line.startswith('Commander:'):
                    commander = line.split(':', 1)[-1].strip()
                elif line and not line.startswith('#'):  # Skip comments
                    cards.append(line)
            
            # If no explicit commander found, check if last line is a single card (likely commander)
            if not commander and cards:
                last_line = cards[-1]
                # Check if last line starts with "1 " (single card)
                if last_line.startswith('1 '):
                    commander = last_line.split(' ', 1)[-1] if ' ' in last_line else last_line
                    cards = cards[:-1]  # Remove commander from cards list
                    
            # Update commander display
            if commander:
                self.commander_label.setText(f"Commander: {commander}")
                self.commander_label.setStyleSheet(f"color: {MTGTheme.SUCCESS.name()}; font-weight: bold;")
            else:
                self.commander_label.setText("Commander: Not Found")
                self.commander_label.setStyleSheet(f"color: {MTGTheme.DANGER.name()}; font-weight: bold;")
                
            # Update stats
            total_cards = len(cards) + (1 if commander else 0)
            self.stats_label.setText(f"Total Cards: {total_cards}")
            
            # Update deck list preview (show first 20 cards)
            self.deck_list.clear()
            for i, card in enumerate(cards[:20]):
                item = QListWidgetItem(card)
                self.deck_list.addItem(item)
                
            if len(cards) > 20:
                more_item = QListWidgetItem(f"... and {len(cards) - 20} more cards")
                more_item.setForeground(MTGTheme.TEXT_DISABLED)
                self.deck_list.addItem(more_item)
                
        except Exception as e:
            self.commander_label.setText("Commander: Error Loading Deck")
            self.commander_label.setStyleSheet(f"color: {MTGTheme.DANGER.name()}; font-weight: bold;")
            self.stats_label.setText("Total Cards: Error")
            self.deck_list.clear()

class EnhancedLobby(QWidget):
    """Enhanced lobby interface matching professional MTG design."""
    
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.current_match_id = None
        self.player_avatars = []  # Initialize empty list for safety
        self.setup_ui()
        
        # Auto-refresh timer with delayed start
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_lobby_state)
        # Start timer after a short delay to ensure everything is initialized
        QTimer.singleShot(2000, lambda: self.refresh_timer.start(2000))  # Start after 2s, refresh every 2s
        
    def setup_ui(self):
        """Setup the enhanced lobby UI."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Create main sections
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Match browser and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Center panel - Current match lobby
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)
        
        # Right panel - Deck selection
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)  # Left: 25%
        splitter.setStretchFactor(1, 2)  # Center: 50%  
        splitter.setStretchFactor(2, 1)  # Right: 25%
        
        main_layout.addWidget(splitter)
        
    def create_left_panel(self):
        """Create the left panel with match browser."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Available Matches")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()}; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Match listings scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 6px;
            }}
        """)
        
        self.matches_container = QWidget()
        self.matches_layout = QVBoxLayout(self.matches_container)
        self.matches_layout.addStretch()
        
        scroll_area.setWidget(self.matches_container)
        layout.addWidget(scroll_area)
        
        # Action buttons
        btn_layout = QVBoxLayout()
        
        self.create_match_btn = QPushButton("Create New Match")
        self.create_match_btn.setStyleSheet(SUCCESS_BUTTON_STYLE)
        self.create_match_btn.clicked.connect(self.create_match)
        btn_layout.addWidget(self.create_match_btn)
        
        self.refresh_btn = QPushButton("Refresh Matches")
        self.refresh_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.refresh_btn.clicked.connect(self.refresh_matches)
        btn_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(btn_layout)
        
        return panel
        
    def create_center_panel(self):
        """Create the center panel with current match lobby."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Match title
        self.match_title = QLabel("No Active Match")
        self.match_title.setFont(QFont("Arial", 18, QFont.Bold))
        self.match_title.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()}; margin-bottom: 15px;")
        layout.addWidget(self.match_title)
        
        # Player slots
        players_group = QGroupBox("Players")
        players_group.setStyleSheet(GROUP_BOX_STYLE)
        players_layout = QGridLayout(players_group)
        
        # Create 4 player avatar slots
        self.player_avatars = []
        for i in range(4):
            avatar = PlayerAvatar()
            players_layout.addWidget(avatar, i // 2, i % 2)
            self.player_avatars.append(avatar)
            
        layout.addWidget(players_group)
        
        # Match controls
        controls_layout = QHBoxLayout()
        
        self.add_ai_btn = QPushButton("Add AI Player")
        self.add_ai_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.add_ai_btn.clicked.connect(self.add_ai_player)
        self.add_ai_btn.setEnabled(False)
        controls_layout.addWidget(self.add_ai_btn)
        
        self.start_game_btn = QPushButton("Start Game")
        self.start_game_btn.setStyleSheet(SUCCESS_BUTTON_STYLE)
        self.start_game_btn.clicked.connect(self.start_game)
        self.start_game_btn.setEnabled(False)
        controls_layout.addWidget(self.start_game_btn)
        
        self.leave_match_btn = QPushButton("Leave Match")
        self.leave_match_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        self.leave_match_btn.clicked.connect(self.leave_match)
        self.leave_match_btn.setEnabled(False)
        controls_layout.addWidget(self.leave_match_btn)
        
        layout.addLayout(controls_layout)
        
        # Match status/chat area
        status_group = QGroupBox("Match Status")
        status_group.setStyleSheet(GROUP_BOX_STYLE)
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setStyleSheet(f"""
            QTextEdit {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 4px;
                color: {MTGTheme.TEXT_SECONDARY.name()};
                font-family: 'Courier New';
                font-size: 11px;
            }}
        """)
        self.status_text.setMaximumHeight(120)
        self.status_text.setReadOnly(True)
        self.status_text.append("Welcome to MTG Commander Lobby!")
        self.status_text.append("Create or join a match to begin playing.")
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(status_group)
        
        return panel
        
    def create_right_panel(self):
        """Create the right panel with deck selection."""
        self.deck_selector = DeckSelector()
        self.deck_selector.deck_changed.connect(self.on_deck_changed)
        return self.deck_selector
        
    # Event handlers
    def create_match(self):
        """Create a new match."""
        if hasattr(self.ctx, 'create_pending_match'):
            self.ctx.create_pending_match()
            self.current_match_id = "local_match"  # Simple ID for local matches
            self.match_title.setText("Local Match - Waiting for Players")
            self.update_ui_state()
            self.log_status("Created new local match")
            
    def add_ai_player(self):
        """Add an AI player to current match."""
        if hasattr(self.ctx, 'add_ai_player_pending'):
            self.ctx.add_ai_player_pending()
            self.log_status("Added AI player to match")
            
    def start_game(self):
        """Start the current match."""
        if hasattr(self.ctx, 'start_pending_match'):
            self.ctx.start_pending_match()
            self.log_status("Starting game...")
            
    def leave_match(self):
        """Leave the current match."""
        if hasattr(self.ctx, 'cancel_pending_match'):
            self.ctx.cancel_pending_match()
            self.current_match_id = None
            self.match_title.setText("No Active Match")
            self.update_ui_state()
            self.log_status("Left match")
            
    def refresh_matches(self):
        """Refresh the matches list."""
        # Clear current matches
        for i in reversed(range(self.matches_layout.count() - 1)):  # Keep stretch at end
            item = self.matches_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
                
        # Add placeholder matches (in a real implementation, this would fetch from server)
        # For now, just show that matches can be displayed
        if not self.current_match_id:
            no_matches = QLabel("No matches available\nCreate a new match to start playing")
            no_matches.setAlignment(Qt.AlignCenter)
            no_matches.setStyleSheet(f"color: {MTGTheme.TEXT_DISABLED.name()}; padding: 20px;")
            self.matches_layout.insertWidget(0, no_matches)
            
    def on_deck_changed(self, deck_path):
        """Handle deck selection change."""
        # Update the game state with selected deck
        # This would typically involve reloading the player's deck
        self.log_status(f"Selected deck: {os.path.basename(deck_path)}")
        
    def log_status(self, message):
        """Add a status message to the status area."""
        self.status_text.append(f"> {message}")
        # Auto-scroll to bottom
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def update_ui_state(self):
        """Update UI state based on current match status."""
        has_match = self.current_match_id is not None
        
        # Update button states
        self.create_match_btn.setEnabled(not has_match)
        self.add_ai_btn.setEnabled(has_match)
        self.leave_match_btn.setEnabled(has_match)
        
        # Update start button based on player count
        if has_match and hasattr(self.ctx, 'game') and self.ctx.game is not None:
            player_count = len(self.ctx.game.players) if hasattr(self.ctx.game, 'players') and self.ctx.game.players else 0
            self.start_game_btn.setEnabled(player_count >= 2)
        else:
            self.start_game_btn.setEnabled(False)
            
    def refresh_lobby_state(self):
        """Refresh the lobby state periodically."""
        try:
            # Ensure player_avatars list exists
            if not hasattr(self, 'player_avatars') or not self.player_avatars:
                return
            
            # Safely check for game and players
            if (hasattr(self.ctx, 'game') and 
                self.ctx.game is not None and 
                hasattr(self.ctx.game, 'players') and 
                self.ctx.game.players):
                
                # Update player avatars
                for i, avatar in enumerate(self.player_avatars):
                    if i < len(self.ctx.game.players):
                        player = self.ctx.game.players[i]
                        is_ai = (hasattr(self.ctx, 'controller') and 
                                self.ctx.controller is not None and
                                hasattr(self.ctx.controller, 'ai_controllers') and
                                hasattr(player, 'player_id') and
                                player.player_id in self.ctx.controller.ai_controllers)
                        
                        # Determine avatar index
                        prefs = get_player_preferences()
                        if i == 0 and not is_ai:  # First player (human)
                            avatar_index = prefs.get_player_avatar()
                        else:  # AI players get assigned different avatars
                            avatar_index = (i + 1) % 5  # Cycle through available avatars
                            
                        avatar.set_player_info(player.name, True, is_ai, avatar_index)
                    else:
                        avatar.set_player_info("", False, False, 0)
            else:
                # No valid game state, clear all avatars
                for avatar in self.player_avatars:
                    avatar.set_player_info("", False, False, 0)
                    
        except (AttributeError, TypeError, IndexError) as e:
            # Handle any remaining errors gracefully
            print(f"Enhanced lobby state refresh error (safe to ignore): {e}")
            # Clear all avatars on error if they exist
            if hasattr(self, 'player_avatars') and self.player_avatars:
                for avatar in self.player_avatars:
                    try:
                        avatar.set_player_info("", False, False, 0)
                    except Exception:
                        pass  # Ignore any errors in cleanup
                
        self.update_ui_state()
        
    def sync_pending_controls(self, active):
        """Sync with the existing lobby system."""
        if active:
            self.current_match_id = "local_match"
            self.match_title.setText("Local Match - Setting Up")
        else:
            self.current_match_id = None
            self.match_title.setText("No Active Match")
            
        self.update_ui_state()

def build_enhanced_play_stack(ctx):
    """Build the enhanced play stack with modern lobby."""
    stack = QStackedWidget()
    
    # Enhanced lobby
    enhanced_lobby = EnhancedLobby(ctx)
    stack.addWidget(enhanced_lobby)
    
    # Game info panel (shown when game is active)
    game_info = QWidget()
    layout = QVBoxLayout(game_info)
    layout.setContentsMargins(40, 40, 40, 40)
    
    title = QLabel("Game In Progress")
    title.setFont(QFont("Arial", 24, QFont.Bold))
    title.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()}; margin-bottom: 20px;")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    
    desc = QLabel(
        "Your MTG Commander game is running in a separate window.\n\n"
        "Use the game window to play, and return here when the game is complete."
    )
    desc.setFont(QFont("Arial", 14))
    desc.setStyleSheet(f"color: {MTGTheme.TEXT_SECONDARY.name()}; line-height: 1.4;")
    desc.setAlignment(Qt.AlignCenter)
    desc.setWordWrap(True)
    layout.addWidget(desc)
    
    layout.addStretch()
    stack.addWidget(game_info)
    
    # Set initial view
    stack.setCurrentIndex(0)
    
    # Connect to existing window system
    if hasattr(ctx, 'w'):
        setattr(ctx.w, 'lobby_widget', enhanced_lobby)
        
    return stack, enhanced_lobby
