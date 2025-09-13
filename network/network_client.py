"""MTG Commander Game - Network Client

This module provides client-side networking functionality for connecting to
MTG Commander game servers and handling multiplayer communication.
"""

import socket
import threading
import time
import queue
from enum import Enum
from typing import Optional, Callable, Dict, Any
from PySide6.QtCore import QObject, Signal, QTimer

from .message_protocol import (
    NetworkMessage, MessageType, MessageProtocol,
    serialize_message, deserialize_message, validate_message
)
from . import (
    DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, CONNECTION_TIMEOUT,
    MESSAGE_TIMEOUT, RECONNECT_ATTEMPTS, RECONNECT_DELAY, HEARTBEAT_INTERVAL
)


class ClientState(Enum):
    """Network client connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    IN_GAME = "in_game"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class NetworkClient(QObject):
    """Network client for MTG Commander multiplayer games."""
    
    # Qt signals for network events
    connected = Signal()
    disconnected = Signal()
    message_received = Signal(object)  # NetworkMessage
    error_occurred = Signal(str)
    state_changed = Signal(object)  # ClientState
    player_joined = Signal(int, str)  # player_id, player_name
    player_left = Signal(int, str)    # player_id, player_name
    game_started = Signal()
    game_ended = Signal()
    
    def __init__(self, player_id: int = 0, parent=None):
        super().__init__(parent)
        
        # Client configuration
        self.player_id = player_id
        self.server_host = DEFAULT_SERVER_HOST
        self.server_port = DEFAULT_SERVER_PORT
        
        # Connection state
        self.state = ClientState.DISCONNECTED
        self.socket: Optional[socket.socket] = None
        self.protocol = MessageProtocol(player_id)
        
        # Threading
        self.receive_thread: Optional[threading.Thread] = None
        self.send_queue = queue.Queue()
        self.running = False
        
        # Reconnection
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = RECONNECT_ATTEMPTS
        self.reconnect_delay = RECONNECT_DELAY
        
        # Heartbeat
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)
        self.last_heartbeat = 0
        
        # Message handling
        self.message_handlers = {
            MessageType.PLAYER_JOINED: self._handle_player_joined,
            MessageType.PLAYER_LEFT: self._handle_player_left,
            MessageType.GAME_START: self._handle_game_start,
            MessageType.GAME_END: self._handle_game_end,
            MessageType.ERROR: self._handle_error,
            MessageType.HEARTBEAT: self._handle_heartbeat
        }
    
    def connect_to_server(self, host: str = None, port: int = None) -> bool:
        """Connect to game server."""
        if self.state in [ClientState.CONNECTED, ClientState.CONNECTING]:
            return False
        
        self.server_host = host or self.server_host
        self.server_port = port or self.server_port
        
        self._set_state(ClientState.CONNECTING)
        
        try:
            # Create socket and connect
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(CONNECTION_TIMEOUT)
            self.socket.connect((self.server_host, self.server_port))
            
            # Start networking threads
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Start heartbeat
            self.heartbeat_timer.start(HEARTBEAT_INTERVAL * 1000)
            
            self._set_state(ClientState.CONNECTED)
            self.connected.emit()
            return True
            
        except Exception as e:
            self._handle_connection_error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server."""
        if self.state == ClientState.DISCONNECTED:
            return
        
        # Send disconnect message
        if self.state in [ClientState.CONNECTED, ClientState.AUTHENTICATED, ClientState.IN_GAME]:
            disconnect_msg = self.protocol.create_message(MessageType.DISCONNECT, {})
            self._send_message_direct(disconnect_msg)
        
        self._cleanup_connection()
        self._set_state(ClientState.DISCONNECTED)
        self.disconnected.emit()
    
    def join_game(self, player_name: str, deck_name: str) -> bool:
        """Join a game on the server."""
        if self.state != ClientState.CONNECTED:
            return False
        
        try:
            message = self.protocol.create_join_game_message(player_name, deck_name)
            return self.send_message(message)
        except Exception as e:
            self.error_occurred.emit(f"Failed to join game: {e}")
            return False
    
    def send_message(self, message: NetworkMessage) -> bool:
        """Send a message to the server."""
        if self.state == ClientState.DISCONNECTED:
            return False
        
        try:
            self.send_queue.put(message, timeout=1.0)
            return True
        except queue.Full:
            self.error_occurred.emit("Send queue full - message dropped")
            return False
    
    def send_player_action(self, action: str, **kwargs) -> bool:
        """Send a player action to the server."""
        message = self.protocol.create_player_action_message(action, **kwargs)
        return self.send_message(message)
    
    def send_play_card(self, card_id: str, zone_from: str, zone_to: str, **kwargs) -> bool:
        """Send a play card action."""
        message = self.protocol.create_play_card_message(card_id, zone_from, zone_to, **kwargs)
        return self.send_message(message)
    
    def send_cast_spell(self, card_id: str, mana_cost: Dict[str, int], targets: list = None) -> bool:
        """Send a cast spell action."""
        message = self.protocol.create_cast_spell_message(card_id, mana_cost, targets)
        return self.send_message(message)
    
    def _receive_loop(self):
        """Main receive loop running in separate thread."""
        buffer = b""
        
        while self.running and self.socket:
            try:
                # Receive data
                data = self.socket.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                # Process complete messages
                while len(buffer) >= 4:
                    # Read message length
                    length = int.from_bytes(buffer[:4], byteorder='big')
                    
                    # Check if we have complete message
                    if len(buffer) < 4 + length:
                        break
                    
                    # Extract message data
                    message_data = buffer[:4+length]
                    buffer = buffer[4+length:]
                    
                    # Deserialize and handle message
                    try:
                        message = deserialize_message(message_data)
                        self._handle_received_message(message)
                    except Exception as e:
                        self.error_occurred.emit(f"Failed to process message: {e}")
                
                # Process send queue
                self._process_send_queue()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self._handle_connection_error(f"Receive error: {e}")
                break
        
        # Connection closed
        if self.running:
            self._handle_connection_lost()
    
    def _process_send_queue(self):
        """Process outgoing messages from send queue."""
        try:
            while not self.send_queue.empty():
                message = self.send_queue.get_nowait()
                self._send_message_direct(message)
        except queue.Empty:
            pass
        except Exception as e:
            self.error_occurred.emit(f"Send error: {e}")
    
    def _send_message_direct(self, message: NetworkMessage) -> bool:
        """Send message directly to socket."""
        if not self.socket or not self.running:
            return False
        
        try:
            data = serialize_message(message)
            self.socket.sendall(data)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to send message: {e}")
            return False
    
    def _handle_received_message(self, message: NetworkMessage):
        """Handle a received message."""
        # Validate message
        if not validate_message(message):
            self.error_occurred.emit("Received invalid message")
            return
        
        # Handle with specific handler if available
        if message.type in self.message_handlers:
            self.message_handlers[message.type](message)
        
        # Emit general message signal
        self.message_received.emit(message)
    
    def _handle_player_joined(self, message: NetworkMessage):
        """Handle PLAYER_JOINED message."""
        player_id = message.data.get("player_id")
        player_name = message.data.get("player_name")
        if player_id is not None and player_name:
            self.player_joined.emit(player_id, player_name)
    
    def _handle_player_left(self, message: NetworkMessage):
        """Handle PLAYER_LEFT message."""
        player_id = message.data.get("player_id")
        player_name = message.data.get("player_name", "Unknown")
        if player_id is not None:
            self.player_left.emit(player_id, player_name)
    
    def _handle_game_start(self, message: NetworkMessage):
        """Handle GAME_START message."""
        self._set_state(ClientState.IN_GAME)
        self.game_started.emit()
    
    def _handle_game_end(self, message: NetworkMessage):
        """Handle GAME_END message."""
        self._set_state(ClientState.AUTHENTICATED)
        self.game_ended.emit()
    
    def _handle_error(self, message: NetworkMessage):
        """Handle ERROR message."""
        error_msg = message.data.get("error_message", "Unknown error")
        self.error_occurred.emit(f"Server error: {error_msg}")
    
    def _handle_heartbeat(self, message: NetworkMessage):
        """Handle HEARTBEAT message."""
        self.last_heartbeat = time.time()
    
    def _send_heartbeat(self):
        """Send heartbeat message to server."""
        if self.state in [ClientState.CONNECTED, ClientState.AUTHENTICATED, ClientState.IN_GAME]:
            heartbeat = self.protocol.create_heartbeat_message()
            self.send_message(heartbeat)
    
    def _handle_connection_error(self, error_msg: str):
        """Handle connection error."""
        self.error_occurred.emit(error_msg)
        self._set_state(ClientState.ERROR)
        self._attempt_reconnection()
    
    def _handle_connection_lost(self):
        """Handle lost connection."""
        if self.state != ClientState.DISCONNECTED:
            self._set_state(ClientState.RECONNECTING)
            self._attempt_reconnection()
    
    def _attempt_reconnection(self):
        """Attempt to reconnect to server."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self._cleanup_connection()
            self._set_state(ClientState.DISCONNECTED)
            self.disconnected.emit()
            return
        
        self.reconnect_attempts += 1
        self.error_occurred.emit(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        # Wait before reconnecting
        time.sleep(self.reconnect_delay)
        
        # Try to reconnect
        if self.connect_to_server():
            self.reconnect_attempts = 0
        else:
            self._attempt_reconnection()
    
    def _cleanup_connection(self):
        """Clean up connection resources."""
        self.running = False
        
        # Stop heartbeat
        self.heartbeat_timer.stop()
        
        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Wait for threads to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        
        # Clear send queue
        while not self.send_queue.empty():
            try:
                self.send_queue.get_nowait()
            except queue.Empty:
                break
    
    def _set_state(self, new_state: ClientState):
        """Set client state and emit signal."""
        if self.state != new_state:
            self.state = new_state
            self.state_changed.emit(new_state)
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self.state in [ClientState.CONNECTED, ClientState.AUTHENTICATED, ClientState.IN_GAME]
    
    @property
    def is_in_game(self) -> bool:
        """Check if client is in an active game."""
        return self.state == ClientState.IN_GAME
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get client status information."""
        return {
            "state": self.state.value,
            "connected": self.is_connected,
            "in_game": self.is_in_game,
            "server": f"{self.server_host}:{self.server_port}",
            "player_id": self.player_id,
            "reconnect_attempts": self.reconnect_attempts,
            "last_heartbeat": self.last_heartbeat
        }
