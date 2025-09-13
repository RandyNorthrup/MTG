#!/usr/bin/env python3
"""Quick test to verify mana cost fixes."""

import sys
sys.path.append('.')
from engine.card_db import load_card_db

def test_key_cards():
    """Test key cards from the user's decks."""
    print("🎯 Testing key cards from your decks:")
    
    by_id, by_name_lower, by_norm, db_path = load_card_db()
    
    test_cards = [
        'elvish mystic',
        'llanowar tribe', 
        'rishkar, peema renegade',
        'wolverine riders',
        'marwyn, the nurturer',
        'fynn, the fangbearer',
        'sol ring',
        'arcane signet',
        'lightning bolt',
        'forest'
    ]
    
    for name in test_cards:
        card = by_name_lower.get(name)
        if card:
            mana_str = card.get('mana_cost_str', 'NO COST')
            cmc = card.get('mana_cost', 0)
            print(f"  ✅ {card['name']}: {mana_str if mana_str else '(no cost)'} (CMC {cmc})")
        else:
            print(f"  ❌ {name}: NOT FOUND")

if __name__ == "__main__":
    test_key_cards()
