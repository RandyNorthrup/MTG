# MTG Commander - Network UI Integration Guide

This guide explains how to integrate the networking UI components into your existing MTG Commander Game Engine interface.

## 🎯 Overview

The network multiplayer system includes two main UI components:

1. **NetworkLobbyDialog** - Full-screen lobby for creating/joining games
2. **NetworkStatusWidget** - Compact status widget for the main game UI

## 🚀 Quick Integration

### 1. Adding Network Lobby to Main Menu

```python
# In your main window or menu system
from ui.network_lobby_dialog import NetworkLobbyDialog
from network.network_game_controller import NetworkGameController

def open_multiplayer_lobby(self):
    """Open the network multiplayer lobby."""
    lobby = NetworkLobbyDialog(self)
    
    # Connect lobby signals
    lobby.game_created.connect(self.on_network_game_created)
    lobby.game_joined.connect(self.on_network_game_joined)
    lobby.lobby_closed.connect(self.on_lobby_closed)
    
    lobby.exec()  # Show as modal dialog

def on_network_game_created(self, controller: NetworkGameController):
    """Handle successful game hosting."""
    self.network_controller = controller
    self.start_multiplayer_game()

def on_network_game_joined(self, controller: NetworkGameController, client):
    """Handle successful game joining."""
    self.network_controller = controller
    self.network_client = client
    self.start_multiplayer_game()
```

### 2. Adding Network Status Widget to Game UI

```python
# In your main game window
from ui.network_status_widget import NetworkStatusWidget

def setup_game_ui(self):
    """Set up the main game interface."""
    # ... existing UI setup ...
    
    # Add network status widget
    self.network_status = NetworkStatusWidget()
    self.network_status.open_lobby_requested.connect(self.open_multiplayer_lobby)
    self.network_status.disconnect_requested.connect(self.disconnect_network)
    self.network_status.game_ready_requested.connect(self.start_network_game)
    
    # Add to your layout (example: sidebar or bottom panel)
    self.sidebar_layout.addWidget(self.network_status)

def set_network_controller(self, controller: NetworkGameController):
    """Update the network controller for UI components."""
    self.network_controller = controller
    self.network_status.set_network_controller(controller)
    
    # Also set client if available
    if hasattr(self, 'network_client'):
        self.network_status.set_network_client(self.network_client)
```

## 🎮 Complete Integration Example

Here's a complete example showing how to integrate networking into an existing main window:

```python
# main_window_with_networking.py
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QMenuBar
from PySide6.QtCore import Signal

from ui.network_lobby_dialog import NetworkLobbyDialog
from ui.network_status_widget import NetworkStatusWidget
from network.network_game_controller import NetworkGameController

class MainWindowWithNetworking(QMainWindow):
    def __init__(self):
        super().__init__()
        self.network_controller = None
        self.network_client = None
        
        self.setup_ui()
        self.setup_menu()
    
    def setup_ui(self):
        """Set up the main UI with networking support."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Game area (your existing game UI)
        game_layout = QVBoxLayout()
        # ... add your existing game widgets here ...
        
        # Sidebar with network status
        sidebar_layout = QVBoxLayout()
        
        # Network status widget
        self.network_status = NetworkStatusWidget()
        self.network_status.open_lobby_requested.connect(self.open_multiplayer_lobby)
        self.network_status.disconnect_requested.connect(self.disconnect_network)
        self.network_status.game_ready_requested.connect(self.ready_for_game)
        sidebar_layout.addWidget(self.network_status)
        
        sidebar_layout.addStretch()
        
        # Add layouts to main layout
        main_layout.addLayout(game_layout, 3)  # 3/4 of space
        main_layout.addLayout(sidebar_layout, 1)  # 1/4 of space
    
    def setup_menu(self):
        """Set up menu bar with network options."""
        menubar = self.menuBar()
        
        # Network menu
        network_menu = menubar.addMenu("Network")
        
        # Multiplayer lobby action
        lobby_action = network_menu.addAction("🌐 Multiplayer Lobby")
        lobby_action.triggered.connect(self.open_multiplayer_lobby)
        
        network_menu.addSeparator()
        
        # Quick host action
        host_action = network_menu.addAction("🏠 Quick Host Game")
        host_action.triggered.connect(self.quick_host_game)
        
        # Quick join action
        join_action = network_menu.addAction("🚀 Quick Join Game")
        join_action.triggered.connect(self.quick_join_game)
    
    def open_multiplayer_lobby(self):
        """Open the network multiplayer lobby."""
        lobby = NetworkLobbyDialog(self)
        
        # Connect signals
        lobby.game_created.connect(self.on_network_game_created)
        lobby.game_joined.connect(self.on_network_game_joined)
        lobby.lobby_closed.connect(self.on_lobby_closed)
        
        # Show lobby
        lobby.exec()
    
    def quick_host_game(self):
        """Quickly host a game with default settings."""
        # Create network controller
        controller = NetworkGameController()
        
        # Try to host with default settings
        if controller.setup_as_server("localhost", 8888):
            self.on_network_game_created(controller)
        else:
            self.show_error("Failed to host game. Port may be in use.")
    
    def quick_join_game(self):
        """Quickly join a local game."""
        # This could open a simple IP/port dialog
        # For now, try to connect to localhost:8888
        controller = NetworkGameController()
        client = controller.setup_as_client("Player", "Default Deck")
        
        if client and controller.connect_to_server("localhost", 8888, "Player", "Default Deck"):
            self.on_network_game_joined(controller, client)
        else:
            self.show_error("Failed to join game. No server found.")
    
    def on_network_game_created(self, controller: NetworkGameController):
        """Handle successful game hosting."""
        self.network_controller = controller
        self.network_status.set_network_controller(controller)
        
        # Start hosting - waiting for players
        self.update_game_state("hosting")
    
    def on_network_game_joined(self, controller: NetworkGameController, client):
        """Handle successful game joining."""
        self.network_controller = controller
        self.network_client = client
        
        self.network_status.set_network_controller(controller)
        self.network_status.set_network_client(client)
        
        # Connected - waiting for game start
        self.update_game_state("connected")
    
    def on_lobby_closed(self):
        """Handle lobby dialog closing."""
        # Update UI state if needed
        pass
    
    def disconnect_network(self):
        """Disconnect from current network game."""
        if self.network_controller:
            self.network_controller.disconnect_from_network()
            self.network_controller = None
            self.network_client = None
            
            # Reset network status
            self.network_status.set_network_controller(None)
            self.network_status.set_network_client(None)
            
            self.update_game_state("single_player")
    
    def ready_for_game(self):
        """Signal that we're ready to start the multiplayer game."""
        if self.network_status.is_ready_for_game():
            # Start the actual multiplayer game
            self.start_multiplayer_game()
        else:
            self.show_error("Not enough players connected to start game.")
    
    def start_multiplayer_game(self):
        """Start the actual multiplayer game."""
        # This is where you'd integrate with your existing game logic
        # Replace your existing GameController with NetworkGameController
        
        print(f"Starting multiplayer game with {self.network_status.get_player_count()} players")
        self.update_game_state("playing")
    
    def update_game_state(self, state: str):
        """Update the game state and UI accordingly."""
        # Update window title
        if state == "hosting":
            self.setWindowTitle("MTG Commander - Hosting Multiplayer Game")
        elif state == "connected":
            self.setWindowTitle("MTG Commander - Connected to Multiplayer Game")
        elif state == "playing":
            self.setWindowTitle("MTG Commander - Multiplayer Game")
        else:
            self.setWindowTitle("MTG Commander - Single Player")
    
    def show_error(self, message: str):
        """Show an error message."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Network Error", message)
```

## 🔧 Network Status Widget Features

The NetworkStatusWidget provides:

- **Real-time status display** - Shows connection state and player count
- **Collapsible interface** - Can be minimized to save space
- **Player list** - Shows all connected players with host indication
- **Quick actions menu** - Open lobby, disconnect, ready to play
- **Progress indicators** - Shows connection progress for clients

### Widget States

1. **Not Connected** - Default state, shows "Open Lobby" option
2. **Hosting** - Shows server info and connected players
3. **Connecting** - Shows progress bar and connection status
4. **Connected** - Shows successful connection and ready option
5. **Error** - Shows error state with disconnect option

## 🌐 Network Lobby Dialog Features

The NetworkLobbyDialog provides:

- **Three-tab interface**:
  - **Host Game** - Server configuration and player settings
  - **Join Game** - Client connection and player settings  
  - **Browse Games** - Network discovery and quick join

- **Automatic discovery** - Scans local network for active games
- **Deck integration** - Uses existing deck selection system
- **Real-time status** - Shows connection progress and errors
- **Player management** - Tracks connected players for hosts

## 🎯 Integration Tips

1. **Replace GameController** - Use NetworkGameController instead of regular GameController
2. **Signal handling** - Connect all network signals to update your UI appropriately
3. **Error handling** - Always handle network errors gracefully
4. **State management** - Track whether you're in single-player or multiplayer mode
5. **UI updates** - Use the provided signals to update your game UI in real-time

## 🚀 Next Steps

With the UI components integrated, you can:

1. **Test locally** - Host and join games on the same machine
2. **Test on LAN** - Try with multiple computers on your network
3. **Add features** - Extend with chat, spectator mode, etc.
4. **Improve UI** - Customize the appearance to match your game theme

## 📝 Example Menu Integration

Add this to your existing menu system:

```python
def setup_network_menu(self):
    \"\"\"Add network options to existing menu.\"\"\"
    # Get or create File menu
    file_menu = self.menuBar().addMenu("Network")
    
    # Lobby action
    file_menu.addAction("Multiplayer Lobby", self.open_multiplayer_lobby)
    file_menu.addSeparator()
    
    # Quick actions
    file_menu.addAction("Quick Host", self.quick_host_game)
    file_menu.addAction("Quick Join", self.quick_join_game)
    file_menu.addSeparator()
    
    # Disconnect action
    disconnect_action = file_menu.addAction("Disconnect", self.disconnect_network)
    disconnect_action.setEnabled(False)  # Enable when connected
    
    # Store reference to enable/disable
    self.network_disconnect_action = disconnect_action
```

This integration guide provides everything you need to add professional multiplayer networking to your MTG Commander Game Engine!
