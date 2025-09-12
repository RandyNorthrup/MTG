"""MTG Debug Window - Development and troubleshooting interface.

Provides comprehensive game state inspection, manual controls,
and real-time monitoring for development and debugging.
"""

import json
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

class DebugWindow(QMainWindow):
    """Comprehensive debug window for MTG game development.
    
    Features:
    - Real-time game state monitoring
    - Player information and statistics
    - Phase/turn manual control
    - Action simulation and testing
    - Console output and logging
    
    Accessed via F9 key during gameplay.
    """
    
    def __init__(self, api, parent=None):
        """Initialize debug window.
        
        Args:
            api: GameAppAPI instance for game state access
            parent: Parent window (usually MainWindow)
        """
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("MTG Debug Console")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Styling
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QTabWidget::pane { border: 1px solid #555; background-color: #2b2b2b; }
            QTabBar::tab { 
                background-color: #3c3c3c; 
                color: #ddd; 
                padding: 8px 16px; 
                margin: 2px;
                border: 1px solid #555;
            }
            QTabBar::tab:selected { 
                background-color: #4a4a4a; 
                color: #fff;
                border-bottom: 2px solid #0078d4;
            }
            QTextEdit, QListWidget, QTableWidget { 
                background-color: #1e1e1e; 
                color: #ddd; 
                border: 1px solid #555; 
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QLabel { color: #ddd; }
            QPushButton { 
                background-color: #0078d4; 
                color: white; 
                border: none; 
                padding: 6px 12px; 
                border-radius: 3px; 
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
            QGroupBox { 
                color: #ddd; 
                border: 2px solid #555; 
                border-radius: 5px; 
                margin-top: 10px; 
                font-weight: bold; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px 0 5px; 
            }
        """)
        
        self.init_ui()
        self.start_auto_refresh()
        
    def init_ui(self):
        """Initialize the debug interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Add tabs
        self.create_game_state_tab()
        self.create_players_tab() 
        self.create_phase_control_tab()
        self.create_actions_tab()
        self.create_console_tab()
        
        # Status bar
        self.status_label = QLabel("Debug window initialized")
        layout.addWidget(self.status_label)
        
    def create_game_state_tab(self):
        """Game state overview tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Game overview
        overview_group = QGroupBox("Game Overview")
        overview_layout = QFormLayout(overview_group)
        
        self.game_status_label = QLabel("Not loaded")
        self.active_player_label = QLabel("N/A")
        self.current_phase_label = QLabel("N/A") 
        self.turn_number_label = QLabel("N/A")
        self.stack_size_label = QLabel("0")
        
        overview_layout.addRow("Status:", self.game_status_label)
        overview_layout.addRow("Active Player:", self.active_player_label)
        overview_layout.addRow("Phase:", self.current_phase_label)
        overview_layout.addRow("Turn:", self.turn_number_label)
        overview_layout.addRow("Stack Size:", self.stack_size_label)
        
        layout.addWidget(overview_group)
        
        # Game state JSON view
        json_group = QGroupBox("Game State (JSON)")
        json_layout = QVBoxLayout(json_group)
        
        self.game_state_text = QTextEdit()
        self.game_state_text.setReadOnly(True)
        json_layout.addWidget(self.game_state_text)
        
        refresh_btn = QPushButton("Refresh State")
        refresh_btn.clicked.connect(self.refresh_game_state)
        json_layout.addWidget(refresh_btn)
        
        layout.addWidget(json_group)
        
        self.tabs.addTab(tab, "Game State")
        
    def create_players_tab(self):
        """Players information tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Players table
        self.players_table = QTableWidget()
        self.players_table.setColumnCount(7)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Life", "Hand Size", "Library", "Battlefield", "Graveyard", "Mana"
        ])
        
        layout.addWidget(self.players_table)
        
        # Player details
        details_group = QGroupBox("Player Details")
        details_layout = QVBoxLayout(details_group)
        
        self.player_details_text = QTextEdit()
        self.player_details_text.setMaximumHeight(150)
        details_layout.addWidget(self.player_details_text)
        
        layout.addWidget(details_group)
        
        self.tabs.addTab(tab, "Players")
        
    def create_phase_control_tab(self):
        """Phase control and timing tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Phase control
        control_group = QGroupBox("Phase Control")
        control_layout = QVBoxLayout(control_group)
        
        # Quick phase buttons
        phase_buttons_layout = QHBoxLayout()
        phases = [
            "Untap", "Upkeep", "Draw", "Main 1", 
            "Combat", "Main 2", "End", "Cleanup"
        ]
        
        for phase in phases:
            btn = QPushButton(phase)
            btn.clicked.connect(lambda checked, p=phase.lower().replace(" ", "_"): self.set_phase(p))
            phase_buttons_layout.addWidget(btn)
            
        control_layout.addLayout(phase_buttons_layout)
        
        # Manual controls
        manual_layout = QHBoxLayout()
        
        advance_btn = QPushButton("Advance Phase")
        advance_btn.clicked.connect(self.advance_phase)
        manual_layout.addWidget(advance_btn)
        
        next_turn_btn = QPushButton("Next Turn")
        next_turn_btn.clicked.connect(self.next_turn)
        manual_layout.addWidget(next_turn_btn)
        
        control_layout.addLayout(manual_layout)
        layout.addWidget(control_group)
        
        # Phase history
        history_group = QGroupBox("Phase History")
        history_layout = QVBoxLayout(history_group)
        
        self.phase_history = QListWidget()
        self.phase_history.setMaximumHeight(200)
        history_layout.addWidget(self.phase_history)
        
        layout.addWidget(history_group)
        
        self.tabs.addTab(tab, "Phase Control")
        
    def create_actions_tab(self):
        """Game actions and testing tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Player actions
        player_actions_layout = QHBoxLayout()
        
        draw_card_btn = QPushButton("Draw Card")
        draw_card_btn.clicked.connect(lambda: self.draw_cards(1))
        player_actions_layout.addWidget(draw_card_btn)
        
        mill_card_btn = QPushButton("Mill Card")
        mill_card_btn.clicked.connect(self.mill_card)
        player_actions_layout.addWidget(mill_card_btn)
        
        gain_life_btn = QPushButton("Gain 5 Life")
        gain_life_btn.clicked.connect(lambda: self.modify_life(5))
        player_actions_layout.addWidget(gain_life_btn)
        
        lose_life_btn = QPushButton("Lose 5 Life")
        lose_life_btn.clicked.connect(lambda: self.modify_life(-5))
        player_actions_layout.addWidget(lose_life_btn)
        
        actions_layout.addLayout(player_actions_layout)
        
        # Mana actions
        mana_layout = QHBoxLayout()
        
        add_mana_btn = QPushButton("Add 10 Mana")
        add_mana_btn.clicked.connect(lambda: self.modify_mana(10))
        mana_layout.addWidget(add_mana_btn)
        
        reset_mana_btn = QPushButton("Reset Mana")
        reset_mana_btn.clicked.connect(lambda: self.modify_mana(0, reset=True))
        mana_layout.addWidget(reset_mana_btn)
        
        actions_layout.addLayout(mana_layout)
        
        # Battlefield actions
        battlefield_layout = QHBoxLayout()
        
        untap_all_btn = QPushButton("Untap All")
        untap_all_btn.clicked.connect(self.untap_all)
        battlefield_layout.addWidget(untap_all_btn)
        
        tap_all_btn = QPushButton("Tap All")
        tap_all_btn.clicked.connect(self.tap_all)
        battlefield_layout.addWidget(tap_all_btn)
        
        actions_layout.addLayout(battlefield_layout)
        layout.addWidget(actions_group)
        
        # Custom action input
        custom_group = QGroupBox("Custom Actions")
        custom_layout = QVBoxLayout(custom_group)
        
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter custom debug command...")
        custom_layout.addWidget(self.custom_input)
        
        execute_btn = QPushButton("Execute")
        execute_btn.clicked.connect(self.execute_custom_action)
        custom_layout.addWidget(execute_btn)
        
        layout.addWidget(custom_group)
        
        self.tabs.addTab(tab, "Actions")
        
    def create_console_tab(self):
        """Console output and logging tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Console output
        console_group = QGroupBox("Debug Console")
        console_layout = QVBoxLayout(console_group)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        console_layout.addWidget(self.console_output)
        
        # Console controls
        console_controls = QHBoxLayout()
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_console)
        console_controls.addWidget(clear_btn)
        
        save_log_btn = QPushButton("Save Log")
        save_log_btn.clicked.connect(self.save_debug_log)
        console_controls.addWidget(save_log_btn)
        
        console_controls.addStretch()
        
        auto_scroll_cb = QCheckBox("Auto-scroll")
        auto_scroll_cb.setChecked(True)
        self.auto_scroll = auto_scroll_cb
        console_controls.addWidget(auto_scroll_cb)
        
        console_layout.addLayout(console_controls)
        layout.addWidget(console_group)
        
        self.tabs.addTab(tab, "Console")
        
        # Initialize console
        self.log_message("Debug console initialized")
        
    def start_auto_refresh(self):
        """Start automatic refresh timer."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(1000)  # Refresh every second
        
    def auto_refresh(self):
        """Automatically refresh debug information."""
        if self.isVisible():
            current_tab = self.tabs.currentIndex()
            if current_tab == 0:  # Game State tab
                self.refresh_game_state()
            elif current_tab == 1:  # Players tab
                self.refresh_players()
                
    def refresh_game_state(self):
        """Refresh game state information."""
        try:
            if not self.api or not hasattr(self.api, 'controller'):
                self.game_status_label.setText("No controller")
                return
                
            controller = self.api.controller
            game = getattr(controller, 'game', None)
            
            if not game:
                self.game_status_label.setText("No game")
                return
                
            # Update labels
            status = "In Game" if getattr(controller, 'in_game', False) else "Not Started"
            if getattr(controller, 'first_player_decided', False):
                status += " (Active)"
                
            self.game_status_label.setText(status)
            
            active_player = getattr(game, 'active_player', 0)
            if hasattr(game, 'players') and game.players:
                player_name = getattr(game.players[active_player], 'name', f'Player {active_player}')
                self.active_player_label.setText(f"{player_name} ({active_player})")
            else:
                self.active_player_label.setText("N/A")
                
            current_phase = getattr(controller, 'current_phase', 'Unknown')
            current_step = getattr(controller, 'current_step', '')
            phase_text = current_phase
            if current_step and current_step != current_phase:
                phase_text += f" / {current_step}"
            self.current_phase_label.setText(phase_text)
            
            self.turn_number_label.setText(str(getattr(game, 'turn', 1)))
            
            stack_size = 0
            if hasattr(game, 'stack'):
                stack_size = len(getattr(game.stack, 'items', []))
            self.stack_size_label.setText(str(stack_size))
            
            # Update JSON view
            game_state = self.serialize_game_state(game)
            self.game_state_text.setText(json.dumps(game_state, indent=2))
            
        except Exception as e:
            self.log_message(f"Error refreshing game state: {e}")
            
    def refresh_players(self):
        """Refresh players information."""
        try:
            if not self.api or not hasattr(self.api, 'controller'):
                return
                
            game = getattr(self.api.controller, 'game', None)
            if not game or not hasattr(game, 'players'):
                return
                
            self.players_table.setRowCount(len(game.players))
            
            for i, player in enumerate(game.players):
                # Safely get collection sizes, handling methods vs attributes
                hand = getattr(player, 'hand', [])
                library = getattr(player, 'library', [])
                battlefield = getattr(player, 'battlefield', [])
                graveyard = getattr(player, 'graveyard', [])
                
                # Check if these are methods and call them if needed
                if callable(hand):
                    hand = hand() if hasattr(player, 'hand') else []
                if callable(library):
                    library = library() if hasattr(player, 'library') else []
                if callable(battlefield):
                    battlefield = battlefield() if hasattr(player, 'battlefield') else []
                if callable(graveyard):
                    graveyard = graveyard() if hasattr(player, 'graveyard') else []
                
                self.players_table.setItem(i, 0, QTableWidgetItem(getattr(player, 'name', f'Player {i}')))
                self.players_table.setItem(i, 1, QTableWidgetItem(str(getattr(player, 'life', 0))))
                self.players_table.setItem(i, 2, QTableWidgetItem(str(len(hand) if hand is not None else 0)))
                self.players_table.setItem(i, 3, QTableWidgetItem(str(len(library) if library is not None else 0)))
                self.players_table.setItem(i, 4, QTableWidgetItem(str(len(battlefield) if battlefield is not None else 0)))
                self.players_table.setItem(i, 5, QTableWidgetItem(str(len(graveyard) if graveyard is not None else 0)))
                self.players_table.setItem(i, 6, QTableWidgetItem(str(getattr(player, 'mana', 0))))
                
        except Exception as e:
            self.log_message(f"Error refreshing players: {e}")
            
    def serialize_game_state(self, game):
        """Serialize game state for JSON display."""
        try:
            state = {
                'active_player': getattr(game, 'active_player', 0),
                'phase_index': getattr(game, 'phase_index', 0),
                'turn': getattr(game, 'turn', 1),
                'phase': getattr(game, 'phase', 'Unknown'),
                'players': []
            }
            
            if hasattr(game, 'players'):
                for player in game.players:
                    # Safely get collection sizes, handling methods vs attributes
                    hand = getattr(player, 'hand', [])
                    library = getattr(player, 'library', [])
                    battlefield = getattr(player, 'battlefield', [])
                    graveyard = getattr(player, 'graveyard', [])
                    
                    # Check if these are methods and call them if needed
                    if callable(hand):
                        hand = hand() if hasattr(player, 'hand') else []
                    if callable(library):
                        library = library() if hasattr(player, 'library') else []
                    if callable(battlefield):
                        battlefield = battlefield() if hasattr(player, 'battlefield') else []
                    if callable(graveyard):
                        graveyard = graveyard() if hasattr(player, 'graveyard') else []
                    
                    player_data = {
                        'name': getattr(player, 'name', 'Unknown'),
                        'life': getattr(player, 'life', 0),
                        'mana': getattr(player, 'mana', 0),
                        'hand_size': len(hand) if hand is not None else 0,
                        'library_size': len(library) if library is not None else 0,
                        'battlefield_size': len(battlefield) if battlefield is not None else 0,
                        'graveyard_size': len(graveyard) if graveyard is not None else 0
                    }
                    state['players'].append(player_data)
                    
            return state
        except Exception as e:
            return {'error': f'Failed to serialize game state: {str(e)}'}
            
    def log_message(self, message):
        """Add message to debug console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.console_output.append(formatted_message)
        
        if self.auto_scroll.isChecked():
            scrollbar = self.console_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
    def clear_console(self):
        """Clear console output."""
        self.console_output.clear()
        self.log_message("Console cleared")
        
    def save_debug_log(self):
        """Save debug log to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_log_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(self.console_output.toPlainText())
                
            self.log_message(f"Debug log saved to {filename}")
        except Exception as e:
            self.log_message(f"Failed to save log: {e}")
            
    # Action methods
    def set_phase(self, phase):
        """Set game to specific phase."""
        try:
            # Check if we have the necessary components
            if not self.api or not hasattr(self.api, 'controller'):
                self.log_message("No controller available")
                return
                
            controller = self.api.controller
            if not hasattr(controller, 'game') or not controller.game:
                self.log_message("No active game")
                return
            
            # Try to import and use phase_hooks
            try:
                from engine.phase_hooks import set_phase
                set_phase(controller, phase)
                self.log_message(f"Phase set to: {phase}")
                self.add_phase_history(f"Manual: Set to {phase}")
            except ImportError:
                # Fallback: try to set phase directly
                if hasattr(controller, 'current_phase'):
                    old_phase = getattr(controller, 'current_phase', 'Unknown')
                    controller.current_phase = phase
                    self.log_message(f"Phase changed: {old_phase} → {phase} (direct)")
                    self.add_phase_history(f"Manual: Set to {phase} (direct)")
                else:
                    self.log_message("Cannot set phase: no phase_hooks or direct access")
        except Exception as e:
            self.log_message(f"Failed to set phase: {e}")
            
    def advance_phase(self):
        """Advance to next phase."""
        try:
            if not self.api or not hasattr(self.api, 'controller'):
                self.log_message("No controller available")
                return
                
            old_phase = getattr(self.api.controller, 'current_phase', 'Unknown')
            
            if hasattr(self.api, 'advance_phase'):
                self.api.advance_phase()
                new_phase = getattr(self.api.controller, 'current_phase', 'Unknown')
                self.log_message(f"Phase advanced: {old_phase} → {new_phase}")
                self.add_phase_history(f"Manual: Advanced {old_phase} → {new_phase}")
            else:
                self.log_message("No advance_phase method available")
        except Exception as e:
            self.log_message(f"Failed to advance phase: {e}")
            
    def next_turn(self):
        """Skip to next turn."""
        try:
            # Advance through phases until we reach cleanup, then advance once more
            current_phase = getattr(self.api.controller, 'current_phase', '')
            while current_phase != 'cleanup':
                self.api.advance_phase()
                current_phase = getattr(self.api.controller, 'current_phase', '')
            # One more to trigger new turn
            self.api.advance_phase()
            self.log_message("Advanced to next turn")
            self.add_phase_history("Manual: Next turn")
        except Exception as e:
            self.log_message(f"Failed to advance turn: {e}")
            
    def draw_cards(self, count):
        """Draw cards for active player."""
        try:
            game = self.api.controller.game
            active_player_id = getattr(game, 'active_player', 0)
            if hasattr(game, 'players') and game.players:
                player = game.players[active_player_id]
                if hasattr(player, 'draw'):
                    player.draw(count)
                    self.log_message(f"Player {active_player_id} drew {count} card(s)")
        except Exception as e:
            self.log_message(f"Failed to draw cards: {e}")
            
    def mill_card(self):
        """Mill one card from library to graveyard."""
        try:
            game = self.api.controller.game
            active_player_id = getattr(game, 'active_player', 0)
            if hasattr(game, 'players') and game.players:
                player = game.players[active_player_id]
                if hasattr(player, 'library') and player.library and hasattr(player, 'graveyard'):
                    card = player.library.pop()
                    player.graveyard.append(card)
                    self.log_message(f"Player {active_player_id} milled: {getattr(card, 'name', 'Unknown card')}")
        except Exception as e:
            self.log_message(f"Failed to mill card: {e}")
            
    def modify_life(self, amount):
        """Modify active player's life."""
        try:
            game = self.api.controller.game
            active_player_id = getattr(game, 'active_player', 0)
            if hasattr(game, 'players') and game.players:
                player = game.players[active_player_id]
                if hasattr(player, 'life'):
                    old_life = player.life
                    player.life += amount
                    self.log_message(f"Player {active_player_id} life: {old_life} → {player.life}")
        except Exception as e:
            self.log_message(f"Failed to modify life: {e}")
            
    def modify_mana(self, amount, reset=False):
        """Modify active player's mana."""
        try:
            game = self.api.controller.game
            active_player_id = getattr(game, 'active_player', 0)
            if hasattr(game, 'players') and game.players:
                player = game.players[active_player_id]
                if hasattr(player, 'mana'):
                    old_mana = player.mana
                    if reset:
                        player.mana = 0
                    else:
                        player.mana += amount
                    self.log_message(f"Player {active_player_id} mana: {old_mana} → {player.mana}")
        except Exception as e:
            self.log_message(f"Failed to modify mana: {e}")
            
    def untap_all(self):
        """Untap all permanents."""
        try:
            game = self.api.controller.game
            active_player_id = getattr(game, 'active_player', 0)
            if hasattr(game, 'players') and game.players:
                player = game.players[active_player_id]
                if hasattr(player, 'battlefield'):
                    count = 0
                    for perm in player.battlefield:
                        if hasattr(perm, 'tapped') and perm.tapped:
                            perm.tapped = False
                            count += 1
                    self.log_message(f"Untapped {count} permanents for player {active_player_id}")
        except Exception as e:
            self.log_message(f"Failed to untap all: {e}")
            
    def tap_all(self):
        """Tap all permanents."""
        try:
            game = self.api.controller.game
            active_player_id = getattr(game, 'active_player', 0)
            if hasattr(game, 'players') and game.players:
                player = game.players[active_player_id]
                if hasattr(player, 'battlefield'):
                    count = 0
                    for perm in player.battlefield:
                        if hasattr(perm, 'tapped') and not perm.tapped:
                            perm.tapped = True
                            count += 1
                    self.log_message(f"Tapped {count} permanents for player {active_player_id}")
        except Exception as e:
            self.log_message(f"Failed to tap all: {e}")
            
    def execute_custom_action(self):
        """Execute custom debug command."""
        command = self.custom_input.text().strip()
        if not command:
            return
            
        self.log_message(f"Executing: {command}")
        
        try:
            # Simple command parser
            if command.startswith("draw "):
                count = int(command.split()[1])
                self.draw_cards(count)
            elif command.startswith("life "):
                amount = int(command.split()[1])
                self.modify_life(amount)
            elif command.startswith("mana "):
                amount = int(command.split()[1])
                self.modify_mana(amount)
            elif command == "untap":
                self.untap_all()
            elif command == "tap":
                self.tap_all()
            elif command.startswith("phase "):
                phase = command.split()[1]
                self.set_phase(phase)
            else:
                self.log_message(f"Unknown command: {command}")
                
        except Exception as e:
            self.log_message(f"Command failed: {e}")
            
        self.custom_input.clear()
        
    def add_phase_history(self, entry):
        """Add entry to phase history."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.phase_history.addItem(f"[{timestamp}] {entry}")
        
        # Keep only last 50 entries
        if self.phase_history.count() > 50:
            self.phase_history.takeItem(0)
            
    def closeEvent(self, event):
        """Handle window close."""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        self.log_message("Debug window closed")
        super().closeEvent(event)
