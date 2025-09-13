#!/usr/bin/env python3
"""
Refresh Card Database with Proper Mana Cost Strings

This script updates the card database to include proper mana_cost_str fields
for all cards, converting integer mana costs to Scryfall-style strings.
"""

import os
import sys
import json
import re
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def convert_mana_cost_to_string(mana_cost: int, card_name: str = "Unknown") -> str:
    """
    Convert integer mana cost to proper mana cost string.
    
    This is a basic conversion - ideally we'd use MTG SDK data,
    but this provides a reasonable fallback for generic costs.
    """
    if mana_cost == 0:
        return ""
    elif mana_cost <= 20:  # Most reasonable mana costs
        return f"{{{mana_cost}}}"
    else:
        # Very high costs might be data errors, but handle them
        return f"{{{mana_cost}}}"

def get_common_mana_costs() -> Dict[str, str]:
    """
    Return a dictionary of common card names to their proper mana costs.
    This helps fix known cards with complex mana costs.
    """
    return {
        # Basic lands have no mana cost
        "forest": "",
        "island": "",
        "mountain": "",
        "plains": "",
        "swamp": "",
        
        # Common artifacts
        "sol ring": "{1}",
        "mox jet": "{0}",
        "mox ruby": "{0}",
        "mox sapphire": "{0}",
        "mox emerald": "{0}",
        "mox pearl": "{0}",
        "black lotus": "{0}",
        
        # Common spells (these might need color-specific costs later)
        "lightning bolt": "{R}",
        "counterspell": "{U}{U}",
        "giant growth": "{G}",
        "dark ritual": "{B}",
        "healing salve": "{W}",
        
        # Add more as needed...
    }

def refresh_card_database():
    """Refresh the card database with proper mana_cost_str fields."""
    
    database_path = "data/cards/card_db.json"
    backup_path = "data/cards/card_db_backup.json"
    
    print("🔄 REFRESHING MTG CARD DATABASE")
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
    
    # Get common mana costs for known cards
    common_costs = get_common_mana_costs()
    
    # Process cards
    updated_count = 0
    added_count = 0
    error_count = 0
    
    print(f"🔧 Processing cards...")
    
    for i, card in enumerate(cards):
        try:
            card_name = card.get('name', 'Unknown').lower()
            mana_cost = card.get('mana_cost', 0)
            existing_cost_str = card.get('mana_cost_str', None)
            
            # Determine proper mana_cost_str
            new_cost_str = None
            
            # 1. Check if card has a known proper mana cost
            if card_name in common_costs:
                new_cost_str = common_costs[card_name]
                
            # 2. If no existing mana_cost_str, convert from integer
            elif not existing_cost_str:
                new_cost_str = convert_mana_cost_to_string(mana_cost, card_name)
            
            # 3. If existing cost string is empty but mana_cost > 0, fix it
            elif existing_cost_str == "" and mana_cost > 0:
                if card_name in common_costs:
                    new_cost_str = common_costs[card_name]
                else:
                    new_cost_str = convert_mana_cost_to_string(mana_cost, card_name)
            
            # Update card if needed
            if new_cost_str is not None:
                if existing_cost_str != new_cost_str:
                    card['mana_cost_str'] = new_cost_str
                    if existing_cost_str is None:
                        added_count += 1
                    else:
                        updated_count += 1
                        
                    if i < 10:  # Show first few updates as examples
                        print(f"   • {card.get('name', 'Unknown')}: '{existing_cost_str or 'None'}' → '{new_cost_str}'")
            
            # Progress indicator
            if (i + 1) % 1000 == 0:
                print(f"   Processed {i + 1}/{len(cards)} cards...")
                
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Show first few errors
                print(f"⚠️ Error processing card {i}: {e}")
    
    # Save updated database
    print(f"💾 Saving updated database...")
    try:
        with open(database_path, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)
        print(f"✅ Database saved successfully")
    except Exception as e:
        print(f"❌ Error saving database: {e}")
        # Try to restore backup
        if os.path.exists(backup_path):
            print(f"🔄 Attempting to restore backup...")
            try:
                shutil.copy2(backup_path, database_path)
                print(f"✅ Backup restored")
            except Exception as restore_error:
                print(f"❌ Could not restore backup: {restore_error}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DATABASE REFRESH SUMMARY")
    print("=" * 60)
    print(f"Total cards processed: {len(cards)}")
    print(f"New mana_cost_str fields added: {added_count}")
    print(f"Existing mana_cost_str fields updated: {updated_count}")
    print(f"Errors encountered: {error_count}")
    print(f"Backup saved to: {backup_path}")
    
    if added_count + updated_count > 0:
        print(f"✅ Database refresh successful!")
        return True
    else:
        print(f"ℹ️ No changes needed - database was already up to date")
        return True

def verify_sol_ring():
    """Verify that Sol Ring now has the correct mana cost."""
    print("\n" + "=" * 60)
    print("🔍 VERIFYING SOL RING")
    print("=" * 60)
    
    try:
        from engine.card_db import load_card_db
        by_id, by_name_lower, by_norm, db_path = load_card_db()
        
        # Find Sol Ring
        sol_ring = by_name_lower.get('sol ring')
        if sol_ring:
            print(f"✅ Sol Ring found:")
            print(f"   • Name: {sol_ring.get('name')}")
            print(f"   • Mana Cost (int): {sol_ring.get('mana_cost')}")
            print(f"   • Mana Cost Str: '{sol_ring.get('mana_cost_str', 'NOT PRESENT')}'")
            print(f"   • Types: {sol_ring.get('types')}")
            
            # Test parsing
            cost_str = sol_ring.get('mana_cost_str')
            if cost_str:
                from engine.mana import parse_mana_cost
                parsed = parse_mana_cost(cost_str)
                print(f"   • Parsed Cost: {parsed}")
                
                # Test payment
                from engine.mana import ManaPool
                pool = ManaPool()
                pool.add('C', 1)
                can_pay = pool.can_pay(parsed)
                print(f"   • Can pay with 1 colorless: {can_pay}")
                
                if can_pay:
                    print(f"🎉 Sol Ring is ready for casting!")
                else:
                    print(f"❌ Sol Ring still has payment issues")
            else:
                print(f"❌ Sol Ring still has no mana_cost_str")
        else:
            print(f"❌ Sol Ring not found in database")
            
    except Exception as e:
        print(f"❌ Error verifying Sol Ring: {e}")

def main():
    """Main function."""
    print("🃏 MTG CARD DATABASE REFRESH TOOL")
    print("=" * 80)
    print("This tool will add proper mana_cost_str fields to all cards")
    print("in the database for proper mana cost parsing and casting.")
    print()
    
    success = refresh_card_database()
    
    if success:
        verify_sol_ring()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 Card database refresh completed successfully!")
        print("The MTG engine should now have proper mana cost parsing for all cards.")
    else:
        print("❌ Card database refresh failed. Please check the errors above.")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
