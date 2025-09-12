"""
Player preferences system for MTG Commander application.
Handles saving and loading of player name and avatar settings.
"""

import json
import os
from typing import Dict, Any


class PlayerPreferences:
    """Manages player preferences including name and avatar."""
    
    def __init__(self, preferences_file="data/player_preferences.json"):
        self.preferences_file = preferences_file
        self.preferences = self.load_preferences()
        
    def load_preferences(self) -> Dict[str, Any]:
        """Load player preferences from file."""
        try:
            if os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading preferences: {e}")
        
        # Return default preferences
        return {
            "player_name": "You",
            "player_avatar": 0,  # Index of selected avatar (0 = white)
            "opponent_avatar": 3  # Default opponent avatar (3 = red)
        }
    
    def save_preferences(self) -> bool:
        """Save current preferences to file."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.preferences_file), exist_ok=True)
            
            with open(self.preferences_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return False
    
    def get_player_name(self) -> str:
        """Get the player's name."""
        return self.preferences.get("player_name", "You")
    
    def set_player_name(self, name: str):
        """Set the player's name."""
        self.preferences["player_name"] = name
        self.save_preferences()
    
    def get_player_avatar(self) -> int:
        """Get the player's selected avatar index."""
        return self.preferences.get("player_avatar", 0)
    
    def set_player_avatar(self, avatar_index: int):
        """Set the player's avatar index."""
        self.preferences["player_avatar"] = avatar_index
        self.save_preferences()
    
    def get_opponent_avatar(self) -> int:
        """Get the opponent's avatar index."""
        return self.preferences.get("opponent_avatar", 3)
    
    def set_opponent_avatar(self, avatar_index: int):
        """Set the opponent's avatar index."""
        self.preferences["opponent_avatar"] = avatar_index
        self.save_preferences()
    
    def get_avatar_path(self, avatar_index: int) -> str:
        """Get the file path for an avatar by index."""
        avatar_files = [
            "data/avatars/white_planeswalker.png",
            "data/avatars/blue_planeswalker.png", 
            "data/avatars/black_planeswalker.png",
            "data/avatars/red_planeswalker.png",
            "data/avatars/green_planeswalker.png"
        ]
        
        if 0 <= avatar_index < len(avatar_files):
            return avatar_files[avatar_index]
        return avatar_files[0]  # Default to white
    
    def get_player_avatar_path(self) -> str:
        """Get the player's avatar file path."""
        return self.get_avatar_path(self.get_player_avatar())
    
    def get_opponent_avatar_path(self) -> str:
        """Get the opponent's avatar file path."""
        return self.get_avatar_path(self.get_opponent_avatar())


# Global instance
_player_prefs = None

def get_player_preferences() -> PlayerPreferences:
    """Get the global player preferences instance."""
    global _player_prefs
    if _player_prefs is None:
        _player_prefs = PlayerPreferences()
    return _player_prefs
