"""MTG Commander Game - Network Game Controller

This module extends the existing GameController to support networked multiplayer games.
It coordinates between the local game state and network events, ensuring all players
stay synchronized during gameplay.
"""

import threading
from typing import Dict, Any, Optional, List, Callable
from PySide6.QtCore import QObject, Signal

# Import the existing game controller
try:
    from engine.game_controller import GameController
except ImportError:
    # Fallback if GameController doesn't exist
    class GameController(QObject):
        def __init__(self, parent=None, ai_ids=None):
            super().__init__(parent)
            self.ai_ids = ai_ids or []
        
        def advance_phase(self):
            pass
        
        def pass_priority(self, player_id=None):
            pass

from .message_protocol import MessageType, NetworkMessage


class NetworkGameController(GameController):
    """Network-aware game controller for multiplayer MTG games."""
    
    # Additional network signals
    network_player_joined = Signal(int, str)    # player_id, name
    network_player_left = Signal(int, str)      # player_id, name
    network_game_started = Signal()
    network_game_ended = Signal()
    network_error = Signal(str)
    connection_status_changed = Signal(str)     # status message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Network components
        self.network_client: Optional['NetworkClient'] = None
        self.game_server: Optional['GameServer'] = None
        self.is_server = False
        self.is_networked = False
        
        # Network state
        self.local_player_id = 0
        self.network_players: Dict[int, Dict[str, Any]] = {}
        self.pending_actions = []
        
        # Synchronization
        self.sync_lock = threading.RLock()
        self.awaiting_server_confirmation = False
        
        # Message handlers
        self.network_handlers = {
            MessageType.GAME_STATE_UPDATE: self._handle_game_state_update,
            MessageType.PHASE_CHANGE: self._handle_phase_change,
            MessageType.PLAYER_ACTION: self._handle_network_player_action,
            MessageType.PLAY_CARD: self._handle_network_play_card,
            MessageType.CAST_SPELL: self._handle_network_cast_spell,
            MessageType.PASS_PRIORITY: self._handle_network_pass_priority
        }
    
    def setup_as_server(self, host: str = "localhost", port: int = 8888) -> bool:
        """Set up this controller as a game server."""
        if self.is_networked:
            return False
        
        try:
            # Lazy import to avoid circular dependencies
            from .game_server import GameServer
            
            self.game_server = GameServer(self)
            
            # Connect server signals if they exist
            if hasattr(self.game_server, 'player_connected'):
                self.game_server.player_connected.connect(self._on_server_player_joined)
            if hasattr(self.game_server, 'player_disconnected'):
                self.game_server.player_disconnected.connect(self._on_server_player_left)
            if hasattr(self.game_server, 'error_occurred'):
                self.game_server.error_occurred.connect(self._on_network_error)
            
            if self.game_server.start_server(host, port):
                self.is_server = True
                self.is_networked = True
                self.connection_status_changed.emit(f"Server running on {host}:{port}")
                return True
            
            return False
            
        except Exception as e:
            self.network_error.emit(f"Failed to setup server: {e}")
            return False
    
    def setup_as_client(self, player_name: str, deck_name: str):
        """Set up this controller as a network client."""
        if self.is_networked:
            return None
        
        try:
            # Lazy import to avoid circular dependencies
            from .network_client import NetworkClient
            
            self.network_client = NetworkClient(self.local_player_id, self)
            
            # Connect client signals if they exist
            if hasattr(self.network_client, 'connected'):
                self.network_client.connected.connect(self._on_client_connected)
            if hasattr(self.network_client, 'disconnected'):
                self.network_client.disconnected.connect(self._on_client_disconnected)
            if hasattr(self.network_client, 'error_occurred'):
                self.network_client.error_occurred.connect(self._on_network_error)
            
            self.is_networked = True
            return self.network_client
            
        except Exception as e:
            self.network_error.emit(f"Failed to setup client: {e}")
            return None
    
    def connect_to_server(self, host: str, port: int, player_name: str, deck_name: str) -> bool:
        """Connect to a game server."""
        if not self.network_client:
            return False
        
        try:
            if hasattr(self.network_client, 'connect_to_server'):
                if self.network_client.connect_to_server(host, port):
                    self.connection_status_changed.emit(f"Connecting to {host}:{port}...")
                    return True
            return False
        except Exception as e:
            self.network_error.emit(f"Failed to connect: {e}")
            return False
    
    def disconnect_from_network(self):
        """Disconnect from network (client or server)."""
        try:
            if self.network_client:
                if hasattr(self.network_client, 'disconnect'):
                    self.network_client.disconnect()
                self.network_client = None
            
            if self.game_server:
                if hasattr(self.game_server, 'stop_server'):
                    self.game_server.stop_server()
                self.game_server = None
            
            self.is_networked = False
            self.is_server = False
            self.network_players.clear()
            self.connection_status_changed.emit("Disconnected")
        except Exception as e:
            self.network_error.emit(f"Error during disconnect: {e}")
    
    # Override game controller methods for network synchronization
    
    def advance_phase(self):
        """Override phase advancement for network synchronization."""
        if not self.is_networked:
            # Single player mode
            super().advance_phase()
            return
        
        if self.is_server:
            # Server handles phase advancement
            with self.sync_lock:
                super().advance_phase()
                self._broadcast_phase_change()
        else:
            # Client sends phase advance request
            if self.network_client and hasattr(self.network_client, 'send_player_action'):
                self.network_client.send_player_action("advance_phase")
    
    def play_card(self, player_id: int, card_id: str, zone_from: str, zone_to: str, **kwargs) -> bool:
        """Override card playing for network synchronization."""
        if not self.is_networked or self.is_server:
            # Single player or server mode - execute locally
            result = self._execute_play_card(player_id, card_id, zone_from, zone_to, **kwargs)
            
            if result and self.is_server:
                # Broadcast to clients
                self._broadcast_play_card(player_id, card_id, zone_from, zone_to, **kwargs)
            
            return result
        else:
            # Client mode - send to server
            if self.network_client and hasattr(self.network_client, 'send_play_card'):
                return self.network_client.send_play_card(card_id, zone_from, zone_to, **kwargs)
            return False
    
    def pass_priority(self, player_id: int = None):
        """Override priority passing for network synchronization."""
        if not self.is_networked or self.is_server:
            # Single player or server mode
            super().pass_priority(player_id)
            
            if self.is_server:
                # Broadcast to clients
                self._broadcast_pass_priority(player_id or 0)
        else:
            # Client mode - send to server
            if self.network_client and hasattr(self.network_client, 'send_player_action'):
                self.network_client.send_player_action("pass_priority", player_id=player_id)
    
    # Network message handling
    
    def _on_network_message(self, message: NetworkMessage):
        """Handle received network message."""
        if message.type in self.network_handlers:
            try:
                self.network_handlers[message.type](message)
            except Exception as e:
                self.network_error.emit(f"Error handling {message.type.value}: {e}")
    
    def _handle_game_state_update(self, message: NetworkMessage):
        """Handle game state update from server."""
        if self.is_server:
            return  # Server doesn't receive state updates
        
        try:
            state_data = message.data.get("state", {})
            self._apply_game_state_update(state_data)
        except Exception as e:
            self.network_error.emit(f"Failed to apply game state update: {e}")
    
    def _handle_phase_change(self, message: NetworkMessage):
        """Handle phase change from server."""
        if self.is_server:
            return
        
        new_phase = message.data.get("new_phase")
        active_player = message.data.get("active_player")
        
        if new_phase:
            with self.sync_lock:
                # Update phase - would need to integrate with actual game state
                print(f"Phase changed to {new_phase}, active player: {active_player}")
    
    def _handle_network_player_action(self, message: NetworkMessage):
        """Handle player action from network."""
        player_id = message.data.get("player_id")
        action = message.data.get("action")
        
        if not player_id or not action:
            return
        
        # Execute action based on type
        if action == "advance_phase" and self.is_server:
            self.advance_phase()
        elif action == "pass_priority" and self.is_server:
            target_player = message.data.get("player_id", player_id)
            self.pass_priority(target_player)
    
    def _handle_network_play_card(self, message: NetworkMessage):
        """Handle card play from network."""
        player_id = message.data.get("player_id")
        card_id = message.data.get("card_id")
        zone_from = message.data.get("zone_from")
        zone_to = message.data.get("zone_to")
        
        if all([player_id, card_id, zone_from, zone_to]):
            kwargs = {k: v for k, v in message.data.items() 
                     if k not in ["player_id", "card_id", "zone_from", "zone_to"]}
            self._execute_play_card(player_id, card_id, zone_from, zone_to, **kwargs)
    
    def _handle_network_cast_spell(self, message: NetworkMessage):
        """Handle spell cast from network."""
        player_id = message.data.get("player_id")
        card_id = message.data.get("card_id")
        mana_cost = message.data.get("mana_cost", {})
        targets = message.data.get("targets", [])
        
        if player_id and card_id:
            self._execute_cast_spell(player_id, card_id, mana_cost, targets)
    
    def _handle_network_pass_priority(self, message: NetworkMessage):
        """Handle priority pass from network."""
        player_id = message.data.get("player_id")
        if player_id is not None:
            super().pass_priority(player_id)
    
    # Game execution methods (actual game logic)
    
    def _execute_play_card(self, player_id: int, card_id: str, zone_from: str, zone_to: str, **kwargs) -> bool:
        """Execute card play locally."""
        try:
            # This would integrate with your existing card playing logic
            # For now, just log the action
            print(f"Player {player_id} played card {card_id} from {zone_from} to {zone_to}")
            return True
        except Exception as e:
            print(f"Error executing play card: {e}")
            return False
    
    def _execute_cast_spell(self, player_id: int, card_id: str, mana_cost: Dict[str, int], targets: List) -> bool:
        """Execute spell cast locally."""
        try:
            # This would integrate with your existing spell casting logic
            print(f"Player {player_id} cast spell {card_id} with cost {mana_cost}")
            return True
        except Exception as e:
            print(f"Error executing cast spell: {e}")
            return False
    
    def _apply_game_state_update(self, state_data: Dict[str, Any]):
        """Apply game state update from server."""
        # This would need to be implemented based on your GameState structure
        with self.sync_lock:
            print(f"Applying game state update: {state_data}")
    
    # Network broadcasting (server-side)
    
    def _broadcast_phase_change(self):
        """Broadcast phase change to all clients."""
        if not self.is_server or not self.game_server:
            return
        
        try:
            if hasattr(self.game_server, 'protocol') and hasattr(self.game_server, '_broadcast_message'):
                message = self.game_server.protocol.create_phase_change_message("main_phase", 0)
                self.game_server._broadcast_message(message)
        except Exception as e:
            print(f"Error broadcasting phase change: {e}")
    
    def _broadcast_play_card(self, player_id: int, card_id: str, zone_from: str, zone_to: str, **kwargs):
        """Broadcast card play to all clients."""
        if not self.is_server or not self.game_server:
            return
        
        try:
            if hasattr(self.game_server, 'protocol') and hasattr(self.game_server, '_broadcast_message'):
                message = self.game_server.protocol.create_play_card_message(
                    card_id, zone_from, zone_to, player_id=player_id, **kwargs
                )
                self.game_server._broadcast_message(message)
        except Exception as e:
            print(f"Error broadcasting play card: {e}")
    
    def _broadcast_pass_priority(self, player_id: int):
        """Broadcast priority pass to all clients."""
        if not self.is_server or not self.game_server:
            return
        
        try:
            if hasattr(self.game_server, 'protocol') and hasattr(self.game_server, '_broadcast_message'):
                message = self.game_server.protocol.create_message(MessageType.PASS_PRIORITY, {
                    "player_id": player_id
                })
                self.game_server._broadcast_message(message)
        except Exception as e:
            print(f"Error broadcasting pass priority: {e}")
    
    # Signal handlers
    
    def _on_client_connected(self):
        """Handle client connection established."""
        self.connection_status_changed.emit("Connected to server")
    
    def _on_client_disconnected(self):
        """Handle client disconnection."""
        self.connection_status_changed.emit("Disconnected from server")
        self.is_networked = False
    
    def _on_network_error(self, error_msg: str):
        """Handle network error."""
        self.network_error.emit(error_msg)
    
    def _on_network_player_joined(self, player_id: int, player_name: str):
        """Handle network player joined."""
        self.network_players[player_id] = {"name": player_name}
        self.network_player_joined.emit(player_id, player_name)
    
    def _on_network_player_left(self, player_id: int, player_name: str):
        """Handle network player left."""
        self.network_players.pop(player_id, None)
        self.network_player_left.emit(player_id, player_name)
    
    def _on_server_player_joined(self, player_id: int, player_name: str):
        """Handle player joining server."""
        self.network_players[player_id] = {"name": player_name}
        self.network_player_joined.emit(player_id, player_name)
    
    def _on_server_player_left(self, player_id: int, player_name: str):
        """Handle player leaving server."""
        self.network_players.pop(player_id, None)
        self.network_player_left.emit(player_id, player_name)
    
    # Properties and status
    
    @property
    def network_status(self) -> str:
        """Get current network status."""
        if not self.is_networked:
            return "Not networked"
        
        if self.is_server:
            if self.game_server and hasattr(self.game_server, 'is_running') and self.game_server.is_running:
                player_count = getattr(self.game_server, 'player_count', len(self.network_players))
                return f"Server running ({player_count} players)"
            else:
                return "Server stopped"
        else:
            if self.network_client and hasattr(self.network_client, 'state'):
                return f"Client {self.network_client.state.value}"
            else:
                return "Client not connected"
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get comprehensive network information."""
        info = {
            "is_networked": self.is_networked,
            "is_server": self.is_server,
            "status": self.network_status,
            "players": self.network_players
        }
        
        if self.game_server and hasattr(self.game_server, 'get_status_info'):
            try:
                info["server"] = self.game_server.get_status_info()
            except:
                info["server"] = {"status": "unknown"}
        
        if self.network_client and hasattr(self.network_client, 'get_status_info'):
            try:
                info["client"] = self.network_client.get_status_info()
            except:
                info["client"] = {"status": "unknown"}
        
        return info
