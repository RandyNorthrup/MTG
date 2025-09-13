#!/usr/bin/env python3
"""
Analyze Mana Costs in Card Database

This script analyzes the card database to identify how many cards have 
incorrect mana costs before running the comprehensive fix.

It categorizes cards by their current mana cost patterns to help understand
the scope of the problem.
"""

import os
import sys
import json
from collections import defaultdict
import re

def analyze_mana_costs():
    """Analyze mana costs in the database to understand the scope of the problem."""
    
    database_path = "data/cards/card_db.json"
    
    print("🔍 ANALYZING MANA COSTS IN CARD DATABASE")
    print("=" * 60)
    
    # Check if database exists
    if not os.path.exists(database_path):
        print(f"❌ Card database not found: {database_path}")
        return False
    
    # Load database
    print(f"📂 Loading card database...")
    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        print(f"✅ Loaded {len(cards)} cards")
    except Exception as e:
        print(f"❌ Error loading database: {e}")
        return False
    
    # Analysis categories
    empty_mana_cost_str = 0
    pure_numeric_costs = 0  # Like {1}, {2}, {3}
    colored_costs = 0       # Like {G}, {1}{G}, {U}{U}
    zero_costs = 0          # {0} or empty
    complex_costs = 0       # Hybrid, phyrexian, etc
    invalid_costs = 0       # Malformed
    
    pure_numeric_examples = []
    colored_cost_examples = []
    complex_cost_examples = []
    
    # Pattern matching
    pure_numeric_pattern = re.compile(r'^\{(\d+)\}$')
    colored_pattern = re.compile(r'\{[WUBRG]\}')
    hybrid_pattern = re.compile(r'\{[^}]*\/[^}]*\}')
    
    print("🔧 Analyzing mana cost patterns...")
    
    for card in cards:
        name = card.get('name', 'Unknown')
        mana_cost_str = card.get('mana_cost_str', '')
        mana_cost = card.get('mana_cost', 0)
        types = card.get('types', [])
        
        # Skip lands (they should have no mana cost)
        if 'Land' in types:
            if not mana_cost_str and mana_cost == 0:
                continue  # Correct for lands
            elif mana_cost_str or mana_cost > 0:
                invalid_costs += 1
                print(f"   ⚠️ Land with mana cost: {name} - {mana_cost_str} (CMC {mana_cost})")
            continue
        
        # Empty mana cost string
        if not mana_cost_str:
            empty_mana_cost_str += 1
            if len(pure_numeric_examples) < 5:
                pure_numeric_examples.append(f"{name} (no cost string, CMC {mana_cost})")
            continue
        
        # Zero cost
        if mana_cost_str in ['{0}', ''] and mana_cost == 0:
            zero_costs += 1
            continue
        
        # Pure numeric costs (likely wrong for most cards)
        pure_numeric_match = pure_numeric_pattern.match(mana_cost_str)
        if pure_numeric_match:
            pure_numeric_costs += 1
            if len(pure_numeric_examples) < 10:
                pure_numeric_examples.append(f"{name}: {mana_cost_str} (CMC {mana_cost})")
            continue
        
        # Colored costs (likely correct or closer to correct)
        if colored_pattern.search(mana_cost_str):
            colored_costs += 1
            if len(colored_cost_examples) < 5:
                colored_cost_examples.append(f"{name}: {mana_cost_str} (CMC {mana_cost})")
            continue
        
        # Complex costs (hybrid, phyrexian, etc.)
        if hybrid_pattern.search(mana_cost_str) or any(c in mana_cost_str for c in 'XYZP/'):
            complex_costs += 1
            if len(complex_cost_examples) < 5:
                complex_cost_examples.append(f"{name}: {mana_cost_str} (CMC {mana_cost})")
            continue
        
        # If we get here, it's an invalid/unrecognized pattern
        invalid_costs += 1
        if invalid_costs <= 5:
            print(f"   ⚠️ Invalid cost pattern: {name} - '{mana_cost_str}' (CMC {mana_cost})")
    
    # Calculate totals
    total_non_lands = len(cards) - sum(1 for c in cards if 'Land' in c.get('types', []))
    likely_incorrect = empty_mana_cost_str + pure_numeric_costs
    
    # Results
    print("\n" + "=" * 60)
    print("📊 MANA COST ANALYSIS RESULTS")
    print("=" * 60)
    print(f"Total cards analyzed: {len(cards)}")
    print(f"Non-land cards: {total_non_lands}")
    print()
    print("COST PATTERN BREAKDOWN:")
    print(f"   Empty mana cost string: {empty_mana_cost_str}")
    print(f"   Pure numeric costs (likely wrong): {pure_numeric_costs}")
    print(f"   Colored costs (likely correct): {colored_costs}")
    print(f"   Zero costs: {zero_costs}")
    print(f"   Complex costs: {complex_costs}")
    print(f"   Invalid/malformed: {invalid_costs}")
    print()
    print(f"📈 LIKELY INCORRECT COSTS: {likely_incorrect} ({likely_incorrect/total_non_lands*100:.1f}% of non-lands)")
    print(f"📉 LIKELY CORRECT COSTS: {colored_costs + complex_costs} ({(colored_costs + complex_costs)/total_non_lands*100:.1f}% of non-lands)")
    
    # Show examples
    if pure_numeric_examples:
        print("\n" + "🔍 EXAMPLES OF PURE NUMERIC COSTS (likely incorrect):")
        for example in pure_numeric_examples:
            print(f"   • {example}")
    
    if colored_cost_examples:
        print("\n" + "✅ EXAMPLES OF COLORED COSTS (likely correct):")
        for example in colored_cost_examples:
            print(f"   • {example}")
    
    if complex_cost_examples:
        print("\n" + "🎯 EXAMPLES OF COMPLEX COSTS:")
        for example in complex_cost_examples:
            print(f"   • {example}")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS")
    print("=" * 60)
    
    if likely_incorrect > total_non_lands * 0.1:  # More than 10% incorrect
        print(f"🚨 HIGH PRIORITY: {likely_incorrect} cards likely have incorrect mana costs")
        print("   Recommend running the comprehensive fix script: python fix_all_mana_costs.py")
    elif likely_incorrect > 0:
        print(f"⚠️  MEDIUM PRIORITY: {likely_incorrect} cards may have incorrect mana costs")
        print("   Consider running the comprehensive fix script for accuracy")
    else:
        print("✅ LOW PRIORITY: Most cards appear to have reasonable mana cost patterns")
    
    print(f"\nThe comprehensive fix would need to process ~{total_non_lands} non-land cards")
    print(f"Estimated time: {(total_non_lands * 0.5) / 60:.0f}-{(total_non_lands * 1.0) / 60:.0f} minutes")
    
    return True

if __name__ == "__main__":
    analyze_mana_costs()
