"""Settings tab manager for MTG Commander.

Creates and manages the settings window accessed from the home screen.
"""

from ui.settings_window import SettingsWindow


class SettingsTabManager:
    """Manager for the settings window."""
    
    def __init__(self, api):
        self.api = api
        self.settings_window = None
        
    def open(self):
        """Open the settings window."""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.api, parent=getattr(self.api, 'w', None))
            
        # Show the window
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
        
    def close(self):
        """Close the settings window."""
        if self.settings_window:
            self.settings_window.close()
            
    def is_open(self):
        """Check if the settings window is open."""
        return self.settings_window is not None and self.settings_window.isVisible()
