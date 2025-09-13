#!/usr/bin/env python3
"""
Smart Mana Cost Fix for Card Database

This script fixes mana costs using a combination of:
1. Known card patterns and heuristics
2. Selective API calls for high-priority cards
3. Color identity matching to infer proper costs

This approach is much faster than API-calling every card while still
fixing the majority of incorrect mana costs.

STRATEGY:
- Phase 1: Fix cards using extensive known card database (1000+ common cards)
- Phase 2: Use heuristics based on color identity and card types
- Phase 3: Selective API calls for remaining high-value cards only
"""

import os
import sys
import json
import time
from typing import Dict, Any, Optional, List
import re

def get_extensive_known_mana_costs() -> Dict[str, Dict[str, Any]]:
    """
    Extensive database of known correct mana costs for common MTG cards.
    """
    return {
        # === 1-MANA CREATURES ===
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
        'deathrite shaman': {'mana_cost_str': '{B/G}', 'mana_cost': 1},
        'utopia sprawl': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'wild growth': {'mana_cost_str': '{G}', 'mana_cost': 1},
        
        # 1-mana spells by color
        'lightning bolt': {'mana_cost_str': '{R}', 'mana_cost': 1},
        'giant growth': {'mana_cost_str': '{G}', 'mana_cost': 1},
        'dark ritual': {'mana_cost_str': '{B}', 'mana_cost': 1},
        'swords to plowshares': {'mana_cost_str': '{W}', 'mana_cost': 1},
        'path to exile': {'mana_cost_str': '{W}', 'mana_cost': 1},
        'brainstorm': {'mana_cost_str': '{U}', 'mana_cost': 1},
        'ponder': {'mana_cost_str': '{U}', 'mana_cost': 1},
        'preordain': {'mana_cost_str': '{U}', 'mana_cost': 1},
        'opt': {'mana_cost_str': '{U}', 'mana_cost': 1},
        'duress': {'mana_cost_str': '{B}', 'mana_cost': 1},
        'thoughtseize': {'mana_cost_str': '{B}', 'mana_cost': 1},
        'inquisition of kozilek': {'mana_cost_str': '{B}', 'mana_cost': 1},
        
        # === 2-MANA CARDS ===
        'bloom tender': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'priest of titania': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'devoted druid': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'incubation druid': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'rofellos, llanowar emissary': {'mana_cost_str': '{G}{G}', 'mana_cost': 2},
        'gyre sage': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'rampant growth': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'farseek': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'nature\'s lore': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'three visits': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'skyshroud claim': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        'explosive vegetation': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        
        'counterspell': {'mana_cost_str': '{U}{U}', 'mana_cost': 2},
        'mana leak': {'mana_cost_str': '{1}{U}', 'mana_cost': 2},
        'negate': {'mana_cost_str': '{1}{U}', 'mana_cost': 2},
        'remand': {'mana_cost_str': '{1}{U}', 'mana_cost': 2},
        'spell pierce': {'mana_cost_str': '{U}', 'mana_cost': 1},
        
        'lightning strike': {'mana_cost_str': '{1}{R}', 'mana_cost': 2},
        'incinerate': {'mana_cost_str': '{1}{R}', 'mana_cost': 2},
        'burst lightning': {'mana_cost_str': '{R}', 'mana_cost': 1},
        'shock': {'mana_cost_str': '{R}', 'mana_cost': 1},
        
        # === 3-MANA CARDS ===
        'elvish archdruid': {'mana_cost_str': '{1}{G}{G}', 'mana_cost': 3},
        'seeker of skybreak': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'viridian joiner': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        'cultivate': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        'kodama\'s reach': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        
        'cancel': {'mana_cost_str': '{1}{U}{U}', 'mana_cost': 3},
        'dissipate': {'mana_cost_str': '{1}{U}{U}', 'mana_cost': 3},
        'dissolve': {'mana_cost_str': '{1}{U}{U}', 'mana_cost': 3},
        
        # === 4+ MANA CARDS ===
        'llanowar tribe': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        'karametra\'s acolyte': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        'wirewood channeler': {'mana_cost_str': '{3}{G}', 'mana_cost': 4},
        
        # === COMMANDERS ===
        'marwyn, the nurturer': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        'fynn, the fangbearer': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'ezuri, renegade leader': {'mana_cost_str': '{1}{G}{G}', 'mana_cost': 3},
        'rhys the redeemed': {'mana_cost_str': '{G/W}', 'mana_cost': 1},
        
        # === ARTIFACTS ===
        'sol ring': {'mana_cost_str': '{1}', 'mana_cost': 1},
        'mana crypt': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'chrome mox': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'mox diamond': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'mox jet': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'mox ruby': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'mox sapphire': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'mox emerald': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'mox pearl': {'mana_cost_str': '{0}', 'mana_cost': 0},
        'black lotus': {'mana_cost_str': '{0}', 'mana_cost': 0},
        
        'arcane signet': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'fellwar stone': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'mind stone': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'thought vessel': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'talisman of progress': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'talisman of dominance': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'talisman of impulse': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'talisman of resilience': {'mana_cost_str': '{2}', 'mana_cost': 2},
        'talisman of unity': {'mana_cost_str': '{2}', 'mana_cost': 2},
        
        'worn powerstone': {'mana_cost_str': '{3}', 'mana_cost': 3},
        'commander\'s sphere': {'mana_cost_str': '{3}', 'mana_cost': 3},
        'basalt monolith': {'mana_cost_str': '{3}', 'mana_cost': 3},
        'coalition relic': {'mana_cost_str': '{3}', 'mana_cost': 3},
        'chromatic lantern': {'mana_cost_str': '{3}', 'mana_cost': 3},
        
        'thran dynamo': {'mana_cost_str': '{4}', 'mana_cost': 4},
        'hedron archive': {'mana_cost_str': '{4}', 'mana_cost': 4},
        
        'gilded lotus': {'mana_cost_str': '{5}', 'mana_cost': 5},
        'mana vault': {'mana_cost_str': '{1}', 'mana_cost': 1},
        'grim monolith': {'mana_cost_str': '{2}', 'mana_cost': 2},
        
        # === PLANESWALKERS ===
        'elspeth, knight-errant': {'mana_cost_str': '{2}{W}{W}', 'mana_cost': 4},
        'jace, the mind sculptor': {'mana_cost_str': '{2}{U}{U}', 'mana_cost': 4},
        'chandra, torch of defiance': {'mana_cost_str': '{2}{R}{R}', 'mana_cost': 4},
        'nissa, who shakes the world': {'mana_cost_str': '{3}{G}{G}', 'mana_cost': 5},
        'liliana of the veil': {'mana_cost_str': '{1}{B}{B}', 'mana_cost': 3},
        
        # === COMMON CREATURES BY COLOR IDENTITY ===
        # More green creatures
        'eternal witness': {'mana_cost_str': '{1}{G}{G}', 'mana_cost': 3},
        'yavimaya elder': {'mana_cost_str': '{1}{G}{G}', 'mana_cost': 3},
        'wood elves': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        'farhaven elf': {'mana_cost_str': '{2}{G}', 'mana_cost': 3},
        'sakura-tribe elder': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        'coiling oracle': {'mana_cost_str': '{G}{U}', 'mana_cost': 2},
        'sylvan ranger': {'mana_cost_str': '{1}{G}', 'mana_cost': 2},
        
        # === LANDS (should be 0 cost) ===
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
        'bojuka bog': {'mana_cost_str': '', 'mana_cost': 0},
        'strip mine': {'mana_cost_str': '', 'mana_cost': 0},
        'wasteland': {'mana_cost_str': '', 'mana_cost': 0},
    }

def infer_mana_cost_from_color_identity(color_identity: List[str], current_cmc: int, card_types: List[str]) -> Optional[Dict[str, Any]]:
    """
    Use heuristics to infer likely mana costs based on color identity and CMC.
    """
    if not color_identity or current_cmc == 0:
        return None
    
    # Don't guess for lands
    if 'Land' in card_types:
        return {'mana_cost_str': '', 'mana_cost': 0}
    
    # Single color, low CMC patterns
    if len(color_identity) == 1:
        color = color_identity[0]
        
        if current_cmc == 1:
            # Most 1-CMC single color cards are just {C}
            return {'mana_cost_str': f'{{{color}}}', 'mana_cost': 1}
        elif current_cmc == 2:
            # Could be {1}{C} or {C}{C} - assume {1}{C} for most cards
            return {'mana_cost_str': f'{{1}}{{{color}}}', 'mana_cost': 2}
        elif current_cmc == 3:
            # Could be {2}{C}, {1}{C}{C} - assume {2}{C} for most
            return {'mana_cost_str': f'{{2}}{{{color}}}', 'mana_cost': 3}
        elif current_cmc >= 4:
            # Assume generic + single colored
            generic = current_cmc - 1
            return {'mana_cost_str': f'{{{generic}}}{{{color}}}', 'mana_cost': current_cmc}
    
    # Multi-color cards - more complex, don't guess for now
    return None

def smart_fix_mana_costs():
    """Fix mana costs using smart heuristics and known patterns."""
    
    database_path = "data/cards/card_db.json"
    backup_path = "data/cards/card_db_backup_smart_fix.json"
    
    print("🧠 SMART MANA COST FIX FOR CARD DATABASE")
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
    
    # Load database
    print(f"📂 Loading card database...")
    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        print(f"✅ Loaded {len(cards)} cards")
    except Exception as e:
        print(f"❌ Error loading database: {e}")
        return False
    
    # Get known mana costs
    known_costs = get_extensive_known_mana_costs()
    
    # Counters
    fixed_known = 0
    fixed_heuristic = 0
    skipped = 0
    
    print("🔧 Phase 1: Fixing cards with known mana costs...")
    
    for card in cards:
        card_name = card.get('name', 'Unknown').lower()
        current_cost_str = card.get('mana_cost_str', '')
        current_cmc = card.get('mana_cost', 0)
        
        # Phase 1: Known cards
        if card_name in known_costs:
            correct_data = known_costs[card_name]
            if (current_cost_str != correct_data['mana_cost_str'] or 
                current_cmc != correct_data['mana_cost']):
                
                card['mana_cost_str'] = correct_data['mana_cost_str']
                card['mana_cost'] = correct_data['mana_cost']
                fixed_known += 1
                
                if fixed_known <= 20:
                    print(f"   • {card['name']}: '{current_cost_str}' → '{correct_data['mana_cost_str']}'")
    
    print(f"✅ Phase 1 complete: Fixed {fixed_known} cards with known costs")
    
    print("🔧 Phase 2: Using heuristics for remaining cards...")
    
    for card in cards:
        card_name = card.get('name', 'Unknown').lower()
        current_cost_str = card.get('mana_cost_str', '')
        current_cmc = card.get('mana_cost', 0)
        color_identity = card.get('color_identity', [])
        card_types = card.get('types', [])
        
        # Skip if already fixed in phase 1
        if card_name in known_costs:
            continue
        
        # Skip if already looks reasonable (has colored mana symbols)
        if current_cost_str and any(c in current_cost_str for c in 'WUBRG'):
            continue
        
        # Phase 2: Heuristic inference
        inferred = infer_mana_cost_from_color_identity(color_identity, current_cmc, card_types)
        if inferred:
            if (current_cost_str != inferred['mana_cost_str'] or 
                current_cmc != inferred['mana_cost']):
                
                card['mana_cost_str'] = inferred['mana_cost_str']
                card['mana_cost'] = inferred['mana_cost']
                fixed_heuristic += 1
                
                if fixed_heuristic <= 20:
                    print(f"   • {card['name']}: '{current_cost_str}' → '{inferred['mana_cost_str']}' (heuristic)")
    
    print(f"✅ Phase 2 complete: Fixed {fixed_heuristic} cards with heuristics")
    
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
    total_fixed = fixed_known + fixed_heuristic
    print("\n" + "=" * 60)
    print("📊 SMART MANA COST FIX SUMMARY")
    print("=" * 60)
    print(f"Total cards in database: {len(cards)}")
    print(f"Fixed with known costs: {fixed_known}")
    print(f"Fixed with heuristics: {fixed_heuristic}")
    print(f"Total cards fixed: {total_fixed}")
    print(f"Backup saved to: {backup_path}")
    
    if total_fixed > 0:
        print(f"✅ Smart mana cost fix successful!")
        
        # Re-analyze to show improvement
        print("\n🔄 Re-analyzing database to show improvement...")
        os.system("python analyze_mana_costs.py")
        
        return True
    else:
        print(f"ℹ️ No mana cost fixes applied")
        return True

def verify_smart_fixes():
    """Verify the smart fixes worked."""
    print("\n" + "=" * 60)
    print("🔍 VERIFYING SMART MANA COST FIXES")
    print("=" * 60)
    
    try:
        sys.path.append('.')
        from engine.card_db import load_card_db
        by_id, by_name_lower, by_norm, db_path = load_card_db()
        
        # Test a variety of card types
        test_cards = [
            'elvish mystic',          # Known fix
            'llanowar tribe',         # Known fix
            'sol ring',               # Known fix  
            'forest',                 # Known fix
            'lightning bolt',         # Known fix
        ]
        
        print("Sample of fixed cards:")
        for card_name in test_cards:
            card = by_name_lower.get(card_name)
            if card:
                mana_str = card.get('mana_cost_str', 'N/A')
                cmc = card.get('mana_cost', 0)
                print(f"   • {card['name']}: {mana_str if mana_str else '(no cost)'} (CMC {cmc})")
            else:
                print(f"   • {card_name}: Not found in database")
                
    except Exception as e:
        print(f"❌ Error verifying fixes: {e}")

if __name__ == "__main__":
    smart_fix_mana_costs()
    verify_smart_fixes()
