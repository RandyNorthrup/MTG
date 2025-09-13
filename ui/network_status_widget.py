"""MTG Commander Game - Network Status Widget

This module provides a compact network status widget that can be embedded
in the main game UI to display connection status, player list, and network controls.
"""

from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QProgressBar,
    QFrame, QToolButton, QMenu, QAction
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon

from network.network_game_controller import NetworkGameController
from network.network_client import NetworkClient, ClientState


class NetworkStatusWidget(QWidget):
    """Compact widget showing network status and player information."""
    
    # Signals
    open_lobby_requested = Signal()
    disconnect_requested = Signal()
    game_ready_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(200)
        
        # Network components (set externally)
        self.network_controller: Optional[NetworkGameController] = None
        self.network_client: Optional[NetworkClient] = None
        
        # UI state
        self.is_collapsed = False
        
        self.setup_ui()
        self.setup_connections()
        self.update_display()
    
    def setup_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header with status and controls
        self.create_header(layout)
        
        # Network info panel (collapsible)
        self.create_info_panel(layout)
        
        # Players list (collapsible)
        self.create_players_panel(layout)
    
    def create_header(self, layout: QVBoxLayout):
        """Create the header with status and main controls."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # Network status icon and text
        self.status_label = QLabel("🔌 Not Connected")
        status_font = QFont()
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        # Collapse/expand button
        self.toggle_button = QToolButton()
        self.toggle_button.setText("▼")
        self.toggle_button.setToolTip("Collapse/Expand network panel")
        self.toggle_button.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_button)
        
        # Menu button for network actions
        self.menu_button = QToolButton()
        self.menu_button.setText("⋮")
        self.menu_button.setToolTip("Network options")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        
        # Create menu
        menu = QMenu(self.menu_button)
        
        self.lobby_action = QAction("🌐 Open Lobby", self)
        self.lobby_action.triggered.connect(self.open_lobby_requested.emit)
        menu.addAction(self.lobby_action)
        
        menu.addSeparator()
        
        self.disconnect_action = QAction("🔌 Disconnect", self)
        self.disconnect_action.triggered.connect(self.disconnect_requested.emit)
        self.disconnect_action.setEnabled(False)
        menu.addAction(self.disconnect_action)
        
        menu.addSeparator()
        
        self.ready_action = QAction("✅ Ready to Play", self)
        self.ready_action.triggered.connect(self.game_ready_requested.emit)
        self.ready_action.setEnabled(False)
        menu.addAction(self.ready_action)
        
        self.menu_button.setMenu(menu)
        header_layout.addWidget(self.menu_button)
        
        layout.addWidget(header_frame)
    
    def create_info_panel(self, layout: QVBoxLayout):
        """Create the network information panel."""
        self.info_group = QGroupBox("Network Information")
        info_layout = QVBoxLayout(self.info_group)
        
        # Connection details
        self.connection_label = QLabel("No active connection")
        self.connection_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.connection_label)
        
        # Server info (for hosts)
        self.server_info_label = QLabel("")
        self.server_info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.server_info_label)
        
        # Connection progress (for clients)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(15)
        info_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.info_group)
    
    def create_players_panel(self, layout: QVBoxLayout):
        """Create the connected players panel."""
        self.players_group = QGroupBox("Connected Players (0)")
        players_layout = QVBoxLayout(self.players_group)
        
        # Players list
        self.players_list = QListWidget()
        self.players_list.setMaximumHeight(80)
        self.players_list.setAlternatingRowColors(True)
        players_layout.addWidget(self.players_list)
        
        # No players message
        self.no_players_label = QLabel("No players connected")
        self.no_players_label.setAlignment(Qt.AlignCenter)
        self.no_players_label.setStyleSheet("color: #999; font-style: italic;")
        players_layout.addWidget(self.no_players_label)
        
        layout.addWidget(self.players_group)
    
    def setup_connections(self):
        """Set up internal signal connections."""
        pass
    
    def set_network_controller(self, controller: Optional[NetworkGameController]):
        """Set the network controller and connect signals."""
        # Disconnect old signals
        if self.network_controller:
            self.network_controller.network_player_joined.disconnect(self.on_player_joined)
            self.network_controller.network_player_left.disconnect(self.on_player_left)
            self.network_controller.network_error.disconnect(self.on_network_error)
            self.network_controller.connection_status_changed.disconnect(self.on_status_changed)
        
        self.network_controller = controller
        
        # Connect new signals
        if self.network_controller:
            self.network_controller.network_player_joined.connect(self.on_player_joined)
            self.network_controller.network_player_left.connect(self.on_player_left)
            self.network_controller.network_error.connect(self.on_network_error)
            self.network_controller.connection_status_changed.connect(self.on_status_changed)
        
        self.update_display()
    
    def set_network_client(self, client: Optional[NetworkClient]):
        """Set the network client and connect signals."""
        # Disconnect old signals
        if self.network_client:
            self.network_client.connected.disconnect(self.on_client_connected)
            self.network_client.disconnected.disconnect(self.on_client_disconnected)
        
        self.network_client = client
        
        # Connect new signals
        if self.network_client:
            self.network_client.connected.connect(self.on_client_connected)
            self.network_client.disconnected.connect(self.on_client_disconnected)
        
        self.update_display()
    
    def update_display(self):
        """Update the display based on current network state."""
        if not self.network_controller:
            # No network connection
            self.status_label.setText("🔌 Not Connected")
            self.status_label.setStyleSheet("color: #666;")
            self.connection_label.setText("No active connection")
            self.server_info_label.setText("")
            self.players_list.clear()
            self.no_players_label.setVisible(True)
            self.players_group.setTitle("Connected Players (0)")
            
            # Update menu actions
            self.disconnect_action.setEnabled(False)
            self.ready_action.setEnabled(False)
            
        elif self.network_controller.is_server:
            # Server mode
            server_info = self.network_controller.get_network_info()
            server_data = server_info.get('server', {})
            
            self.status_label.setText("🏠 Hosting Game")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            if 'host' in server_data and 'port' in server_data:
                self.connection_label.setText(f"Server: {server_data['host']}:{server_data['port']}")
            else:
                self.connection_label.setText("Server running")
            
            player_count = len(self.network_controller.network_players)
            self.server_info_label.setText(f"Waiting for players ({player_count} connected)")
            
            # Update menu actions
            self.disconnect_action.setEnabled(True)
            self.ready_action.setEnabled(player_count > 1)  # Need at least 2 players
            
        else:
            # Client mode
            client_info = self.network_controller.get_network_info()
            client_data = client_info.get('client', {})
            
            if self.network_client and self.network_client.state == ClientState.CONNECTED:
                self.status_label.setText("🌐 Connected")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.connection_label.setText("Connected to server")
                self.server_info_label.setText("Waiting for game to start")
                
                # Update menu actions
                self.disconnect_action.setEnabled(True)
                self.ready_action.setEnabled(True)
                
            elif self.network_client and self.network_client.state == ClientState.CONNECTING:
                self.status_label.setText("🔄 Connecting...")
                self.status_label.setStyleSheet("color: blue;")
                self.connection_label.setText("Connecting to server...")
                self.server_info_label.setText("")
                
                # Show progress bar
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # Indeterminate
                
                # Update menu actions
                self.disconnect_action.setEnabled(True)
                self.ready_action.setEnabled(False)
                
            else:
                self.status_label.setText("❌ Connection Failed")
                self.status_label.setStyleSheet("color: red;")
                self.connection_label.setText("Connection error")
                self.server_info_label.setText("")
                
                # Update menu actions
                self.disconnect_action.setEnabled(False)
                self.ready_action.setEnabled(False)
        
        # Update players list
        self.update_players_list()
    
    def update_players_list(self):
        """Update the connected players list."""
        self.players_list.clear()
        
        if self.network_controller:
            players = self.network_controller.network_players
            
            if players:
                self.no_players_label.setVisible(False)
                self.players_list.setVisible(True)
                
                for player_id, player_info in players.items():
                    player_name = player_info.get('name', f'Player {player_id}')
                    
                    # Add host indicator
                    if self.network_controller.is_server and player_id == 0:
                        player_name += " (Host)"
                    
                    item = QListWidgetItem(f"👤 {player_name}")
                    item.setData(Qt.UserRole, player_id)
                    self.players_list.addItem(item)
                
                self.players_group.setTitle(f"Connected Players ({len(players)})")
            else:
                self.no_players_label.setVisible(True)
                self.players_list.setVisible(False)
                self.players_group.setTitle("Connected Players (0)")
        else:
            self.no_players_label.setVisible(True)
            self.players_list.setVisible(False)
            self.players_group.setTitle("Connected Players (0)")
    
    def toggle_collapse(self):
        """Toggle the collapse state of the network panel."""
        self.is_collapsed = not self.is_collapsed
        
        if self.is_collapsed:
            self.info_group.setVisible(False)
            self.players_group.setVisible(False)
            self.toggle_button.setText("▶")
            self.setMaximumHeight(50)
        else:
            self.info_group.setVisible(True)
            self.players_group.setVisible(True)
            self.toggle_button.setText("▼")
            self.setMaximumHeight(200)
    
    def show_connecting_progress(self, show: bool = True):
        """Show or hide the connection progress bar."""
        self.progress_bar.setVisible(show)
        if show:
            self.progress_bar.setRange(0, 0)  # Indeterminate
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
    
    # Signal handlers
    
    def on_player_joined(self, player_id: int, player_name: str):
        """Handle player joining event."""
        self.update_display()
    
    def on_player_left(self, player_id: int, player_name: str):
        """Handle player leaving event."""
        self.update_display()
    
    def on_network_error(self, error_msg: str):
        """Handle network error."""
        self.status_label.setText(f"❌ Error: {error_msg[:20]}...")
        self.status_label.setStyleSheet("color: red;")
        self.connection_label.setText(f"Error: {error_msg}")
        self.server_info_label.setText("")
        self.progress_bar.setVisible(False)
        
        # Update menu actions
        self.disconnect_action.setEnabled(True)  # Allow disconnect to clean up
        self.ready_action.setEnabled(False)
    
    def on_status_changed(self, status_msg: str):
        """Handle network status change."""
        # Update connection info
        if "Server running" in status_msg:
            self.update_display()
        elif "Connected" in status_msg:
            self.show_connecting_progress(False)
            self.update_display()
        elif "Connecting" in status_msg:
            self.show_connecting_progress(True)
        elif "Disconnected" in status_msg:
            self.show_connecting_progress(False)
            self.update_display()
    
    def on_client_connected(self):
        """Handle client connection established."""
        self.show_connecting_progress(False)
        self.update_display()
    
    def on_client_disconnected(self):
        """Handle client disconnection."""
        self.show_connecting_progress(False)
        self.update_display()
    
    # Utility methods
    
    def get_connection_status(self) -> str:
        """Get a text description of the current connection status."""
        if not self.network_controller:
            return "Not connected"
        
        if self.network_controller.is_server:
            player_count = len(self.network_controller.network_players)
            return f"Hosting ({player_count} players)"
        else:
            if self.network_client:
                return f"Client ({self.network_client.state.value})"
            else:
                return "Client (unknown state)"
    
    def is_ready_for_game(self) -> bool:
        """Check if the network is ready to start a game."""
        if not self.network_controller:
            return False
        
        if self.network_controller.is_server:
            return len(self.network_controller.network_players) >= 2
        else:
            return (self.network_client and 
                   self.network_client.state == ClientState.CONNECTED)
    
    def get_player_count(self) -> int:
        """Get the number of connected players."""
        if self.network_controller:
            return len(self.network_controller.network_players)
        return 0
