"""MTG Commander Game - Network Game Controller

This module extends the existing GameController to support networked multiplayer games.
It coordinates between the local game state and network events, ensuring all players
stay synchronized during gameplay.
"""

import threading
from typing import Dict, Any, Optional, List, Callable
from PySide6.QtCore import QObject, Signal

from engine.game_controller import GameController
from engine.game_state import GameState, PlayerState
from .network_client import NetworkClient, ClientState
from .game_server import GameServer, ServerState
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
        self.network_client: Optional[NetworkClient] = None
        self.game_server: Optional[GameServer] = None
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
            self.game_server = GameServer(self)
            self.game_server.set_game_controller(self)
            
            # Connect server signals
            self.game_server.player_connected.connect(self._on_server_player_joined)
            self.game_server.player_disconnected.connect(self._on_server_player_left)
            self.game_server.game_started.connect(self._on_server_game_started)
            self.game_server.game_ended.connect(self._on_server_game_ended)
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
    
    def setup_as_client(self, player_name: str, deck_name: str) -> NetworkClient:
        """Set up this controller as a network client."""
        if self.is_networked:
            return None
        
        try:
            self.network_client = NetworkClient(self.local_player_id, self)
            
            # Connect client signals
            self.network_client.connected.connect(self._on_client_connected)
            self.network_client.disconnected.connect(self._on_client_disconnected)
            self.network_client.message_received.connect(self._on_network_message)
            self.network_client.error_occurred.connect(self._on_network_error)
            self.network_client.player_joined.connect(self._on_network_player_joined)
            self.network_client.player_left.connect(self._on_network_player_left)
            self.network_client.game_started.connect(self._on_network_game_started)
            self.network_client.game_ended.connect(self._on_network_game_ended)
            
            self.is_networked = True
            return self.network_client
            
        except Exception as e:
            self.network_error.emit(f"Failed to setup client: {e}")
            return None
    
    def connect_to_server(self, host: str, port: int, player_name: str, deck_name: str) -> bool:
        """Connect to a game server."""
        if not self.network_client:
            return False
        
        if self.network_client.connect_to_server(host, port):
            self.connection_status_changed.emit(f"Connecting to {host}:{port}...")
            # Join game after connection is established
            return self.network_client.join_game(player_name, deck_name)
        
        return False
    
    def disconnect_from_network(self):
        """Disconnect from network (client or server)."""
        if self.network_client:
            self.network_client.disconnect()
            self.network_client = None
        
        if self.game_server:
            self.game_server.stop_server()
            self.game_server = None
        
        self.is_networked = False
        self.is_server = False
        self.network_players.clear()
        self.connection_status_changed.emit("Disconnected")\n    \n    # Override game controller methods for network synchronization\n    \n    def advance_phase(self):\n        \"\"\"Override phase advancement for network synchronization.\"\"\"\n        if not self.is_networked:\n            # Single player mode\n            super().advance_phase()\n            return\n        \n        if self.is_server:\n            # Server handles phase advancement\n            with self.sync_lock:\n                super().advance_phase()\n                self._broadcast_phase_change()\n        else:\n            # Client sends phase advance request\n            if self.network_client and self.network_client.is_in_game:\n                self.network_client.send_player_action(\"advance_phase\")\n    \n    def play_card(self, player_id: int, card_id: str, zone_from: str, zone_to: str, **kwargs) -> bool:\n        \"\"\"Override card playing for network synchronization.\"\"\"\n        if not self.is_networked or self.is_server:\n            # Single player or server mode - execute locally\n            result = self._execute_play_card(player_id, card_id, zone_from, zone_to, **kwargs)\n            \n            if result and self.is_server:\n                # Broadcast to clients\n                self._broadcast_play_card(player_id, card_id, zone_from, zone_to, **kwargs)\n            \n            return result\n        else:\n            # Client mode - send to server\n            if self.network_client and self.network_client.is_in_game:\n                return self.network_client.send_play_card(card_id, zone_from, zone_to, **kwargs)\n            return False\n    \n    def cast_spell(self, player_id: int, card_id: str, mana_cost: Dict[str, int], targets: List = None) -> bool:\n        \"\"\"Override spell casting for network synchronization.\"\"\"\n        if not self.is_networked or self.is_server:\n            # Single player or server mode\n            result = self._execute_cast_spell(player_id, card_id, mana_cost, targets)\n            \n            if result and self.is_server:\n                # Broadcast to clients\n                self._broadcast_cast_spell(player_id, card_id, mana_cost, targets)\n            \n            return result\n        else:\n            # Client mode - send to server\n            if self.network_client and self.network_client.is_in_game:\n                return self.network_client.send_cast_spell(card_id, mana_cost, targets)\n            return False\n    \n    def pass_priority(self, player_id: int = None):\n        \"\"\"Override priority passing for network synchronization.\"\"\"\n        if not self.is_networked or self.is_server:\n            # Single player or server mode\n            super().pass_priority(player_id)\n            \n            if self.is_server:\n                # Broadcast to clients\n                self._broadcast_pass_priority(player_id or self.game.active_player)\n        else:\n            # Client mode - send to server\n            if self.network_client and self.network_client.is_in_game:\n                self.network_client.send_player_action(\"pass_priority\", player_id=player_id)\n    \n    # Network message handling\n    \n    def _on_network_message(self, message: NetworkMessage):\n        \"\"\"Handle received network message.\"\"\"\n        if message.type in self.network_handlers:\n            try:\n                self.network_handlers[message.type](message)\n            except Exception as e:\n                self.network_error.emit(f\"Error handling {message.type.value}: {e}\")\n    \n    def _handle_game_state_update(self, message: NetworkMessage):\n        \"\"\"Handle game state update from server.\"\"\"\n        if self.is_server:\n            return  # Server doesn't receive state updates\n        \n        try:\n            state_data = message.data.get(\"state\", {})\n            self._apply_game_state_update(state_data)\n        except Exception as e:\n            self.network_error.emit(f\"Failed to apply game state update: {e}\")\n    \n    def _handle_phase_change(self, message: NetworkMessage):\n        \"\"\"Handle phase change from server.\"\"\"\n        if self.is_server:\n            return\n        \n        new_phase = message.data.get(\"new_phase\")\n        active_player = message.data.get(\"active_player\")\n        \n        if new_phase and self.game:\n            with self.sync_lock:\n                self.game.phase = new_phase\n                if active_player is not None:\n                    self.game.active_player = active_player\n                self.phase_changed.emit(new_phase, active_player)\n    \n    def _handle_network_player_action(self, message: NetworkMessage):\n        \"\"\"Handle player action from network.\"\"\"\n        player_id = message.data.get(\"player_id\")\n        action = message.data.get(\"action\")\n        \n        if not player_id or not action:\n            return\n        \n        # Execute action based on type\n        if action == \"advance_phase\" and self.is_server:\n            self.advance_phase()\n        elif action == \"pass_priority\" and self.is_server:\n            target_player = message.data.get(\"player_id\", player_id)\n            self.pass_priority(target_player)\n    \n    def _handle_network_play_card(self, message: NetworkMessage):\n        \"\"\"Handle card play from network.\"\"\"\n        player_id = message.data.get(\"player_id\")\n        card_id = message.data.get(\"card_id\")\n        zone_from = message.data.get(\"zone_from\")\n        zone_to = message.data.get(\"zone_to\")\n        \n        if all([player_id, card_id, zone_from, zone_to]):\n            # Remove player_id from kwargs to avoid duplication\n            kwargs = {k: v for k, v in message.data.items() \n                     if k not in [\"player_id\", \"card_id\", \"zone_from\", \"zone_to\"]}\n            self._execute_play_card(player_id, card_id, zone_from, zone_to, **kwargs)\n    \n    def _handle_network_cast_spell(self, message: NetworkMessage):\n        \"\"\"Handle spell cast from network.\"\"\"\n        player_id = message.data.get(\"player_id\")\n        card_id = message.data.get(\"card_id\")\n        mana_cost = message.data.get(\"mana_cost\", {})\n        targets = message.data.get(\"targets\", [])\n        \n        if player_id and card_id:\n            self._execute_cast_spell(player_id, card_id, mana_cost, targets)\n    \n    def _handle_network_pass_priority(self, message: NetworkMessage):\n        \"\"\"Handle priority pass from network.\"\"\"\n        player_id = message.data.get(\"player_id\")\n        if player_id is not None:\n            super().pass_priority(player_id)\n    \n    # Game execution methods (actual game logic)\n    \n    def _execute_play_card(self, player_id: int, card_id: str, zone_from: str, zone_to: str, **kwargs) -> bool:\n        \"\"\"Execute card play locally.\"\"\"\n        try:\n            # This would integrate with your existing card playing logic\n            # For now, just emit a signal\n            self.card_played.emit(player_id, card_id, zone_from, zone_to)\n            return True\n        except Exception as e:\n            print(f\"Error executing play card: {e}\")\n            return False\n    \n    def _execute_cast_spell(self, player_id: int, card_id: str, mana_cost: Dict[str, int], targets: List) -> bool:\n        \"\"\"Execute spell cast locally.\"\"\"\n        try:\n            # This would integrate with your existing spell casting logic\n            # For now, just emit a signal\n            self.spell_cast.emit(player_id, card_id, mana_cost, targets or [])\n            return True\n        except Exception as e:\n            print(f\"Error executing cast spell: {e}\")\n            return False\n    \n    def _apply_game_state_update(self, state_data: Dict[str, Any]):\n        \"\"\"Apply game state update from server.\"\"\"\n        if not self.game:\n            return\n        \n        # Update game state based on server data\n        # This would need to be implemented based on your GameState structure\n        with self.sync_lock:\n            # Update basic game properties\n            if \"phase\" in state_data:\n                self.game.phase = state_data[\"phase\"]\n            if \"active_player\" in state_data:\n                self.game.active_player = state_data[\"active_player\"]\n            if \"turn_number\" in state_data:\n                self.game.turn_number = state_data[\"turn_number\"]\n            \n            # Update player states\n            if \"players\" in state_data:\n                self._update_player_states(state_data[\"players\"])\n    \n    def _update_player_states(self, players_data: List[Dict[str, Any]]):\n        \"\"\"Update player states from network data.\"\"\"\n        for player_data in players_data:\n            player_id = player_data.get(\"player_id\")\n            if player_id is not None and player_id < len(self.game.players):\n                player = self.game.players[player_id]\n                \n                # Update player properties\n                if \"life\" in player_data:\n                    player.life = player_data[\"life\"]\n                if \"mana_pool\" in player_data:\n                    player.mana_pool.pool = player_data[\"mana_pool\"]\n    \n    # Network broadcasting (server-side)\n    \n    def _broadcast_phase_change(self):\n        \"\"\"Broadcast phase change to all clients.\"\"\"\n        if not self.is_server or not self.game_server:\n            return\n        \n        message = self.game_server.protocol.create_phase_change_message(\n            self.game.phase, self.game.active_player\n        )\n        self.game_server._broadcast_message(message)\n    \n    def _broadcast_play_card(self, player_id: int, card_id: str, zone_from: str, zone_to: str, **kwargs):\n        \"\"\"Broadcast card play to all clients.\"\"\"\n        if not self.is_server or not self.game_server:\n            return\n        \n        message = self.game_server.protocol.create_play_card_message(\n            card_id, zone_from, zone_to, player_id=player_id, **kwargs\n        )\n        self.game_server._broadcast_message(message)\n    \n    def _broadcast_cast_spell(self, player_id: int, card_id: str, mana_cost: Dict[str, int], targets: List):\n        \"\"\"Broadcast spell cast to all clients.\"\"\"\n        if not self.is_server or not self.game_server:\n            return\n        \n        message = self.game_server.protocol.create_cast_spell_message(\n            card_id, mana_cost, targets\n        )\n        message.data[\"player_id\"] = player_id\n        self.game_server._broadcast_message(message)\n    \n    def _broadcast_pass_priority(self, player_id: int):\n        \"\"\"Broadcast priority pass to all clients.\"\"\"\n        if not self.is_server or not self.game_server:\n            return\n        \n        message = self.game_server.protocol.create_message(MessageType.PASS_PRIORITY, {\n            \"player_id\": player_id\n        })\n        self.game_server._broadcast_message(message)\n    \n    def _broadcast_game_state(self):\n        \"\"\"Broadcast full game state to all clients.\"\"\"\n        if not self.is_server or not self.game_server or not self.game:\n            return\n        \n        state_data = self._serialize_game_state()\n        message = self.game_server.protocol.create_game_state_update_message(state_data)\n        self.game_server._broadcast_message(message)\n    \n    def _serialize_game_state(self) -> Dict[str, Any]:\n        \"\"\"Serialize current game state for network transmission.\"\"\"\n        if not self.game:\n            return {}\n        \n        return {\n            \"phase\": self.game.phase,\n            \"active_player\": self.game.active_player,\n            \"turn_number\": self.game.turn_number,\n            \"players\": [\n                {\n                    \"player_id\": player.player_id,\n                    \"life\": player.life,\n                    \"mana_pool\": player.mana_pool.pool if hasattr(player, 'mana_pool') else {},\n                    \"hand_size\": len(player.hand) if hasattr(player, 'hand') else 0\n                }\n                for player in self.game.players\n            ]\n        }\n    \n    # Signal handlers\n    \n    def _on_client_connected(self):\n        \"\"\"Handle client connection established.\"\"\"\n        self.connection_status_changed.emit(\"Connected to server\")\n    \n    def _on_client_disconnected(self):\n        \"\"\"Handle client disconnection.\"\"\"\n        self.connection_status_changed.emit(\"Disconnected from server\")\n        self.is_networked = False\n    \n    def _on_network_error(self, error_msg: str):\n        \"\"\"Handle network error.\"\"\"\n        self.network_error.emit(error_msg)\n    \n    def _on_network_player_joined(self, player_id: int, player_name: str):\n        \"\"\"Handle network player joined.\"\"\"\n        self.network_players[player_id] = {\"name\": player_name}\n        self.network_player_joined.emit(player_id, player_name)\n    \n    def _on_network_player_left(self, player_id: int, player_name: str):\n        \"\"\"Handle network player left.\"\"\"\n        self.network_players.pop(player_id, None)\n        self.network_player_left.emit(player_id, player_name)\n    \n    def _on_network_game_started(self):\n        \"\"\"Handle network game started.\"\"\"\n        self.network_game_started.emit()\n    \n    def _on_network_game_ended(self):\n        \"\"\"Handle network game ended.\"\"\"\n        self.network_game_ended.emit()\n    \n    def _on_server_player_joined(self, player_id: int, player_name: str):\n        \"\"\"Handle player joining server.\"\"\"\n        self.network_players[player_id] = {\"name\": player_name}\n        self.network_player_joined.emit(player_id, player_name)\n    \n    def _on_server_player_left(self, player_id: int, player_name: str):\n        \"\"\"Handle player leaving server.\"\"\"\n        self.network_players.pop(player_id, None)\n        self.network_player_left.emit(player_id, player_name)\n    \n    def _on_server_game_started(self):\n        \"\"\"Handle game started on server.\"\"\"\n        self.network_game_started.emit()\n    \n    def _on_server_game_ended(self):\n        \"\"\"Handle game ended on server.\"\"\"\n        self.network_game_ended.emit()\n    \n    # Properties and status\n    \n    @property\n    def network_status(self) -> str:\n        \"\"\"Get current network status.\"\"\"\n        if not self.is_networked:\n            return \"Not networked\"\n        \n        if self.is_server:\n            if self.game_server and self.game_server.is_running:\n                return f\"Server running ({self.game_server.player_count} players)\"\n            else:\n                return \"Server stopped\"\n        else:\n            if self.network_client:\n                return f\"Client {self.network_client.state.value}\"\n            else:\n                return \"Client not connected\"\n    \n    def get_network_info(self) -> Dict[str, Any]:\n        \"\"\"Get comprehensive network information.\"\"\"\n        info = {\n            \"is_networked\": self.is_networked,\n            \"is_server\": self.is_server,\n            \"status\": self.network_status,\n            \"players\": self.network_players\n        }\n        \n        if self.game_server:\n            info[\"server\"] = self.game_server.get_status_info()\n        \n        if self.network_client:\n            info[\"client\"] = self.network_client.get_status_info()\n        \n        return info
