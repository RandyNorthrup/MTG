"""MTG Dice Roll Dialog - Animated D20 for first player selection.

Provides an animated 20-sided dice roll interface to determine
which player goes first in Magic: The Gathering games.
"""

import math
import random

from PySide6.QtCore import Qt, QRectF, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AnimatedDiceWidget(QWidget):
    """Animated D20 dice widget for Magic: The Gathering.
    
    Displays a spinning 20-sided die with visual animation effects.
    Emits rollComplete signal when animation finishes with final result.
    
    Signals:
        rollComplete(int): Emitted with final dice roll result (1-20)
    """
    
    rollComplete = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setMaximumSize(200, 200)
        
        # Animation state
        self.is_rolling = False
        self.current_value = 1
        self.final_value = 1
        self.animation_frame = 0
        self.animation_speed = 50  # milliseconds between frames
        self.rotation_angle = 0
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        
    def start_roll(self, final_result: int):
        """Start the dice roll animation with the predetermined result."""
        if self.is_rolling:
            return
            
        self.final_value = final_result
        self.current_value = random.randint(1, 20)
        self.is_rolling = True
        self.animation_frame = 0
        self.rotation_angle = 0
        
        # Start animation - will run for about 2 seconds
        self.timer.start(self.animation_speed)
        
    def update_animation(self):
        """Update the animation frame."""
        if not self.is_rolling:
            return
            
        self.animation_frame += 1
        self.rotation_angle = (self.rotation_angle + 15) % 360
        
        # Change the displayed number randomly during animation
        if self.animation_frame < 40:  # 2 seconds of animation
            self.current_value = random.randint(1, 20)
            self.update()
        else:
            # Animation complete
            self.current_value = self.final_value
            self.is_rolling = False
            self.timer.stop()
            self.update()
            self.rollComplete.emit(self.final_value)
    
    def paintEvent(self, event):
        """Paint the dice."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get the center of the widget
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Dice size
        dice_size = min(self.width(), self.height()) - 20
        dice_radius = dice_size // 2
        
        # Draw dice background (icosahedron approximation as circle for simplicity)
        if self.is_rolling:
            # Pulsing effect while rolling
            pulse = abs(math.sin(self.animation_frame * 0.3)) * 20
            dice_color = QColor(200 + int(pulse), 200 + int(pulse), 255)
        else:
            dice_color = QColor(220, 220, 255)
            
        painter.setBrush(QBrush(dice_color))
        painter.setPen(QPen(QColor(100, 100, 150), 3))
        
        # Draw the dice as a circle (representing the D20)
        dice_rect = QRectF(center_x - dice_radius, center_y - dice_radius, 
                          dice_radius * 2, dice_radius * 2)
        painter.drawEllipse(dice_rect)
        
        # Draw rotation lines if rolling
        if self.is_rolling:
            painter.setPen(QPen(QColor(150, 150, 200), 2))
            for i in range(8):
                angle = (self.rotation_angle + i * 45) * math.pi / 180
                start_radius = dice_radius * 0.7
                end_radius = dice_radius * 0.9
                
                x1 = center_x + start_radius * math.cos(angle)
                y1 = center_y + start_radius * math.sin(angle)
                x2 = center_x + end_radius * math.cos(angle)
                y2 = center_y + end_radius * math.sin(angle)
                
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # Draw the number
        painter.setPen(QPen(QColor(50, 50, 100), 2))
        font = QFont("Arial", 36, QFont.Bold)
        painter.setFont(font)
        
        # Center the text
        text = str(self.current_value)
        text_rect = painter.fontMetrics().boundingRect(text)
        text_x = center_x - text_rect.width() // 2
        text_y = center_y + text_rect.height() // 2
        
        painter.drawText(text_x, text_y, text)
        
        # Draw "D20" label if not rolling
        if not self.is_rolling:
            painter.setPen(QPen(QColor(100, 100, 150), 1))
            font_small = QFont("Arial", 12)
            painter.setFont(font_small)
            painter.drawText(center_x - 15, center_y + dice_radius + 15, "D20")
        
        # Properly end painting to avoid warnings
        painter.end()


class DiceRollDialog(QDialog):
    """Dialog for animated dice rolling to determine first player."""
    
    def __init__(self, players, parent=None):
        super().__init__(parent)
        self.players = players
        self.rolls = {}
        self.winner = None
        self.current_player_index = 0
        self.ai_controllers = None  # Will be set by caller
        
        self.setWindowTitle("Roll for First Player")
        self.setModal(True)
        self.setMinimumSize(400, 350)
        self.setMaximumSize(400, 350)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Roll D20 to Determine First Player")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #333; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Current player label
        self.current_player_label = QLabel("")
        self.current_player_label.setAlignment(Qt.AlignCenter)
        self.current_player_label.setFont(QFont("Arial", 12))
        self.current_player_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(self.current_player_label)
        
        # Dice widget
        dice_container = QHBoxLayout()
        dice_container.addStretch()
        
        self.dice_widget = AnimatedDiceWidget()
        self.dice_widget.rollComplete.connect(self.on_roll_complete)
        dice_container.addWidget(self.dice_widget)
        
        dice_container.addStretch()
        layout.addLayout(dice_container)
        
        # Results display
        self.results_label = QLabel("")
        self.results_label.setAlignment(Qt.AlignCenter)
        self.results_label.setFont(QFont("Arial", 11))
        self.results_label.setStyleSheet("color: #444; margin-top: 10px;")
        self.results_label.setMinimumHeight(40)
        layout.addWidget(self.results_label)
        
        # Roll button
        self.roll_button = QPushButton("Roll Dice")
        self.roll_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.roll_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.roll_button.clicked.connect(self.roll_dice)
        layout.addWidget(self.roll_button)
        
        # Close button (initially hidden)
        self.close_button = QPushButton("Continue")
        self.close_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.close_button.clicked.connect(self.accept)
        self.close_button.setVisible(False)
        layout.addWidget(self.close_button)
        
        # Initialize for first player
        self.update_current_player_display()
        
    def set_ai_controllers(self, ai_controllers):
        """Set the AI controllers dictionary to identify AI players."""
        self.ai_controllers = ai_controllers
        
    def update_current_player_display(self):
        """Update the display for the current player."""
        if self.current_player_index < len(self.players):
            player = self.players[self.current_player_index]
            player_name = getattr(player, 'name', f'Player {self.current_player_index}')
            
            # Check if current player is AI
            is_ai_player = (self.ai_controllers is not None and 
                           hasattr(player, 'player_id') and 
                           player.player_id in self.ai_controllers)
            
            if is_ai_player:
                self.current_player_label.setText(f"{player_name} (AI) rolling...")
                self.roll_button.setEnabled(False)
                self.roll_button.setText("AI Rolling...")
                # Automatically roll for AI after a short delay
                QTimer.singleShot(800, self.roll_dice_auto_ai)
            else:
                self.current_player_label.setText(f"{player_name}'s turn to roll")
                self.roll_button.setEnabled(True)
                self.roll_button.setText("Roll Dice")
            
            # Update results display
            if self.rolls:
                results_text = "Results so far:\n"
                for i, (pid, roll) in enumerate(self.rolls.items()):
                    # Find player by ID
                    player = next((p for p in self.players if p.player_id == pid), None)
                    p_name = getattr(player, 'name', f'Player {pid}') if player else f'Player {pid}'
                    results_text += f"{p_name}: {roll}"
                    if i < len(self.rolls) - 1:
                        results_text += ", "
                self.results_label.setText(results_text)
        else:
            self.current_player_label.setText("Rolling complete!")
    
    def roll_dice(self):
        """Start a dice roll for the current player."""
        if self.current_player_index >= len(self.players):
            return
            
        # Disable the roll button during animation
        self.roll_button.setEnabled(False)
        self.roll_button.setText("Rolling...")
        
        # Generate the actual roll result
        roll_result = random.randint(1, 20)
        
        # Start the animation with this result
        self.dice_widget.start_roll(roll_result)
    
    def roll_dice_auto_ai(self):
        """Automatically roll dice for AI player without user interaction."""
        if self.current_player_index >= len(self.players):
            return
            
        player = self.players[self.current_player_index]
        
        # Verify this is an AI player
        is_ai_player = (self.ai_controllers is not None and 
                       hasattr(player, 'player_id') and 
                       player.player_id in self.ai_controllers)
        
        if not is_ai_player:
            # Not an AI player, should not auto-roll
            return
            
        # Disable interaction during AI roll
        self.roll_button.setEnabled(False)
        self.roll_button.setText("AI Rolling...")
        
        # Generate the AI roll result
        roll_result = random.randint(1, 20)
        
        # Start the animation with this result
        self.dice_widget.start_roll(roll_result)
    
    def on_roll_complete(self, result):
        """Handle completion of dice roll animation."""
        # Store the result
        player_id = self.players[self.current_player_index].player_id
        self.rolls[player_id] = result
        
        # Move to next player
        self.current_player_index += 1
        
        if self.current_player_index < len(self.players):
            # More players to roll
            self.roll_button.setEnabled(True)
            self.roll_button.setText("Roll Dice")
            self.update_current_player_display()
        else:
            # All players have rolled - determine winner
            self.determine_winner()
    
    def determine_winner(self):
        """Determine the winner and handle ties."""
        if not self.rolls:
            return
            
        # Find the highest roll
        max_roll = max(self.rolls.values())
        winners = [pid for pid, roll in self.rolls.items() if roll == max_roll]
        
        if len(winners) == 1:
            # Single winner
            self.winner = winners[0]
            winner_player = next((p for p in self.players if p.player_id == self.winner), None)
            winner_name = getattr(winner_player, 'name', f'Player {self.winner}') if winner_player else f'Player {self.winner}'
            
            self.current_player_label.setText(f"{winner_name} wins!")
            self.results_label.setText(self.format_final_results())
            
            self.roll_button.setVisible(False)
            self.close_button.setVisible(True)
        else:
            # Tie - need to re-roll
            tied_players = [p for p in self.players if p.player_id in winners]
            tied_names = [getattr(p, 'name', f'Player {p.player_id}') for p in tied_players]
            
            self.current_player_label.setText(f"Tie! {', '.join(tied_names)} must re-roll")
            self.results_label.setText(self.format_final_results() + "\n\nRe-rolling tied players...")
            
            # Reset for tie-breaker
            self.players = tied_players
            self.rolls.clear()
            self.current_player_index = 0
            
            # Re-enable rolling after a short delay
            QTimer.singleShot(2000, self.restart_for_tiebreaker)
    
    def restart_for_tiebreaker(self):
        """Restart rolling for tiebreaker."""
        self.roll_button.setEnabled(True)
        self.roll_button.setText("Roll Dice")
        self.roll_button.setVisible(True)
        self.update_current_player_display()
    
    def format_final_results(self):
        """Format the final results text."""
        results = []
        for pid, roll in sorted(self.rolls.items(), key=lambda x: x[1], reverse=True):
            player = next((p for p in self.players if p.player_id == pid), None)
            player_name = getattr(player, 'name', f'Player {pid}') if player else f'Player {pid}'
            results.append(f"{player_name}: {roll}")
        return "Final Results:\n" + "\n".join(results)
    
    def get_winner(self):
        """Get the winning player ID."""
        return self.winner
    
    def get_rolls(self):
        """Get all roll results."""
        return self.rolls.copy()
