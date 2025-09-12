from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QHBoxLayout,
    QGroupBox, QCheckBox, QFrame, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.theme import MTGTheme
from ui.player_preferences import get_player_preferences

class SettingsWindow(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MTG Commander - Settings")
        self.api = api
        self.preferences = get_player_preferences()
        self.setMinimumSize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the settings window UI."""
        # Apply theme styling
        self.setStyleSheet(f"""
            QDialog {{
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
                color: {MTGTheme.TEXT_PRIMARY.name()};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Game Settings")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()}; margin-bottom: 8px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # UI Settings Group
        ui_group = QGroupBox("User Interface")
        ui_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                color: {MTGTheme.TEXT_PRIMARY.name()};
                border: 2px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 8px;
                margin: 8px 0px;
                padding-top: 12px;
            }}
        """)
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setSpacing(8)
        
        # Game log toggle checkbox
        self.game_log_checkbox = QCheckBox("Show Game Log Window")
        self.game_log_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size: 13px;
                color: {MTGTheme.TEXT_PRIMARY.name()};
                spacing: 8px;
                padding: 4px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 4px;
                background: {MTGTheme.BACKGROUND_DARK.name()};
            }}
            QCheckBox::indicator:checked {{
                background: {MTGTheme.HOVER_HIGHLIGHT.name()};
                border: 2px solid {MTGTheme.ACTIVE_HIGHLIGHT.name()};
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {MTGTheme.HOVER_HIGHLIGHT.name()};
            }}
        """)
        
        # Set initial state if game log manager exists
        if hasattr(self.api, 'board_window') and self.api.board_window:
            if hasattr(self.api.board_window.play_area, 'game_log_manager'):
                log_manager = self.api.board_window.play_area.game_log_manager
                self.game_log_checkbox.setChecked(log_manager.is_visible)
                
        self.game_log_checkbox.toggled.connect(self.toggle_game_log)
        ui_layout.addWidget(self.game_log_checkbox)
        
        # Game log description
        log_desc = QLabel("Toggle the floating game log window that shows game events and actions.")
        log_desc.setStyleSheet(f"""
            color: {MTGTheme.TEXT_SECONDARY.name()};
            font-size: 11px;
            margin-left: 26px;
            margin-bottom: 8px;
        """)
        log_desc.setWordWrap(True)
        ui_layout.addWidget(log_desc)
        
        layout.addWidget(ui_group)
        
        # Player Setup Group
        player_group = QGroupBox("Player Setup")
        player_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                color: {MTGTheme.TEXT_PRIMARY.name()};
                border: 2px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 8px;
                margin: 8px 0px;
                padding-top: 12px;
            }}
        """)
        player_layout = QVBoxLayout(player_group)
        player_layout.setSpacing(12)
        
        # Player name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Player Name:")
        name_label.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()}; font-size: 13px; font-weight: bold;")
        name_layout.addWidget(name_label)
        
        self.player_name_input = QLineEdit()
        self.player_name_input.setPlaceholderText("Enter your name...")
        self.player_name_input.setText(self.preferences.get_player_name())  # Load from preferences
        self.player_name_input.textChanged.connect(self.on_name_changed)
        self.player_name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {MTGTheme.BACKGROUND_DARK.name()};
                border: 2px solid {MTGTheme.BORDER_DARK.name()};
                border-radius: 6px;
                color: {MTGTheme.TEXT_PRIMARY.name()};
                font-size: 13px;
                padding: 8px 12px;
                min-width: 200px;
            }}
            QLineEdit:focus {{
                border: 2px solid {MTGTheme.HOVER_HIGHLIGHT.name()};
            }}
        """)
        name_layout.addWidget(self.player_name_input)
        name_layout.addStretch()
        player_layout.addLayout(name_layout)
        
        # Avatar selection
        avatar_label = QLabel("Choose Avatar:")
        avatar_label.setStyleSheet(f"color: {MTGTheme.TEXT_PRIMARY.name()}; font-size: 13px; font-weight: bold; margin-bottom: 8px;")
        player_layout.addWidget(avatar_label)
        
        # Avatar grid
        avatar_layout = QHBoxLayout()
        avatar_layout.setSpacing(12)
        
        self.avatar_buttons = []
        avatar_data = [
            ("White Planeswalker", "white", "data/avatars/white_planeswalker.png"),
            ("Blue Planeswalker", "blue", "data/avatars/blue_planeswalker.png"), 
            ("Black Planeswalker", "black", "data/avatars/black_planeswalker.png"),
            ("Red Planeswalker", "red", "data/avatars/red_planeswalker.png"),
            ("Green Planeswalker", "green", "data/avatars/green_planeswalker.png")
        ]
        
        for i, (name, color, image_path) in enumerate(avatar_data):
            avatar_btn = QPushButton()
            avatar_btn.setFixedSize(80, 80)
            avatar_btn.setToolTip(name)
            avatar_btn.setCheckable(True)
            
            # Load and set avatar image
            try:
                from PySide6.QtGui import QPixmap, QIcon
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Scale to fit button and make it rounded
                    scaled_pixmap = pixmap.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    avatar_btn.setIcon(QIcon(scaled_pixmap))
                    avatar_btn.setIconSize(scaled_pixmap.size())
            except Exception as e:
                print(f"Could not load avatar {image_path}: {e}")
            
            # Create styled avatar button with rounded edges
            avatar_btn.setStyleSheet(f"""
                QPushButton {{
                    border: 3px solid {MTGTheme.BORDER_DARK.name()};
                    border-radius: 40px;
                    background: transparent;
                }}
                QPushButton:hover {{
                    border: 3px solid {MTGTheme.HOVER_HIGHLIGHT.name()};
                }}
                QPushButton:checked {{
                    border: 4px solid {MTGTheme.ACTIVE_HIGHLIGHT.name()};
                    background: rgba(70, 120, 180, 50);
                }}
            """)
            
            # Connect to selection handler
            avatar_btn.clicked.connect(lambda checked, idx=i: self.select_avatar(idx))
            
            self.avatar_buttons.append(avatar_btn)
            avatar_layout.addWidget(avatar_btn)
            
        # Select avatar from preferences
        saved_avatar = self.preferences.get_player_avatar()
        if 0 <= saved_avatar < len(self.avatar_buttons):
            self.avatar_buttons[saved_avatar].setChecked(True)
            self.selected_avatar = saved_avatar
        else:
            self.avatar_buttons[0].setChecked(True)
            self.selected_avatar = 0
        
        avatar_layout.addStretch()
        player_layout.addLayout(avatar_layout)
        
        # Avatar description
        avatar_desc = QLabel("Choose an avatar representing your planeswalker identity. Each color represents a different magical philosophy.")
        avatar_desc.setStyleSheet(f"""
            color: {MTGTheme.TEXT_SECONDARY.name()};
            font-size: 11px;
            margin-top: 8px;
        """)
        avatar_desc.setWordWrap(True)
        player_layout.addWidget(avatar_desc)
        
        layout.addWidget(player_group)
        
        # Add stretch to push buttons to bottom
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Close button
        btn_close = QPushButton("Close")
        btn_close.setFixedSize(100, 36)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {MTGTheme.BACKGROUND_LIGHT.name()};
                border: 1px solid {MTGTheme.BORDER_DARK.name()};
                color: {MTGTheme.TEXT_PRIMARY.name()};
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {MTGTheme.HOVER_HIGHLIGHT.name()};
            }}
            QPushButton:pressed {{
                background: {MTGTheme.ACTIVE_HIGHLIGHT.name()};
            }}
        """)
        btn_close.clicked.connect(self.close)
        button_layout.addWidget(btn_close)
        
        layout.addLayout(button_layout)
        
    def on_name_changed(self, text):
        """Handle player name changes."""
        self.preferences.set_player_name(text.strip() or "You")
        
    def select_avatar(self, avatar_index):
        """Handle avatar selection."""
        # Uncheck all other avatars
        for i, btn in enumerate(self.avatar_buttons):
            btn.setChecked(i == avatar_index)
        
        self.selected_avatar = avatar_index
        
        # Save avatar preference
        self.preferences.set_player_avatar(avatar_index)
        
        # Apply avatar changes to game if active
        if hasattr(self.api, 'board_window') and self.api.board_window:
            if hasattr(self.api.board_window.play_area, 'update_player_avatars'):
                self.api.board_window.play_area.update_player_avatars()
        
    def toggle_game_log(self, checked):
        """Toggle the game log window visibility."""
        if hasattr(self.api, 'board_window') and self.api.board_window:
            if hasattr(self.api.board_window.play_area, 'game_log_manager'):
                log_manager = self.api.board_window.play_area.game_log_manager
                if checked:
                    log_manager.show_log_window()
                else:
                    log_manager.hide_log_window()
