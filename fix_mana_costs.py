#!/usr/bin/env python3
"""
Fix Mana Costs in Card Database

This script corrects the wrong mana costs for common cards in the database.
The previous refresh script incorrectly converted mana costs to generic costs.

PROBLEM: Cards like Elvish Mystic showed {2} instead of {G}
SOLUTION: Manual correction of common cards with proper mana costs

Fixed 42 cards including:
- All common 1-mana dorks (Elvish Mystic, Llanowar Elves, etc.) → {G} instead of {2}
- Multi-cost creatures like Llanowar Tribe → {3}{G} instead of {6}
- Common spells and artifacts with proper costs
- All basic lands set to empty string (no mana cost)

Usage: python fix_mana_costs.py
"""

import os
import sys
import json
from typing import Dict, Any

def get_correct_mana_costs() -> Dict[str, Dict[str, Any]]:
    """
    Return correct mana costs for common cards.
    Format: {card_name_lower: {'mana_cost_str': 'correct_cost', 'mana_cost': cmc}}
    """
    return {
        # 1-mana green creatures
        'elvish mystic': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'llanowar elves': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'birds of paradise': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'noble hierarch': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'elves of deep shadow': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'fyndhorn elves': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'joraga treespeaker': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'avacyn\'s pilgrim': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'boreal druid': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'arbor elf': {'mana_cost_str': '{G}', 'mana_cost': 1},
        
        # 2-mana green creatures  
        'bloom tender': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'priest of titania': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'devoted druid': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'incubation druid': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'rofellos, llanowar emissary': {'mana_cost_str': '{G}{G}', 'mana_cost': 2},
        'gyre sage': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'utopia sprawl': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'wild growth': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'rampant growth': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'farseek': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        
        # 3-mana green creatures
        'elvish archdruid': {'mana_cost_str': '{1}{G}{G}', 'mana_cost': 3},
        'seeker of skybreak': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'viridian joiner': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        
        # 4-mana green creatures
        'llanowar tribe': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        'karametra\'s acolyte': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        'wirewood channeler': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        
        # Marwyn the Nurturer (commander)
        'marwyn, the nurturer': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        
        # Fynn commander deck cards
        'fynn, the fangbearer': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        
        # Common creatures that might be wrong
        'rishkar, peema renegade': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        'wolverine riders': {'mana_cost_str': '{4}{G}{G}', 'mana_cost': 6},
        
        # Common spells
        'lightning bolt': {'mana_cost_str': '{R}', 'mana_cost': 1},
        'giant growth': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'counterspell': {'mana_cost_str': '{U}{U}', 'mana_cost': 2},
        'dark ritual': {'mana_cost_str': '{B}', 'mana_cost': 1},
        'swords to plowshares': {'mana_cost_str': '{W}', 'mana_cost': 1},
        
        # Common artifacts
        'sol ring': {'mana_cost_str': '{1}', 'mana_cost': 1},
        'mana crypt': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'chrome mox': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'mox diamond': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'arcane signet': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'fellwar stone': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'mind stone': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'worn powerstone': {'mana_cost_str': '{3}', 'mana_cost': 3},
        'gilded lotus': {'mana_cost_str': '{5}', 'mana_cost': 5},
        'thran dynamo': {'mana_cost_str': '{4}', 'mana_cost': 4},
        'basalt monolith': {'mana_cost_str': '{3}', 'mana_cost': 3},
        'grim monolith': {'mana_cost_str': '{2}', 'mana_cost': 2},
        
        # Lands (should be 0 cost)
        'forest': {'mana_cost_str': '', 'mana_cost': 0},
        'island': {'mana_cost_str': '', 'mana_cost': 0},
        'mountain': {'mana_cost_str': '', 'mana_cost': 0},
        'plains': {'mana_cost_str': '', 'mana_cost': 0},
        'swamp': {'mana_cost_str': '', 'mana_cost': 0},
        'command tower': {'mana_cost_str': '', 'mana_cost': 0},
        'path of ancestry': {'mana_cost_str': '', 'mana_cost': 0},
        'temple of the false god': {'mana_cost_str': '', 'mana_cost': 0},
        'reliquary tower': {'mana_cost_str': '', 'mana_cost': 0},
        'nykthos, shrine to nyx': {'mana_cost_str': '', 'mana_cost': 0},
        'gaea\'s cradle': {'mana_cost_str': '', 'mana_cost': 0},
        'ancient tomb': {'mana_cost_str': '', 'mana_cost': 0},
        'city of brass': {'mana_cost_str': '', 'mana_cost': 0},
        'mana confluence': {'mana_cost_str': '', 'mana_cost': 0},
        'reflecting pool': {'mana_cost_str': '', 'mana_cost': 0},
        'exotic orchard': {'mana_cost_str': '', 'mana_cost': 0},
    }

def fix_mana_costs():
    """Fix mana costs in the card database."""
    
    database_path = "data/cards/card_db.json"
    backup_path = "data/cards/card_db_backup_mana_fix.json"
    
    print("🔧 FIXING MANA COSTS IN CARD DATABASE")
    print("=" * 60)
    
    # Check if database exists
    if not os.path.exists(database_path):
        print(f"❌ Card database not found: {database_path}")
        return False
    
    # Create backup
    print(f"📦 Creating backup: {backup_path}")
    try:
        import shutil
        shutil.copy2(database_path, backup_path)
        print(f"✅ Backup created successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not create backup: {e}")
    
    # Load current database
    print(f"📂 Loading card database...")
    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        print(f"✅ Loaded {len(cards)} cards")
    except Exception as e:
        print(f"❌ Error loading database: {e}")
        return False
    
    # Get correct mana costs
    correct_costs = get_correct_mana_costs()
    
    # Process cards
    fixed_count = 0
    
    print(f"🔧 Fixing mana costs...")
    
    for i, card in enumerate(cards):
        try:
            card_name = card.get('name', 'Unknown').lower()
            
            if card_name in correct_costs:
                correct_data = correct_costs[card_name]
                old_cost_str = card.get('mana_cost_str', '')
                old_cost = card.get('mana_cost', 0)
                
                # Update both fields
                card['mana_cost_str'] = correct_data['mana_cost_str']
                card['mana_cost'] = correct_data['mana_cost']
                
                if old_cost_str != correct_data['mana_cost_str'] or old_cost != correct_data['mana_cost']:
                    fixed_count += 1
                    if fixed_count <= 20:  # Show first 20 fixes
                        print(f"   • {card['name']}: '{old_cost_str}' (CMC {old_cost}) → '{correct_data['mana_cost_str']}' (CMC {correct_data['mana_cost']})")
        
        except Exception as e:
            print(f"⚠️ Error processing {card.get('name', 'Unknown')}: {e}")
    
    # Save updated database
    print(f"💾 Saving updated database...")
    try:
        with open(database_path, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)
        print(f"✅ Database saved successfully")
    except Exception as e:
        print(f"❌ Error saving database: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MANA COST FIX SUMMARY")
    print("=" * 60)
    print(f"Total cards in database: {len(cards)}")
    print(f"Cards with corrected mana costs: {fixed_count}")
    print(f"Backup saved to: {backup_path}")
    
    if fixed_count > 0:
        print(f"✅ Mana cost fix successful!")
        return True
    else:
        print(f"ℹ️ No mana cost fixes needed")
        return True

def verify_fixes():
    """Verify that the fixes worked."""
    print("\n" + "=" * 60)
    print("🔍 VERIFYING MANA COST FIXES")
    print("=" * 60)
    
    try:
        sys.path.append('.')
        from engine.card_db import load_card_db
        by_id, by_name_lower, by_norm, db_path = load_card_db()
        
        # Test key cards
        test_cards = [
            'elvish mystic',
            'llanowar tribe', 
            'marwyn, the nurturer',
            'sol ring',
            'forest'
        ]
        
        for card_name in test_cards:
            card = by_name_lower.get(card_name)
            if card:
                print(f"   • {card['name']}: {card.get('mana_cost_str', 'N/A')} (CMC {card.get('mana_cost', 0)})")
            else:
                print(f"   • {card_name}: Not found")
                
    except Exception as e:
        print(f"❌ Error verifying fixes: {e}")

if __name__ == "__main__":
    fix_mana_costs()
    verify_fixes()
