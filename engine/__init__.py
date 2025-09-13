"""MTG Commander Game Engine.

A comprehensive Magic: The Gathering rules engine implementation."""

import os
from pathlib import Path

# Load version from VERSION file
def _load_version():
    """Load version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.1.0-dev"  # Fallback version

__version__ = _load_version()
__author__ = "Randy"
__description__ = "MTG Commander Game Engine - Beta Version"
__status__ = "Beta"
__license__ = "MIT"

# Version helper functions
def get_version_info():
    """Get detailed version information."""
    version_parts = __version__.split('-')
    base_version = version_parts[0]
    pre_release = version_parts[1] if len(version_parts) > 1 else None
    
    return {
        'version': __version__,
        'base_version': base_version,
        'pre_release': pre_release,
        'status': __status__,
        'is_beta': 'beta' in __version__.lower(),
        'is_dev': 'dev' in __version__.lower(),
        'is_stable': not ('beta' in __version__.lower() or 'dev' in __version__.lower())
    }

def print_version():
    """Print version information."""
    info = get_version_info()
    print(f"MTG Commander Game Engine v{info['version']}")
    print(f"Status: {info['status']}")
    if info['is_beta']:
        print("⚠️  This is a beta version - some features may be unstable")
    elif info['is_dev']:
        print("🔧 Development version - expect bugs and frequent changes")
    print(f"Author: {__author__}")

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
