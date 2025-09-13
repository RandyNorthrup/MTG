"""MTG Commander Game - Network Lobby Dialog

This module provides the main lobby interface for multiplayer networking.
Players can create new games as servers or join existing games as clients.
"""

import os
import socket
from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QLineEdit, QSpinBox, QTabWidget, QWidget, QGroupBox, QListWidget,
    QListWidgetItem, QTextEdit, QComboBox, QProgressBar, QMessageBox,
    QSplitter, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, pyqtSignal
from PySide6.QtGui import QFont, QPixmap, QPalette, QIcon

from network.network_game_controller import NetworkGameController
from network.network_client import NetworkClient, ClientState
from ui.deck_selection_dialog import DeckSelectionDialog


class NetworkDiscoveryThread(QThread):
    """Thread for discovering network games via LAN scanning."""
    
    game_discovered = pyqtSignal(str, int, str, int)  # host, port, game_name, player_count
    discovery_finished = pyqtSignal()
    
    def __init__(self, port_range=(8888, 8898)):
        super().__init__()
        self.port_range = port_range
        self.is_scanning = False
    
    def run(self):
        """Scan local network for active game servers."""
        self.is_scanning = True
        
        # Get local network range
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network_base = '.'.join(local_ip.split('.')[:-1]) + '.'
        except:
            network_base = '192.168.1.'  # Fallback
        
        # Scan common IP ranges and ports
        for i in range(1, 255):
            if not self.is_scanning:
                break
                
            target_ip = network_base + str(i)
            
            for port in range(self.port_range[0], self.port_range[1] + 1):
                if not self.is_scanning:
                    break
                
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)  # Very quick timeout
                    result = sock.connect_ex((target_ip, port))
                    sock.close()
                    
                    if result == 0:
                        # Found a server, emit discovery signal
                        self.game_discovered.emit(target_ip, port, f"Game on {target_ip}", 0)
                        
                except:
                    continue
        
        self.discovery_finished.emit()
    
    def stop_scanning(self):
        """Stop the network discovery scan."""
        self.is_scanning = False


class GameServerItem(QListWidgetItem):
    """Custom list item for displaying discovered game servers."""
    
    def __init__(self, host: str, port: int, game_name: str, player_count: int):
        super().__init__()
        self.host = host
        self.port = port
        self.game_name = game_name
        self.player_count = player_count
        
        # Set display text
        self.setText(f"{game_name} ({host}:{port}) - {player_count} players")
        
        # Set tooltip with more details
        self.setToolTip(f"Host: {host}\nPort: {port}\nPlayers: {player_count}")


class NetworkLobbyDialog(QDialog):
    """Main lobby dialog for network multiplayer games."""
    
    # Signals for game events
    game_created = Signal(NetworkGameController)
    game_joined = Signal(NetworkGameController, NetworkClient)
    lobby_closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MTG Commander - Network Multiplayer Lobby")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # Network components
        self.network_controller: Optional[NetworkGameController] = None
        self.network_client: Optional[NetworkClient] = None
        self.discovery_thread: Optional[NetworkDiscoveryThread] = None
        
        # UI refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_server_list)
        
        self.setup_ui()
        self.setup_connections()
        self.load_settings()
    
    def setup_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        self.create_header(layout)
        
        # Main content tabs
        self.create_tabs(layout)
        
        # Footer with connection status
        self.create_footer(layout)
    
    def create_header(self, layout: QVBoxLayout):
        """Create the header section with title and info."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("🌐 Network Multiplayer Lobby")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Create or join local network games with friends")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_frame)
    
    def create_tabs(self, layout: QVBoxLayout):
        """Create the main tab widget with host and join tabs."""
        self.tab_widget = QTabWidget()
        
        # Host Game Tab
        self.host_tab = self.create_host_tab()
        self.tab_widget.addTab(self.host_tab, "🏠 Host Game")
        
        # Join Game Tab  
        self.join_tab = self.create_join_tab()
        self.tab_widget.addTab(self.join_tab, "🚀 Join Game")
        
        # Game Browser Tab
        self.browser_tab = self.create_browser_tab()
        self.tab_widget.addTab(self.browser_tab, "🔍 Browse Games")
        
        layout.addWidget(self.tab_widget)
    
    def create_host_tab(self) -> QWidget:
        """Create the host game tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Server Configuration
        config_group = QGroupBox("Server Configuration")
        config_layout = QGridLayout(config_group)
        
        # Game Name
        config_layout.addWidget(QLabel("Game Name:"), 0, 0)
        self.game_name_edit = QLineEdit("Commander Game")
        config_layout.addWidget(self.game_name_edit, 0, 1)
        
        # Host Address
        config_layout.addWidget(QLabel("Host Address:"), 1, 0)
        self.host_address_edit = QLineEdit("localhost")
        self.host_address_edit.setToolTip("IP address to bind server to (localhost for local-only)")
        config_layout.addWidget(self.host_address_edit, 1, 1)
        
        # Port
        config_layout.addWidget(QLabel("Port:"), 2, 0)
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(8000, 9999)
        self.port_spinbox.setValue(8888)
        config_layout.addWidget(self.port_spinbox, 2, 1)
        
        # Max Players
        config_layout.addWidget(QLabel("Max Players:"), 3, 0)
        self.max_players_spinbox = QSpinBox()
        self.max_players_spinbox.setRange(2, 8)
        self.max_players_spinbox.setValue(4)
        config_layout.addWidget(self.max_players_spinbox, 3, 1)
        
        layout.addWidget(config_group)
        
        # Player Configuration
        player_group = QGroupBox("Your Player Settings")
        player_layout = QGridLayout(player_group)
        
        # Player Name
        player_layout.addWidget(QLabel("Player Name:"), 0, 0)
        self.host_player_name = QLineEdit("Host Player")
        player_layout.addWidget(self.host_player_name, 0, 1)
        
        # Deck Selection
        player_layout.addWidget(QLabel("Deck:"), 1, 0)
        deck_layout = QHBoxLayout()
        self.host_deck_combo = QComboBox()
        self.load_available_decks(self.host_deck_combo)
        deck_layout.addWidget(self.host_deck_combo)
        
        self.host_deck_browse_btn = QPushButton("Browse...")
        self.host_deck_browse_btn.clicked.connect(self.browse_host_deck)
        deck_layout.addWidget(self.host_deck_browse_btn)
        
        player_layout.addLayout(deck_layout, 1, 1)
        
        layout.addWidget(player_group)
        
        # Server Status
        self.host_status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout(self.host_status_group)
        
        self.server_status_label = QLabel("Ready to host")
        self.server_status_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.server_status_label)
        
        self.connected_players_list = QListWidget()
        self.connected_players_list.setMaximumHeight(100)
        status_layout.addWidget(QLabel("Connected Players:"))
        status_layout.addWidget(self.connected_players_list)
        
        layout.addWidget(self.host_status_group)
        
        # Host Button
        self.host_button = QPushButton("🚀 Start Hosting")
        self.host_button.setMinimumHeight(40)
        self.host_button.clicked.connect(self.start_hosting)
        layout.addWidget(self.host_button)
        
        # Stop hosting button (initially hidden)
        self.stop_host_button = QPushButton("⏹️ Stop Hosting")
        self.stop_host_button.setMinimumHeight(40)
        self.stop_host_button.clicked.connect(self.stop_hosting)
        self.stop_host_button.setVisible(False)
        layout.addWidget(self.stop_host_button)
        
        layout.addStretch()
        return widget
    
    def create_join_tab(self) -> QWidget:
        """Create the join game tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Connection Configuration
        connect_group = QGroupBox("Server Connection")
        connect_layout = QGridLayout(connect_group)
        
        # Server Address
        connect_layout.addWidget(QLabel("Server Address:"), 0, 0)
        self.server_address_edit = QLineEdit("localhost")
        connect_layout.addWidget(self.server_address_edit, 0, 1)
        
        # Server Port
        connect_layout.addWidget(QLabel("Server Port:"), 1, 0)
        self.server_port_spinbox = QSpinBox()
        self.server_port_spinbox.setRange(8000, 9999)
        self.server_port_spinbox.setValue(8888)
        connect_layout.addWidget(self.server_port_spinbox, 1, 1)
        
        layout.addWidget(connect_group)
        
        # Player Configuration
        join_player_group = QGroupBox("Your Player Settings")
        join_player_layout = QGridLayout(join_player_group)
        
        # Player Name
        join_player_layout.addWidget(QLabel("Player Name:"), 0, 0)
        self.join_player_name = QLineEdit("Player")
        join_player_layout.addWidget(self.join_player_name, 0, 1)
        
        # Deck Selection
        join_player_layout.addWidget(QLabel("Deck:"), 1, 0)
        join_deck_layout = QHBoxLayout()
        self.join_deck_combo = QComboBox()
        self.load_available_decks(self.join_deck_combo)
        join_deck_layout.addWidget(self.join_deck_combo)
        
        self.join_deck_browse_btn = QPushButton("Browse...")
        self.join_deck_browse_btn.clicked.connect(self.browse_join_deck)
        join_deck_layout.addWidget(self.join_deck_browse_btn)
        
        join_player_layout.addLayout(join_deck_layout, 1, 1)
        
        layout.addWidget(join_player_group)
        
        # Connection Status
        self.join_status_group = QGroupBox("Connection Status")
        join_status_layout = QVBoxLayout(self.join_status_group)
        
        self.connection_status_label = QLabel("Ready to connect")
        self.connection_status_label.setStyleSheet("color: #666;")
        join_status_layout.addWidget(self.connection_status_label)
        
        self.connection_progress = QProgressBar()
        self.connection_progress.setVisible(False)
        join_status_layout.addWidget(self.connection_progress)
        
        layout.addWidget(self.join_status_group)
        
        # Join Button
        self.join_button = QPushButton("🌐 Join Game")
        self.join_button.setMinimumHeight(40)
        self.join_button.clicked.connect(self.join_game)
        layout.addWidget(self.join_button)
        
        # Disconnect button (initially hidden)
        self.disconnect_button = QPushButton("🔌 Disconnect")
        self.disconnect_button.setMinimumHeight(40)
        self.disconnect_button.clicked.connect(self.disconnect_from_game)
        self.disconnect_button.setVisible(False)
        layout.addWidget(self.disconnect_button)
        
        layout.addStretch()
        return widget
    
    def create_browser_tab(self) -> QWidget:
        """Create the game browser tab for discovering local games."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Browser controls
        controls_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("🔍 Scan for Games")
        self.scan_button.clicked.connect(self.scan_for_games)
        controls_layout.addWidget(self.scan_button)
        
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_game_list)
        controls_layout.addWidget(self.refresh_button)
        
        controls_layout.addStretch()
        
        # Auto-refresh checkbox
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.scan_for_games)
        
        layout.addLayout(controls_layout)
        
        # Discovered Games List
        games_group = QGroupBox("Discovered Games")
        games_layout = QVBoxLayout(games_group)
        
        self.discovered_games_list = QListWidget()
        self.discovered_games_list.itemDoubleClicked.connect(self.quick_join_game)
        games_layout.addWidget(self.discovered_games_list)
        
        # Quick join controls
        quick_join_layout = QHBoxLayout()
        
        self.quick_join_button = QPushButton("⚡ Quick Join Selected")
        self.quick_join_button.clicked.connect(self.quick_join_selected)
        self.quick_join_button.setEnabled(False)
        quick_join_layout.addWidget(self.quick_join_button)
        
        quick_join_layout.addStretch()
        
        games_layout.addLayout(quick_join_layout)
        
        layout.addWidget(games_group)
        
        # Enable quick join when selection changes
        self.discovered_games_list.itemSelectionChanged.connect(
            lambda: self.quick_join_button.setEnabled(
                bool(self.discovered_games_list.currentItem())
            )
        )
        
        return widget
    
    def create_footer(self, layout: QVBoxLayout):
        """Create the footer with status and controls."""
        footer_frame = QFrame()
        footer_frame.setFrameStyle(QFrame.StyledPanel)
        footer_layout = QHBoxLayout(footer_frame)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        # Close button
        close_button = QPushButton("Close Lobby")
        close_button.clicked.connect(self.close_lobby)
        footer_layout.addWidget(close_button)
        
        layout.addWidget(footer_frame)
    
    def setup_connections(self):
        """Set up signal connections."""
        # Tab change handling
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def load_settings(self):
        """Load saved settings and defaults."""
        try:
            # Try to get local IP address for hosting
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip != "127.0.0.1":
                self.host_address_edit.setText(local_ip)
        except:
            pass  # Keep default localhost
    
    def load_available_decks(self, combo_box: QComboBox):
        """Load available decks into a combo box."""
        combo_box.clear()
        
        # Look for deck files
        decks_dir = "data/decks"
        if os.path.exists(decks_dir):
            for filename in os.listdir(decks_dir):
                if filename.endswith('.txt'):
                    deck_name = filename[:-4]  # Remove .txt extension
                    combo_box.addItem(deck_name, filename)
        
        # Add default if no decks found
        if combo_box.count() == 0:
            combo_box.addItem("No decks found", "")
    
    def browse_host_deck(self):
        """Browse for host deck file."""
        self.browse_deck(self.host_deck_combo)
    
    def browse_join_deck(self):
        """Browse for join deck file."""
        self.browse_deck(self.join_deck_combo)
    
    def browse_deck(self, combo_box: QComboBox):
        """Browse for a deck file and add to combo box."""
        dialog = DeckSelectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            selected_deck = dialog.get_selected_deck()
            if selected_deck:
                # Add to combo box if not already there
                for i in range(combo_box.count()):
                    if combo_box.itemText(i) == selected_deck:
                        combo_box.setCurrentIndex(i)
                        return
                
                # Add new deck
                combo_box.addItem(selected_deck, selected_deck + ".txt")
                combo_box.setCurrentIndex(combo_box.count() - 1)
    
    def start_hosting(self):
        """Start hosting a game server."""
        try:
            # Validate inputs
            game_name = self.game_name_edit.text().strip()
            if not game_name:
                self.show_error("Please enter a game name")
                return
            
            player_name = self.host_player_name.text().strip()
            if not player_name:
                self.show_error("Please enter your player name")
                return
            
            deck_name = self.host_deck_combo.currentText()
            if not deck_name or deck_name == "No decks found":
                self.show_error("Please select a valid deck")
                return
            
            # Create network controller
            self.network_controller = NetworkGameController()
            
            # Connect signals
            self.network_controller.network_player_joined.connect(self.on_player_joined)
            self.network_controller.network_player_left.connect(self.on_player_left)
            self.network_controller.network_error.connect(self.on_network_error)
            self.network_controller.connection_status_changed.connect(self.on_status_changed)
            
            # Start server
            host = self.host_address_edit.text()
            port = self.port_spinbox.value()
            
            if self.network_controller.setup_as_server(host, port):
                self.host_button.setVisible(False)
                self.stop_host_button.setVisible(True)
                self.server_status_label.setText(f"Hosting on {host}:{port}")
                self.server_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.status_label.setText("Server running - waiting for players")
                
                # Add host player to list
                self.add_connected_player(0, player_name + " (Host)")
                
                # Disable configuration controls
                self.set_host_controls_enabled(False)
                
            else:
                self.show_error("Failed to start server. Check if port is already in use.")
                
        except Exception as e:
            self.show_error(f"Error starting server: {e}")
    
    def stop_hosting(self):
        """Stop hosting the game server."""
        try:
            if self.network_controller:
                self.network_controller.disconnect_from_network()
                self.network_controller = None
            
            # Reset UI
            self.host_button.setVisible(True)
            self.stop_host_button.setVisible(False)
            self.server_status_label.setText("Ready to host")
            self.server_status_label.setStyleSheet("color: #666;")
            self.status_label.setText("Ready")
            self.connected_players_list.clear()
            
            # Re-enable configuration controls
            self.set_host_controls_enabled(True)
            
        except Exception as e:
            self.show_error(f"Error stopping server: {e}")
    
    def join_game(self):
        """Join an existing game server."""
        try:
            # Validate inputs
            player_name = self.join_player_name.text().strip()
            if not player_name:
                self.show_error("Please enter your player name")
                return
            
            deck_name = self.join_deck_combo.currentText()
            if not deck_name or deck_name == "No decks found":
                self.show_error("Please select a valid deck")
                return
            
            # Create network controller
            self.network_controller = NetworkGameController()
            
            # Set up as client
            self.network_client = self.network_controller.setup_as_client(player_name, deck_name)
            if not self.network_client:
                self.show_error("Failed to setup network client")
                return
            
            # Connect signals
            self.network_controller.network_error.connect(self.on_network_error)
            self.network_controller.connection_status_changed.connect(self.on_status_changed)
            self.network_client.connected.connect(self.on_connected_to_server)
            self.network_client.disconnected.connect(self.on_disconnected_from_server)
            
            # Show connection progress
            self.connection_progress.setVisible(True)
            self.connection_progress.setRange(0, 0)  # Indeterminate progress
            self.connection_status_label.setText("Connecting...")
            self.connection_status_label.setStyleSheet("color: blue;")
            
            # Connect to server
            host = self.server_address_edit.text()
            port = self.server_port_spinbox.value()
            
            if self.network_controller.connect_to_server(host, port, player_name, deck_name):
                self.join_button.setVisible(False)
                self.disconnect_button.setVisible(True)
                
                # Disable configuration controls
                self.set_join_controls_enabled(False)
                
            else:
                self.connection_progress.setVisible(False)
                self.connection_status_label.setText("Connection failed")
                self.connection_status_label.setStyleSheet("color: red;")
                self.show_error("Failed to connect to server")
                
        except Exception as e:
            self.connection_progress.setVisible(False)
            self.show_error(f"Error joining game: {e}")
    
    def disconnect_from_game(self):
        """Disconnect from the current game."""
        try:
            if self.network_controller:
                self.network_controller.disconnect_from_network()
                self.network_controller = None
                self.network_client = None
            
            # Reset UI
            self.join_button.setVisible(True)
            self.disconnect_button.setVisible(False)
            self.connection_progress.setVisible(False)
            self.connection_status_label.setText("Ready to connect")
            self.connection_status_label.setStyleSheet("color: #666;")
            self.status_label.setText("Ready")
            
            # Re-enable configuration controls
            self.set_join_controls_enabled(True)
            
        except Exception as e:
            self.show_error(f"Error disconnecting: {e}")
    
    def scan_for_games(self):
        """Start scanning for local network games."""
        if self.discovery_thread and self.discovery_thread.isRunning():
            self.discovery_thread.stop_scanning()
            self.discovery_thread.wait()
        
        self.discovered_games_list.clear()
        self.scan_button.setText("🔄 Scanning...")
        self.scan_button.setEnabled(False)
        
        # Start discovery thread
        self.discovery_thread = NetworkDiscoveryThread()
        self.discovery_thread.game_discovered.connect(self.on_game_discovered)
        self.discovery_thread.discovery_finished.connect(self.on_discovery_finished)
        self.discovery_thread.start()
    
    def refresh_game_list(self):
        """Refresh the discovered games list."""
        self.scan_for_games()
    
    def quick_join_selected(self):
        """Quick join the selected game from the browser."""
        current_item = self.discovered_games_list.currentItem()
        if isinstance(current_item, GameServerItem):
            self.quick_join_game(current_item)
    
    def quick_join_game(self, item: GameServerItem):
        """Quick join a discovered game."""
        # Switch to join tab
        self.tab_widget.setCurrentIndex(1)  # Join Game tab
        
        # Fill in connection details
        self.server_address_edit.setText(item.host)
        self.server_port_spinbox.setValue(item.port)
        
        # Trigger join
        self.join_game()
    
    def on_game_discovered(self, host: str, port: int, game_name: str, player_count: int):
        """Handle discovery of a network game."""
        item = GameServerItem(host, port, game_name, player_count)
        self.discovered_games_list.addItem(item)
    
    def on_discovery_finished(self):
        """Handle completion of network discovery."""
        self.scan_button.setText("🔍 Scan for Games")
        self.scan_button.setEnabled(True)
        
        if self.discovered_games_list.count() == 0:
            item = QListWidgetItem("No games found on local network")
            item.setFlags(Qt.NoItemFlags)  # Make it unselectable
            self.discovered_games_list.addItem(item)
    
    def on_tab_changed(self, index: int):
        """Handle tab change events."""
        if index == 2:  # Browser tab
            # Auto-scan when switching to browser tab
            self.scan_for_games()
    
    def on_player_joined(self, player_id: int, player_name: str):
        """Handle player joining the hosted game."""
        self.add_connected_player(player_id, player_name)
        self.status_label.setText(f"Player joined: {player_name}")
    
    def on_player_left(self, player_id: int, player_name: str):
        """Handle player leaving the hosted game."""
        self.remove_connected_player(player_id)
        self.status_label.setText(f"Player left: {player_name}")
    
    def on_connected_to_server(self):
        """Handle successful connection to server."""
        self.connection_progress.setVisible(False)
        self.connection_status_label.setText("Connected to server")
        self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
        self.status_label.setText("Connected - waiting for game to start")
    
    def on_disconnected_from_server(self):
        """Handle disconnection from server."""
        self.disconnect_from_game()
    
    def on_network_error(self, error_msg: str):
        """Handle network errors."""
        self.status_label.setText(f"Network error: {error_msg}")
        self.show_error(f"Network Error: {error_msg}")
    
    def on_status_changed(self, status_msg: str):
        """Handle network status changes."""
        self.status_label.setText(status_msg)
    
    def add_connected_player(self, player_id: int, player_name: str):
        """Add a player to the connected players list."""
        item = QListWidgetItem(f"{player_name} (ID: {player_id})")
        item.setData(Qt.UserRole, player_id)
        self.connected_players_list.addItem(item)
    
    def remove_connected_player(self, player_id: int):
        """Remove a player from the connected players list."""
        for i in range(self.connected_players_list.count()):
            item = self.connected_players_list.item(i)
            if item.data(Qt.UserRole) == player_id:
                self.connected_players_list.takeItem(i)
                break
    
    def set_host_controls_enabled(self, enabled: bool):
        """Enable or disable host configuration controls."""
        self.game_name_edit.setEnabled(enabled)
        self.host_address_edit.setEnabled(enabled)
        self.port_spinbox.setEnabled(enabled)
        self.max_players_spinbox.setEnabled(enabled)
        self.host_player_name.setEnabled(enabled)
        self.host_deck_combo.setEnabled(enabled)
        self.host_deck_browse_btn.setEnabled(enabled)
    
    def set_join_controls_enabled(self, enabled: bool):
        """Enable or disable join configuration controls."""
        self.server_address_edit.setEnabled(enabled)
        self.server_port_spinbox.setEnabled(enabled)
        self.join_player_name.setEnabled(enabled)
        self.join_deck_combo.setEnabled(enabled)
        self.join_deck_browse_btn.setEnabled(enabled)
    
    def show_error(self, message: str):
        """Show an error message to the user."""
        QMessageBox.critical(self, "Network Lobby Error", message)
    
    def show_info(self, message: str):
        """Show an info message to the user."""
        QMessageBox.information(self, "Network Lobby", message)
    
    def close_lobby(self):
        """Close the lobby dialog."""
        # Clean up connections
        if self.network_controller:
            self.network_controller.disconnect_from_network()
        
        if self.discovery_thread and self.discovery_thread.isRunning():
            self.discovery_thread.stop_scanning()
            self.discovery_thread.wait()
        
        self.lobby_closed.emit()
        self.close()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        self.close_lobby()
        super().closeEvent(event)
    
    def get_network_controller(self) -> Optional[NetworkGameController]:
        """Get the current network controller."""
        return self.network_controller
    
    def get_network_client(self) -> Optional[NetworkClient]:
        """Get the current network client."""
        return self.network_client
