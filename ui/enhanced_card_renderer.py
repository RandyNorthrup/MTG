"""
Enhanced Card Renderer with Layers System Integration
Displays accurate power/toughness, keywords, and enhanced card properties
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPen, QColor, QPainter
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from typing import Dict, Any, Optional

class EnhancedCardDisplay(QWidget):
    """Enhanced card display widget that shows accurate P/T and keywords"""
    
    def __init__(self, card, api, parent=None):
        super().__init__(parent)
        self.card = card
        self.api = api
        self.card_info = None
        
        self.setup_ui()
        self.update_display()
        
    def setup_ui(self):
        """Setup the enhanced card display UI"""
        self.setFixedSize(180, 250)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #555;
                border-radius: 8px;
                color: white;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: white;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        
        # Card name
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(30)
        layout.addWidget(self.name_label)
        
        # Mana cost
        self.cost_label = QLabel()
        self.cost_label.setFont(QFont("Arial", 9))
        self.cost_label.setMaximumHeight(20)
        layout.addWidget(self.cost_label)
        
        # Type line
        self.type_label = QLabel()
        self.type_label.setFont(QFont("Arial", 8))
        self.type_label.setWordWrap(True)
        self.type_label.setMaximumHeight(25)
        layout.addWidget(self.type_label)
        
        # Enhanced power/toughness display
        self.pt_container = QWidget()
        pt_layout = QHBoxLayout(self.pt_container)
        pt_layout.setContentsMargins(0, 0, 0, 0)
        
        self.base_pt_label = QLabel()
        self.base_pt_label.setFont(QFont("Arial", 8))
        self.base_pt_label.setStyleSheet("color: #aaa;")
        
        self.current_pt_label = QLabel()
        self.current_pt_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        pt_layout.addWidget(QLabel("Base:"))
        pt_layout.addWidget(self.base_pt_label)
        pt_layout.addStretch()
        pt_layout.addWidget(self.current_pt_label)
        
        layout.addWidget(self.pt_container)
        
        # Keywords display
        self.keywords_label = QLabel()
        self.keywords_label.setFont(QFont("Arial", 7))
        self.keywords_label.setWordWrap(True)
        self.keywords_label.setMaximumHeight(40)
        self.keywords_label.setStyleSheet("color: #ffd700;")  # Gold color for keywords
        layout.addWidget(self.keywords_label)
        
        # Enhanced status indicators
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Arial", 7))
        self.status_label.setMaximumHeight(20)
        self.status_label.setStyleSheet("color: #90ee90;")  # Light green
        layout.addWidget(self.status_label)
        
        # Card text (abbreviated)
        self.text_label = QLabel()
        self.text_label.setFont(QFont("Arial", 6))
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignTop)
        layout.addWidget(self.text_label)
        
        layout.addStretch()
    
    def update_display(self):
        """Update the display with enhanced card information"""
        try:
            # Get enhanced card info from API
            self.card_info = self.api.get_enhanced_card_info(self.card)
            
            # Update basic info
            self.name_label.setText(self.card_info.get('name', 'Unknown'))
            
            # Format mana cost
            cost_str = self.card_info.get('mana_cost_str', '')
            if cost_str:
                self.cost_label.setText(f"Cost: {cost_str}")
            else:
                cost = self.card_info.get('mana_cost', 0)
                self.cost_label.setText(f"Cost: {cost}" if cost > 0 else "")
            
            # Type line
            types = self.card_info.get('types', [])
            self.type_label.setText(" ".join(types))
            
            # Enhanced P/T display
            self._update_power_toughness()
            
            # Keywords display
            self._update_keywords()
            
            # Status indicators
            self._update_status()
            
            # Abbreviated text
            text = self.card_info.get('text', '')
            if len(text) > 100:
                text = text[:97] + "..."
            self.text_label.setText(text)
            
            # Update styling based on enhanced properties
            self._update_styling()
            
        except Exception as e:
            # Fallback display
            self.name_label.setText(getattr(self.card, 'name', 'Unknown'))
            self.cost_label.setText(f"Cost: {getattr(self.card, 'mana_cost', 0)}")
            self.type_label.setText(" ".join(getattr(self.card, 'types', [])))
            self.current_pt_label.setText(f"{getattr(self.card, 'power', '?')}/{getattr(self.card, 'toughness', '?')}")
    
    def _update_power_toughness(self):
        """Update power/toughness display with layers system results"""
        base_power = self.card_info.get('base_power')
        base_toughness = self.card_info.get('base_toughness')
        current_power = self.card_info.get('current_power')
        current_toughness = self.card_info.get('current_toughness')
        
        # Only show P/T for creatures
        types = self.card_info.get('types', [])
        if "Creature" in types or any("Vehicle" in t for t in types):
            # Base P/T
            if base_power is not None and base_toughness is not None:
                self.base_pt_label.setText(f"{base_power}/{base_toughness}")
            else:
                self.base_pt_label.setText("")
            
            # Current P/T (after effects)
            if current_power is not None and current_toughness is not None:
                pt_text = f"{current_power}/{current_toughness}"
                
                # Color coding for modifications
                if (base_power is not None and current_power != base_power) or \
                   (base_toughness is not None and current_toughness != base_toughness):
                    if (current_power or 0) > (base_power or 0) or (current_toughness or 0) > (base_toughness or 0):
                        self.current_pt_label.setStyleSheet("color: #90EE90;")  # Light green for buffs
                    else:
                        self.current_pt_label.setStyleSheet("color: #FFB6C1;")  # Light red for debuffs
                else:
                    self.current_pt_label.setStyleSheet("color: white;")
                
                self.current_pt_label.setText(pt_text)
            else:
                self.current_pt_label.setText("")
            
            self.pt_container.setVisible(True)
        else:
            self.pt_container.setVisible(False)
    
    def _update_keywords(self):
        """Update keywords display"""
        keywords = self.card_info.get('keywords', [])
        combat_keywords = self.card_info.get('combat_keywords', set())
        
        if keywords:
            # Highlight combat keywords
            keyword_display = []
            for keyword in keywords:
                if keyword.lower() in combat_keywords:
                    keyword_display.append(f"⚔️{keyword}")
                else:
                    keyword_display.append(keyword)
            
            self.keywords_label.setText(", ".join(keyword_display))
        else:
            self.keywords_label.setText("")
    
    def _update_status(self):
        """Update status indicators"""
        status_parts = []
        
        if self.card_info.get('is_token', False):
            status_parts.append("🪙Token")
        
        if self.card_info.get('is_copy', False):
            status_parts.append("📄Copy")
        
        # Check for special properties
        try:
            if hasattr(self.card, 'is_commander') and self.card.is_commander:
                status_parts.append("👑Commander")
            
            if hasattr(self.card, 'enters_tapped') and self.card.enters_tapped:
                status_parts.append("💤Enters Tapped")
                
        except:
            pass
        
        self.status_label.setText(" ".join(status_parts))
    
    def _update_styling(self):
        """Update widget styling based on enhanced properties"""
        try:
            # Special styling for tokens and copies
            if self.card_info.get('is_token', False):
                self.setStyleSheet(self.styleSheet() + """
                    QWidget {
                        border-color: #DAA520;  /* Gold for tokens */
                    }
                """)
            elif self.card_info.get('is_copy', False):
                self.setStyleSheet(self.styleSheet() + """
                    QWidget {
                        border-color: #9370DB;  /* Purple for copies */
                    }
                """)
            
            # Color-based styling
            colors = self.card_info.get('color_identity', [])
            if len(colors) == 1:
                color_map = {
                    'W': '#FFFBD5',  # White
                    'U': '#0E68AB',  # Blue  
                    'B': '#150B00',  # Black
                    'R': '#D3202A',  # Red
                    'G': '#00733E'   # Green
                }
                if colors[0] in color_map:
                    self.name_label.setStyleSheet(f"color: {color_map[colors[0]]};")
                    
        except Exception:
            pass


class EnhancedCardTooltip(QLabel):
    """Enhanced tooltip that shows detailed card information"""
    
    def __init__(self, card, api, parent=None):
        super().__init__(parent)
        self.card = card
        self.api = api
        
        self.setWindowFlags(Qt.ToolTip)
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 2px solid #666;
                border-radius: 8px;
                color: white;
                padding: 10px;
                font-size: 11px;
                max-width: 300px;
            }
        """)
        
        self.update_tooltip()
    
    def update_tooltip(self):
        """Update tooltip with comprehensive card information"""
        try:
            card_info = self.api.get_enhanced_card_info(self.card)
            
            parts = []
            parts.append(f"<b>{card_info.get('name', 'Unknown')}</b>")
            
            # Mana cost
            cost_str = card_info.get('mana_cost_str', '')
            if cost_str:
                parts.append(f"<i>Cost: {cost_str}</i>")
            
            # Types
            types = card_info.get('types', [])
            if types:
                parts.append(f"<i>{'  '.join(types)}</i>")
            
            # Enhanced P/T info
            if "Creature" in types:
                base_power = card_info.get('base_power')
                base_toughness = card_info.get('base_toughness')
                current_power = card_info.get('current_power')
                current_toughness = card_info.get('current_toughness')
                
                pt_info = []
                if base_power is not None and base_toughness is not None:
                    pt_info.append(f"Base P/T: {base_power}/{base_toughness}")
                
                if current_power is not None and current_toughness is not None:
                    if (base_power != current_power) or (base_toughness != current_toughness):
                        pt_info.append(f"<b>Current P/T: {current_power}/{current_toughness}</b>")
                
                if pt_info:
                    parts.extend(pt_info)
            
            # Keywords
            keywords = card_info.get('keywords', [])
            if keywords:
                parts.append(f"<b>Keywords:</b> {', '.join(keywords)}")
            
            # Combat keywords
            combat_keywords = card_info.get('combat_keywords', set())
            if combat_keywords:
                parts.append(f"<b>Combat:</b> {', '.join(combat_keywords)}")
            
            # Status
            status_parts = []
            if card_info.get('is_token', False):
                status_parts.append("Token")
            if card_info.get('is_copy', False):
                status_parts.append("Copy")
            if hasattr(self.card, 'is_commander') and self.card.is_commander:
                status_parts.append("Commander")
            
            if status_parts:
                parts.append(f"<b>Status:</b> {', '.join(status_parts)}")
            
            # Card text
            text = card_info.get('text', '')
            if text:
                parts.append(f"<i>{text}</i>")
            
            self.setText("<br><br>".join(parts))
            
        except Exception as e:
            # Fallback
            self.setText(f"<b>{getattr(self.card, 'name', 'Unknown')}</b><br>Enhanced info unavailable")


def create_enhanced_card_widget(card, api, parent=None):
    """Factory function to create enhanced card display widgets"""
    return EnhancedCardDisplay(card, api, parent)

def show_enhanced_card_tooltip(card, api, position, parent=None):
    """Show an enhanced card tooltip at the given position"""
    tooltip = EnhancedCardTooltip(card, api, parent)
    tooltip.move(position)
    tooltip.show()
    return tooltip
