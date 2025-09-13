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

# Network configuration constants (define first to avoid circular imports)
DEFAULT_SERVER_HOST = "localhost"
DEFAULT_SERVER_PORT = 8888
MAX_PLAYERS = 4
HEARTBEAT_INTERVAL = 30  # seconds
CONNECTION_TIMEOUT = 60  # seconds
MESSAGE_TIMEOUT = 10  # seconds
RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 2  # seconds

# Import core networking components
from .message_protocol import (
    MessageType,
    NetworkMessage,
    MessageProtocol,
    serialize_message,
    deserialize_message
)

# Lazy import to avoid circular dependencies
def _get_network_client():
    from .network_client import NetworkClient, ClientState
    return NetworkClient, ClientState

def _get_game_server():
    from .game_server import GameServer, ServerState
    return GameServer, ServerState

def _get_network_game_controller():
    from .network_game_controller import NetworkGameController
    return NetworkGameController

# Try to import components, but don't fail if there are issues
try:
    from .network_client import NetworkClient, ClientState
except ImportError:
    NetworkClient, ClientState = None, None

try:
    from .game_server import GameServer, ServerState
except ImportError:
    GameServer, ServerState = None, None

try:
    from .network_game_controller import NetworkGameController
except ImportError:
    NetworkGameController = None

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
