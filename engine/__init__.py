"""MTG Commander Game Engine.

A comprehensive Magic: The Gathering rules engine implementation."""

__version__ = "1.0.0"
__author__ = "Randy"

# Core engine imports
from .game_state import GameState, PlayerState
from .game_controller import GameController
from .card_engine import Card, Permanent
from .mana import ManaPool
from .combat import CombatManager
from .stack import Stack
from .rules_engine import RulesEngine

__all__ = [
    "GameState",
    "PlayerState",
    "GameController", 
    "Card",
    "Permanent",
    "ManaPool",
    "CombatManager",
    "Stack",
    "RulesEngine",
]
