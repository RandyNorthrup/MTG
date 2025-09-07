from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict
import time, uuid

@dataclass
class LobbyPlayer:
    name: str
    deck_path: Optional[str] = None
    ready: bool = False
    is_host: bool = False

@dataclass
class LobbyState:
    lobby_id: str
    created_ts: float
    players: List[LobbyPlayer] = field(default_factory=list)
    started: bool = False

class LobbyServer:
    # Single in-memory lobby registry (placeholder for real backend)
    lobbies: Dict[str, LobbyState] = {}

    @classmethod
    def create_lobby(cls, host_name: str, deck_path: Optional[str]) -> LobbyState:
        lob = LobbyState(lobby_id=str(uuid.uuid4()), created_ts=time.time())
        lob.players.append(LobbyPlayer(name=host_name, deck_path=deck_path, ready=False, is_host=True))
        cls.lobbies[lob.lobby_id] = lob
        return lob

    @classmethod
    def list_lobbies(cls) -> List[LobbyState]:
        return list(cls.lobbies.values())

    @classmethod
    def join(cls, lobby_id: str, player_name: str) -> Optional[LobbyState]:
        lob = cls.lobbies.get(lobby_id)
        if not lob or lob.started:
            return None
        if any(p.name == player_name for p in lob.players):
            return lob
        lob.players.append(LobbyPlayer(name=player_name))
        return lob

    @classmethod
    def set_deck(cls, lobby_id: str, player_name: str, path: str):
        lob = cls.lobbies.get(lobby_id)
        if not lob: return
        for p in lob.players:
            if p.name == player_name:
                p.deck_path = path
                p.ready = False

    @classmethod
    def set_ready(cls, lobby_id: str, player_name: str, ready: bool):
        lob = cls.lobbies.get(lobby_id)
        if not lob: return
        for p in lob.players:
            if p.name == player_name:
                p.ready = ready

    @classmethod
    def can_start(cls, lobby_id: str) -> bool:
        lob = cls.lobbies.get(lobby_id)
        if not lob or not lob.players:
            return False
        host = next((p for p in lob.players if p.is_host), None)
        if not host:
            return False
        # Require every player to have deck + ready
        return all(p.deck_path and p.ready for p in lob.players)

    @classmethod
    def mark_started(cls, lobby_id: str):
        lob = cls.lobbies.get(lobby_id)
        if lob:
            lob.started = True
