"""MTG Commander Game - Network Module

This module provides local network multiplayer support for the MTG Commander Game Engine.
It implements a client-server architecture with reliable message passing and game state synchronization.

Components:
- MessageProtocol: Message serialization and protocol definitions
- NetworkClient: Client-side networking for connecting to game servers
- GameServer: Server-side game hosting and coordination
- NetworkGameController: Network-aware game controller
"""

__version__ = "1.0.0"
__author__ = "MTG Commander Game Team"

# Import core networking components
from .message_protocol import (
    MessageType,
    NetworkMessage,
    MessageProtocol,
    serialize_message,
    deserialize_message
)

from .network_client import NetworkClient, ClientState
from .game_server import GameServer, ServerState
from .network_game_controller import NetworkGameController

# Network configuration constants
DEFAULT_SERVER_HOST = "localhost"
DEFAULT_SERVER_PORT = 8888
MAX_PLAYERS = 4
HEARTBEAT_INTERVAL = 30  # seconds
CONNECTION_TIMEOUT = 60  # seconds
MESSAGE_TIMEOUT = 10  # seconds
RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 2  # seconds

__all__ = [
    "MessageType",
    "NetworkMessage", 
    "MessageProtocol",
    "serialize_message",
    "deserialize_message",
    "NetworkClient",
    "ClientState",
    "GameServer", 
    "ServerState",
    "NetworkGameController",
    "DEFAULT_SERVER_HOST",
    "DEFAULT_SERVER_PORT",
    "MAX_PLAYERS",
    "HEARTBEAT_INTERVAL",
    "CONNECTION_TIMEOUT",
    "MESSAGE_TIMEOUT",
    "RECONNECT_ATTEMPTS",
    "RECONNECT_DELAY"
]
