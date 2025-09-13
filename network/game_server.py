"""MTG Commander Game - Game Server

This module provides server-side functionality for hosting MTG Commander
multiplayer games. It manages player connections, game state, and coordinates
game logic across all connected clients.
"""

import socket
import threading
import time
import json
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from PySide6.QtCore import QObject, Signal, QTimer

from .message_protocol import (
    NetworkMessage, MessageType, MessageProtocol,
    serialize_message, deserialize_message, validate_message
)
from . import DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, MAX_PLAYERS, HEARTBEAT_INTERVAL


class ServerState(Enum):
    """Game server states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    IN_GAME = "in_game"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ConnectedPlayer:
    """Information about a connected player."""
    player_id: int
    socket: socket.socket
    name: str = "Unknown"
    deck_name: str = ""
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    authenticated: bool = False
    ready: bool = False


class GameServer(QObject):
    """Game server for MTG Commander multiplayer games."""
    
    # Qt signals for server events
    server_started = Signal()
    server_stopped = Signal()
    player_connected = Signal(int, str)    # player_id, name
    player_disconnected = Signal(int, str) # player_id, name
    game_started = Signal()
    game_ended = Signal()
    error_occurred = Signal(str)
    state_changed = Signal(object)  # ServerState
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Server configuration
        self.host = DEFAULT_SERVER_HOST
        self.port = DEFAULT_SERVER_PORT
        self.max_players = MAX_PLAYERS
        
        # Server state
        self.state = ServerState.STOPPED
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        
        # Connected players
        self.players: Dict[int, ConnectedPlayer] = {}
        self.next_player_id = 1
        
        # Game state management
        self.game_controller = None
        self.game_active = False
        self.protocol = MessageProtocol(0)  # Server uses player_id 0
        
        # Threading
        self.accept_thread: Optional[threading.Thread] = None
        self.client_threads: Dict[int, threading.Thread] = {}
        
        # Heartbeat monitoring
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._check_heartbeats)
        
        # Message handlers
        self.message_handlers = {
            MessageType.JOIN_GAME: self._handle_join_game,
            MessageType.DISCONNECT: self._handle_disconnect,
            MessageType.HEARTBEAT: self._handle_heartbeat,
            MessageType.PLAYER_ACTION: self._handle_player_action,
            MessageType.PLAY_CARD: self._handle_play_card,
            MessageType.CAST_SPELL: self._handle_cast_spell,
            MessageType.PASS_PRIORITY: self._handle_pass_priority
        }
    
    def start_server(self, host: str = None, port: int = None) -> bool:
        """Start the game server."""
        if self.state != ServerState.STOPPED:
            return False
        
        self.host = host or self.host
        self.port = port or self.port
        
        self._set_state(ServerState.STARTING)
        
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_players)
            
            # Start accepting connections
            self.running = True
            self.accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self.accept_thread.start()
            
            # Start heartbeat monitoring
            self.heartbeat_timer.start(HEARTBEAT_INTERVAL * 1000)
            
            self._set_state(ServerState.RUNNING)
            self.server_started.emit()
            
            print(f"🎮 MTG Server started on {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to start server: {e}")
            self._set_state(ServerState.ERROR)
            return False
    
    def stop_server(self):
        """Stop the game server."""
        if self.state == ServerState.STOPPED:
            return
        
        self._set_state(ServerState.STOPPING)
        
        # Stop accepting new connections
        self.running = False
        
        # Disconnect all players
        for player_id in list(self.players.keys()):
            self._disconnect_player(player_id)
        
        # Stop heartbeat monitoring
        self.heartbeat_timer.stop()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        # Wait for threads to finish
        if self.accept_thread and self.accept_thread.is_alive():
            self.accept_thread.join(timeout=2.0)
        
        for thread in self.client_threads.values():
            if thread.is_alive():
                thread.join(timeout=1.0)
        self.client_threads.clear()
        
        self._set_state(ServerState.STOPPED)
        self.server_stopped.emit()
        print("🛑 MTG Server stopped")
    
    def set_game_controller(self, controller):
        """Set the game controller for managing game logic."""
        self.game_controller = controller
    
    def start_game(self) -> bool:
        """Start a game with connected players."""
        if self.state != ServerState.RUNNING or len(self.players) < 2:
            return False
        
        # Check if all players are ready
        ready_players = [p for p in self.players.values() if p.ready]
        if len(ready_players) != len(self.players):
            return False
        
        self.game_active = True
        self._set_state(ServerState.IN_GAME)
        
        # Notify all players that game is starting
        start_message = self.protocol.create_message(MessageType.GAME_START, {
            "players": [{"id": p.player_id, "name": p.name} for p in self.players.values()]
        })
        self._broadcast_message(start_message)
        
        self.game_started.emit()
        print(f"🎮 Game started with {len(self.players)} players")
        return True
    
    def end_game(self):
        """End the current game."""
        if not self.game_active:
            return
        
        self.game_active = False
        self._set_state(ServerState.RUNNING)
        
        # Notify all players that game ended
        end_message = self.protocol.create_message(MessageType.GAME_END, {})
        self._broadcast_message(end_message)
        
        # Reset player ready states
        for player in self.players.values():
            player.ready = False
        
        self.game_ended.emit()
        print("🏁 Game ended")
    
    def _accept_connections(self):
        """Accept new client connections."""
        while self.running and self.server_socket:
            try:
                client_socket, address = self.server_socket.accept()
                
                if len(self.players) >= self.max_players:
                    # Server full
                    error_msg = self.protocol.create_error_message("SERVER_FULL", "Server is full")
                    self._send_message_to_socket(client_socket, error_msg)
                    client_socket.close()
                    continue
                
                # Create new player
                player_id = self.next_player_id
                self.next_player_id += 1
                
                player = ConnectedPlayer(
                    player_id=player_id,
                    socket=client_socket
                )
                
                self.players[player_id] = player
                
                # Start client handler thread
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(player,),
                    daemon=True
                )
                self.client_threads[player_id] = thread
                thread.start()
                
                print(f"👤 Player {player_id} connected from {address}")
                
            except Exception as e:
                if self.running:
                    self.error_occurred.emit(f"Accept connection error: {e}")
    
    def _handle_client(self, player: ConnectedPlayer):
        """Handle communication with a specific client."""
        buffer = b""
        
        while self.running and player.player_id in self.players:
            try:
                # Receive data
                data = player.socket.recv(4096)
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
                        self._handle_client_message(player, message)
                    except Exception as e:
                        print(f"⚠️ Failed to process message from player {player.player_id}: {e}")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ Client {player.player_id} communication error: {e}")
                break
        
        # Client disconnected
        self._disconnect_player(player.player_id)
    
    def _handle_client_message(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle a message from a client."""
        # Validate message
        if not validate_message(message):
            error_msg = self.protocol.create_error_message("INVALID_MESSAGE", "Invalid message format")
            self._send_message_to_player(player.player_id, error_msg)
            return
        
        # Update last activity
        player.last_heartbeat = time.time()
        
        # Handle with specific handler
        if message.type in self.message_handlers:
            self.message_handlers[message.type](player, message)
        else:
            print(f"⚠️ Unhandled message type: {message.type}")
    
    def _handle_join_game(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle JOIN_GAME message."""
        player_name = message.data.get("player_name", f"Player{player.player_id}")
        deck_name = message.data.get("deck_name", "Unknown Deck")
        
        player.name = player_name
        player.deck_name = deck_name
        player.authenticated = True
        
        # Notify this player they joined successfully
        joined_msg = self.protocol.create_message(MessageType.PLAYER_JOINED, {
            "player_id": player.player_id,
            "player_name": player_name,
            "success": True
        })
        self._send_message_to_player(player.player_id, joined_msg)
        
        # Notify other players
        for other_id, other_player in self.players.items():
            if other_id != player.player_id and other_player.authenticated:
                notify_msg = self.protocol.create_message(MessageType.PLAYER_JOINED, {
                    "player_id": player.player_id,
                    "player_name": player_name
                })
                self._send_message_to_player(other_id, notify_msg)
        
        self.player_connected.emit(player.player_id, player_name)
        print(f"✅ Player {player.player_id} ({player_name}) joined the game")
    
    def _handle_disconnect(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle DISCONNECT message."""
        self._disconnect_player(player.player_id)
    
    def _handle_heartbeat(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle HEARTBEAT message."""
        player.last_heartbeat = time.time()
        
        # Send heartbeat response
        response = self.protocol.create_heartbeat_message()
        self._send_message_to_player(player.player_id, response)
    
    def _handle_player_action(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle PLAYER_ACTION message."""
        if not self.game_active or not self.game_controller:
            return
        
        action = message.data.get("action")
        if not action:
            return
        
        # Forward to game controller and broadcast result
        try:
            # This would integrate with your existing game controller
            # For now, just broadcast the action to other players
            action_msg = self.protocol.create_message(MessageType.PLAYER_ACTION, {
                "player_id": player.player_id,
                "action": action,
                **message.data
            })
            self._broadcast_message(action_msg, exclude_player=player.player_id)
            
        except Exception as e:
            error_msg = self.protocol.create_error_message("ACTION_FAILED", str(e))
            self._send_message_to_player(player.player_id, error_msg)
    
    def _handle_play_card(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle PLAY_CARD message."""
        if not self.game_active:
            return
        
        # Broadcast card play to other players
        play_msg = self.protocol.create_message(MessageType.PLAY_CARD, {
            "player_id": player.player_id,
            **message.data
        })
        self._broadcast_message(play_msg, exclude_player=player.player_id)
    
    def _handle_cast_spell(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle CAST_SPELL message."""
        if not self.game_active:
            return
        
        # Broadcast spell cast to other players
        cast_msg = self.protocol.create_message(MessageType.CAST_SPELL, {
            "player_id": player.player_id,
            **message.data
        })
        self._broadcast_message(cast_msg, exclude_player=player.player_id)
    
    def _handle_pass_priority(self, player: ConnectedPlayer, message: NetworkMessage):
        """Handle PASS_PRIORITY message."""
        if not self.game_active:
            return
        
        # Broadcast priority pass
        priority_msg = self.protocol.create_message(MessageType.PASS_PRIORITY, {
            "player_id": player.player_id
        })
        self._broadcast_message(priority_msg, exclude_player=player.player_id)
    
    def _disconnect_player(self, player_id: int):
        """Disconnect a player from the server."""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        
        # Close socket
        try:
            player.socket.close()
        except:
            pass
        
        # Notify other players
        if player.authenticated:
            disconnect_msg = self.protocol.create_message(MessageType.PLAYER_LEFT, {
                "player_id": player_id,
                "player_name": player.name
            })
            self._broadcast_message(disconnect_msg, exclude_player=player_id)
            
            self.player_disconnected.emit(player_id, player.name)
        
        # Remove from players
        del self.players[player_id]
        
        # Clean up thread
        if player_id in self.client_threads:
            del self.client_threads[player_id]
        
        print(f"👋 Player {player_id} ({player.name}) disconnected")
        
        # End game if no players left
        if self.game_active and len(self.players) == 0:
            self.end_game()
    
    def _send_message_to_player(self, player_id: int, message: NetworkMessage) -> bool:
        """Send a message to a specific player."""
        if player_id not in self.players:
            return False
        
        return self._send_message_to_socket(self.players[player_id].socket, message)
    
    def _send_message_to_socket(self, sock: socket.socket, message: NetworkMessage) -> bool:
        """Send a message to a socket."""
        try:
            data = serialize_message(message)
            sock.sendall(data)
            return True
        except Exception as e:
            print(f"⚠️ Failed to send message: {e}")
            return False
    
    def _broadcast_message(self, message: NetworkMessage, exclude_player: int = None):
        """Broadcast a message to all connected players."""
        for player_id, player in self.players.items():
            if exclude_player and player_id == exclude_player:
                continue
            if player.authenticated:
                self._send_message_to_socket(player.socket, message)
    
    def _check_heartbeats(self):
        """Check for inactive players and disconnect them."""
        current_time = time.time()
        timeout = HEARTBEAT_INTERVAL * 2  # 2x heartbeat interval
        
        inactive_players = []
        for player_id, player in self.players.items():
            if current_time - player.last_heartbeat > timeout:
                inactive_players.append(player_id)
        
        for player_id in inactive_players:
            print(f"⏰ Player {player_id} timed out")
            self._disconnect_player(player_id)
    
    def _set_state(self, new_state: ServerState):
        """Set server state and emit signal."""
        if self.state != new_state:
            self.state = new_state
            self.state_changed.emit(new_state)
    
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.state in [ServerState.RUNNING, ServerState.IN_GAME]
    
    @property
    def player_count(self) -> int:
        """Get number of connected players."""
        return len(self.players)
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get server status information."""
        return {
            "state": self.state.value,
            "running": self.is_running,
            "address": f"{self.host}:{self.port}",
            "player_count": self.player_count,
            "max_players": self.max_players,
            "game_active": self.game_active,
            "players": [
                {
                    "id": p.player_id,
                    "name": p.name,
                    "deck": p.deck_name,
                    "ready": p.ready,
                    "connected_at": p.connected_at
                }
                for p in self.players.values()
            ]
        }
