# MTG Commander - Network Architecture

## Overview

The MTG Commander Game Engine supports local network multiplayer through a client-server architecture. This document outlines the design and implementation of the networking system.

## Architecture

### Client-Server Model

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client 1  │    │   Client 2  │    │   Client 3  │
│  (Player 1) │    │  (Player 2) │    │  (Player 3) │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                   ┌──────▼──────┐
                   │             │
                   │ Game Server │
                   │             │
                   └─────────────┘
```

### Components

1. **Game Server** (`network/game_server.py`)
   - Manages game state
   - Coordinates player actions
   - Validates moves according to MTG rules
   - Broadcasts state changes to clients

2. **Network Client** (`network/network_client.py`)
   - Connects to game server
   - Sends player actions
   - Receives game state updates
   - Handles connection management

3. **Message Protocol** (`network/message_protocol.py`)
   - Defines message types and formats
   - Handles serialization/deserialization
   - Ensures reliable communication

4. **Network Game Controller** (`network/network_game_controller.py`)
   - Extends existing GameController
   - Routes actions through network
   - Synchronizes local and remote state

## Message Types

### Connection Messages
- `JOIN_GAME` - Player requests to join
- `PLAYER_JOINED` - New player joined notification
- `PLAYER_LEFT` - Player disconnected notification
- `HEARTBEAT` - Keep connection alive

### Game State Messages
- `GAME_STATE_UPDATE` - Full game state synchronization
- `PHASE_CHANGE` - Turn/phase progression
- `PLAYER_ACTION` - Player performs action
- `ACTION_RESULT` - Result of action validation

### Card/Game Action Messages
- `PLAY_CARD` - Player plays a card
- `CAST_SPELL` - Player casts a spell
- `ACTIVATE_ABILITY` - Ability activation
- `DECLARE_ATTACKERS` - Combat declaration
- `DECLARE_BLOCKERS` - Block declaration
- `PASS_PRIORITY` - Pass priority to next player

## Protocol Specification

### Message Format
```python
{
    "type": str,           # Message type
    "player_id": int,      # Sender player ID
    "timestamp": float,    # Unix timestamp
    "sequence": int,       # Message sequence number
    "data": dict,          # Message-specific data
    "checksum": str        # Message integrity check
}
```

### Connection Flow
1. Client connects to server socket
2. Server sends game configuration
3. Client sends JOIN_GAME with player info
4. Server validates and adds player
5. Server broadcasts PLAYER_JOINED to all clients
6. Game begins when all players ready

## Game State Synchronization

### Authority Model
- Server is authoritative for all game state
- Clients send action requests
- Server validates and executes actions
- Server broadcasts results to all clients

### Conflict Resolution
- All actions validated server-side against MTG rules
- Invalid actions rejected with error message
- Clients update UI based on server responses only

### State Consistency
- Regular state checksum validation
- Full state resync on checksum mismatch
- Rollback mechanism for desync recovery

## Network Features

### Connection Management
- Automatic reconnection on connection loss
- Graceful handling of player disconnections
- Game pause/resume for reconnecting players

### Performance Optimization
- Delta updates for large game states
- Compression for message efficiency
- Buffering and batching for frequent updates

### Security Considerations
- Input validation on all messages
- Rate limiting to prevent spam
- Checksum validation for message integrity
- Local network only (no internet security needed)

## Implementation Notes

### Threading Model
- Server uses thread pool for client connections
- Async message handling with Qt signals/slots
- Non-blocking network operations

### Error Handling
- Connection timeouts and retries
- Graceful degradation on network issues
- User-friendly error messages

### Integration Points
- Extends existing GameController architecture
- Minimal changes to core game logic
- Maintains compatibility with single-player mode

## Configuration

### Server Settings
```python
SERVER_HOST = "localhost"
SERVER_PORT = 8888
MAX_PLAYERS = 4
HEARTBEAT_INTERVAL = 30  # seconds
CONNECTION_TIMEOUT = 60  # seconds
```

### Client Settings
```python
RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 2  # seconds
MESSAGE_TIMEOUT = 10  # seconds
```
