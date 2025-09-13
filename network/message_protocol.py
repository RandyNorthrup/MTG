"""MTG Commander Game - Network Message Protocol

This module defines the message protocol for network communication between
clients and servers. It handles message serialization, validation, and type definitions.
"""

import json
import hashlib
import time
from enum import Enum
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict


class MessageType(Enum):
    """Network message types for MTG Commander multiplayer."""
    
    # Connection Management
    JOIN_GAME = "join_game"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    HEARTBEAT = "heartbeat"
    DISCONNECT = "disconnect"
    
    # Game State
    GAME_STATE_UPDATE = "game_state_update"
    PHASE_CHANGE = "phase_change"
    TURN_CHANGE = "turn_change"
    GAME_START = "game_start"
    GAME_END = "game_end"
    
    # Player Actions
    PLAYER_ACTION = "player_action"
    ACTION_RESULT = "action_result"
    PASS_PRIORITY = "pass_priority"
    
    # Card Actions
    PLAY_CARD = "play_card"
    CAST_SPELL = "cast_spell"
    ACTIVATE_ABILITY = "activate_ability"
    
    # Combat
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    COMBAT_DAMAGE = "combat_damage"
    
    # Mana & Resources
    TAP_LAND = "tap_land"
    ADD_MANA = "add_mana"
    SPEND_MANA = "spend_mana"
    
    # Error Handling
    ERROR = "error"
    INVALID_ACTION = "invalid_action"
    RESYNC_REQUEST = "resync_request"


@dataclass
class NetworkMessage:
    """A network message with metadata and payload."""
    
    type: MessageType
    player_id: int
    timestamp: float
    sequence: int
    data: Dict[str, Any]
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Calculate checksum after initialization."""
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of message content."""
        content = {
            "type": self.type.value,
            "player_id": self.player_id,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "data": self.data
        }
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]
    
    def is_valid(self) -> bool:
        """Verify message integrity using checksum."""
        return self.checksum == self._calculate_checksum()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "type": self.type.value,
            "player_id": self.player_id,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "data": self.data,
            "checksum": self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkMessage':
        """Create message from dictionary."""
        return cls(
            type=MessageType(data["type"]),
            player_id=data["player_id"],
            timestamp=data["timestamp"],
            sequence=data["sequence"],
            data=data["data"],
            checksum=data.get("checksum")
        )


class MessageProtocol:
    """Handles message creation, validation, and protocol logic."""
    
    def __init__(self, player_id: int = 0):
        self.player_id = player_id
        self.sequence_counter = 0
    
    def create_message(self, msg_type: MessageType, data: Dict[str, Any]) -> NetworkMessage:
        """Create a new network message with proper metadata."""
        self.sequence_counter += 1
        
        return NetworkMessage(
            type=msg_type,
            player_id=self.player_id,
            timestamp=time.time(),
            sequence=self.sequence_counter,
            data=data
        )
    
    def create_join_game_message(self, player_name: str, deck_name: str) -> NetworkMessage:
        """Create a JOIN_GAME message."""
        return self.create_message(MessageType.JOIN_GAME, {
            "player_name": player_name,
            "deck_name": deck_name
        })
    
    def create_player_action_message(self, action: str, **kwargs) -> NetworkMessage:
        """Create a PLAYER_ACTION message."""
        return self.create_message(MessageType.PLAYER_ACTION, {
            "action": action,
            **kwargs
        })
    
    def create_play_card_message(self, card_id: str, zone_from: str, zone_to: str, **kwargs) -> NetworkMessage:
        """Create a PLAY_CARD message."""
        return self.create_message(MessageType.PLAY_CARD, {
            "card_id": card_id,
            "zone_from": zone_from,
            "zone_to": zone_to,
            **kwargs
        })
    
    def create_cast_spell_message(self, card_id: str, mana_cost: Dict[str, int], targets: list = None) -> NetworkMessage:
        """Create a CAST_SPELL message."""
        return self.create_message(MessageType.CAST_SPELL, {
            "card_id": card_id,
            "mana_cost": mana_cost,
            "targets": targets or []
        })
    
    def create_phase_change_message(self, new_phase: str, active_player: int) -> NetworkMessage:
        """Create a PHASE_CHANGE message."""
        return self.create_message(MessageType.PHASE_CHANGE, {
            "new_phase": new_phase,
            "active_player": active_player
        })
    
    def create_game_state_update_message(self, state_data: Dict[str, Any]) -> NetworkMessage:
        """Create a GAME_STATE_UPDATE message."""
        return self.create_message(MessageType.GAME_STATE_UPDATE, {
            "state": state_data
        })
    
    def create_error_message(self, error_code: str, error_msg: str) -> NetworkMessage:
        """Create an ERROR message."""
        return self.create_message(MessageType.ERROR, {
            "error_code": error_code,
            "error_message": error_msg
        })
    
    def create_heartbeat_message(self) -> NetworkMessage:
        """Create a HEARTBEAT message."""
        return self.create_message(MessageType.HEARTBEAT, {
            "alive": True
        })


def serialize_message(message: NetworkMessage) -> bytes:
    """Serialize a network message to bytes for transmission."""
    try:
        message_dict = message.to_dict()
        json_str = json.dumps(message_dict, separators=(',', ':'))
        
        # Add message length header (4 bytes)
        message_bytes = json_str.encode('utf-8')
        length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
        
        return length_bytes + message_bytes
        
    except Exception as e:
        raise ValueError(f"Failed to serialize message: {e}")


def deserialize_message(data: bytes) -> NetworkMessage:
    """Deserialize bytes back to a network message."""
    try:
        # Read length header
        if len(data) < 4:
            raise ValueError("Invalid message: too short for length header")
        
        length = int.from_bytes(data[:4], byteorder='big')
        
        if len(data) < 4 + length:
            raise ValueError("Invalid message: incomplete data")
        
        # Extract and decode JSON
        json_data = data[4:4+length].decode('utf-8')
        message_dict = json.loads(json_data)
        
        # Create and validate message
        message = NetworkMessage.from_dict(message_dict)
        
        if not message.is_valid():
            raise ValueError("Invalid message: checksum mismatch")
        
        return message
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to deserialize message: invalid JSON - {e}")
    except Exception as e:
        raise ValueError(f"Failed to deserialize message: {e}")


def validate_message(message: NetworkMessage, expected_types: list = None) -> bool:
    """Validate a network message for correctness."""
    try:
        # Check basic structure
        if not isinstance(message.player_id, int) or message.player_id < 0:
            return False
        
        if not isinstance(message.timestamp, (int, float)) or message.timestamp <= 0:
            return False
        
        if not isinstance(message.sequence, int) or message.sequence <= 0:
            return False
        
        if not isinstance(message.data, dict):
            return False
        
        # Check message type if specified
        if expected_types and message.type not in expected_types:
            return False
        
        # Verify checksum
        if not message.is_valid():
            return False
        
        return True
        
    except Exception:
        return False


# Message validation schemas for different message types
MESSAGE_SCHEMAS = {
    MessageType.JOIN_GAME: {
        "required_fields": ["player_name", "deck_name"],
        "optional_fields": []
    },
    MessageType.PLAYER_ACTION: {
        "required_fields": ["action"],
        "optional_fields": []
    },
    MessageType.PLAY_CARD: {
        "required_fields": ["card_id", "zone_from", "zone_to"],
        "optional_fields": ["targets", "mana_cost"]
    },
    MessageType.CAST_SPELL: {
        "required_fields": ["card_id", "mana_cost"],
        "optional_fields": ["targets"]
    },
    MessageType.PHASE_CHANGE: {
        "required_fields": ["new_phase", "active_player"],
        "optional_fields": []
    }
}


def validate_message_data(message: NetworkMessage) -> bool:
    """Validate message data against expected schema."""
    if message.type not in MESSAGE_SCHEMAS:
        return True  # No schema defined, assume valid
    
    schema = MESSAGE_SCHEMAS[message.type]
    data = message.data
    
    # Check required fields
    for field in schema["required_fields"]:
        if field not in data:
            return False
    
    return True
