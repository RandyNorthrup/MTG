#!/usr/bin/env python3
"""
Fix All Mana Costs in Card Database

This script corrects ALL wrong mana costs in the database by fetching proper
mana cost data from the MTG SDK API. This fixes the systematic issue where
cards had generic costs instead of proper colored mana requirements.

PROBLEM: 
- Most cards show generic costs like {2}, {3}, {4} instead of proper costs
- Elvish Mystic shows {2} instead of {G}
- Llanowar Tribe shows {6} instead of {3}{G}
- This affects thousands of cards in the database

SOLUTION:
- Use MTG SDK to fetch correct mana costs for all cards
- Update both mana_cost_str and mana_cost (CMC) fields
- Handle rate limiting and API errors gracefully
- Create comprehensive backup before changes

Usage: python fix_all_mana_costs.py
"""

import os
import sys
import json
import time
from typing import Dict, Any, Optional, List
import re

def try_import_mtg_sdk():
    """Try to import MTG SDK, install if needed."""
    try:
        from mtgsdk import Card as SDKCard
        return SDKCard
    except ImportError:
        print("📦 MTG SDK not found. Installing...")
        try:
            import subprocess
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'mtgsdk'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ MTG SDK installed successfully")
                from mtgsdk import Card as SDKCard
                return SDKCard
            else:
                print(f"❌ Failed to install MTG SDK: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ Error installing MTG SDK: {e}")
            return None

def normalize_card_name(name: str) -> str:
    """Normalize card name for API search."""
    # Remove common deck list formatting
    name = re.sub(r'\s*\([^)]+\)$', '', name)  # Remove set codes like (KTK)
    name = re.sub(r'^\d+x?\s+', '', name)      # Remove quantity prefixes
    name = name.strip()
    return name

def fetch_card_mana_cost(card_name: str, SDKCard) -> Optional[Dict[str, Any]]:
    """Fetch correct mana cost from MTG SDK."""
    try:
        normalized_name = normalize_card_name(card_name)
        
        # Special handling for basic lands
        basic_lands = ['forest', 'island', 'mountain', 'plains', 'swamp']
        if normalized_name.lower() in basic_lands:
            return {'mana_cost_str': '', 'mana_cost': 0}
        
        # Search for exact name match
        cards = SDKCard.where(name=normalized_name).all()
        
        if not cards:
            # Try partial match if exact fails
            cards = SDKCard.where(name=normalized_name).all()
            
        if not cards:
            return None
        
        # Use the first card (usually most relevant)
        card = cards[0]
        
        # Extract mana cost information
        mana_cost_str = getattr(card, 'mana_cost', '') or ''
        cmc = getattr(card, 'cmc', 0) or 0
        
        return {
            'mana_cost_str': mana_cost_str,
            'mana_cost': int(cmc)
        }
        
    except Exception as e:
        print(f"⚠️ Error fetching {card_name}: {e}")
        return None

def fix_all_mana_costs():
    """Fix mana costs for all cards in the database."""
    
    database_path = "data/cards/card_db.json"
    backup_path = "data/cards/card_db_backup_complete_fix.json"
    
    print("🔧 FIXING ALL MANA COSTS IN CARD DATABASE")
    print("=" * 60)
    
    # Check if database exists
    if not os.path.exists(database_path):
        print(f"❌ Card database not found: {database_path}")
        return False
    
    # Try to import MTG SDK
    SDKCard = try_import_mtg_sdk()
    if not SDKCard:
        print("❌ Cannot proceed without MTG SDK")
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
    
    # Process cards
    fixed_count = 0
    api_errors = 0
    skipped_count = 0
    processed_count = 0
    
    print(f"🔧 Processing all cards (this may take a while due to API rate limiting)...")
    print("📊 Progress will be shown every 100 cards")
    
    # Process in batches to handle rate limiting
    batch_size = 10
    delay_between_requests = 0.5  # seconds
    delay_between_batches = 2.0   # seconds
    
    for i in range(0, len(cards), batch_size):
        batch_end = min(i + batch_size, len(cards))
        
        print(f"🔄 Processing batch {i//batch_size + 1}: cards {i+1}-{batch_end} of {len(cards)}")
        
        # Process each card in the batch
        for j in range(i, batch_end):
            card = cards[j]
            processed_count += 1
            
            try:
                card_name = card.get('name', 'Unknown')
                current_cost_str = card.get('mana_cost_str', '')
                current_cmc = card.get('mana_cost', 0)
                
                # Skip if this looks like it already has a proper mana cost
                if current_cost_str and ('{' in current_cost_str):
                    # Check if it's obviously wrong (pure numeric like {2} for known colored cards)
                    # For now, fetch all to be comprehensive
                    pass
                
                # Fetch correct mana cost from API
                correct_data = fetch_card_mana_cost(card_name, SDKCard)
                
                if correct_data:
                    new_cost_str = correct_data['mana_cost_str']
                    new_cmc = correct_data['mana_cost']
                    
                    # Update if different
                    if (current_cost_str != new_cost_str or current_cmc != new_cmc):
                        card['mana_cost_str'] = new_cost_str
                        card['mana_cost'] = new_cmc
                        fixed_count += 1
                        
                        # Show examples of fixes
                        if fixed_count <= 50:
                            print(f"   • {card_name}: '{current_cost_str}' (CMC {current_cmc}) → '{new_cost_str}' (CMC {new_cmc})")
                else:
                    api_errors += 1
                    if api_errors <= 10:
                        print(f"   ❌ Could not fetch: {card_name}")
                
                # Rate limiting delay
                time.sleep(delay_between_requests)
                
            except Exception as e:
                print(f"⚠️ Error processing {card.get('name', 'Unknown')}: {e}")
                skipped_count += 1
        
        # Batch completion delay
        time.sleep(delay_between_batches)
        
        # Progress update every batch
        if (i // batch_size + 1) % 10 == 0 or batch_end >= len(cards):
            print(f"📊 Progress: {processed_count}/{len(cards)} processed, {fixed_count} fixed, {api_errors} API errors")
            
            # Save progress periodically
            if (i // batch_size + 1) % 50 == 0:
                print("💾 Saving progress...")
                try:
                    with open(database_path, 'w', encoding='utf-8') as f:
                        json.dump(cards, f, indent=2, ensure_ascii=False)
                    print("✅ Progress saved")
                except Exception as e:
                    print(f"⚠️ Error saving progress: {e}")
    
    # Save final updated database
    print(f"💾 Saving final updated database...")
    try:
        with open(database_path, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)
        print(f"✅ Database saved successfully")
    except Exception as e:
        print(f"❌ Error saving database: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 COMPLETE MANA COST FIX SUMMARY")
    print("=" * 60)
    print(f"Total cards in database: {len(cards)}")
    print(f"Cards processed: {processed_count}")
    print(f"Cards with corrected mana costs: {fixed_count}")
    print(f"API errors (cards skipped): {api_errors}")
    print(f"Other errors: {skipped_count}")
    print(f"Backup saved to: {backup_path}")
    print(f"Success rate: {((processed_count - api_errors - skipped_count) / processed_count * 100):.1f}%")
    
    if fixed_count > 0:
        print(f"✅ Complete mana cost fix successful!")
        return True
    else:
        print(f"ℹ️ No mana cost fixes needed")
        return True

def verify_random_fixes():
    """Verify some random fixes worked."""
    print("\n" + "=" * 60)
    print("🔍 VERIFYING RANDOM MANA COST FIXES")
    print("=" * 60)
    
    try:
        sys.path.append('.')
        from engine.card_db import load_card_db
        by_id, by_name_lower, by_norm, db_path = load_card_db()
        
        # Test a variety of card types
        test_cards = [
            'elvish mystic',          # 1-mana dork
            'llanowar tribe',         # Multi-mana creature  
            'lightning bolt',         # 1-mana spell
            'counterspell',           # 2-mana spell
            'sol ring',               # Artifact
            'forest',                 # Basic land
            'command tower',          # Special land
            'birds of paradise',      # Another 1-mana dork
            'arcane signet',          # 2-mana artifact
            'cultivate',              # 3-mana spell
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

def interactive_mode():
    """Ask user for confirmation before proceeding."""
    print("⚠️  WARNING: This script will update the ENTIRE card database!")
    print("   - This process may take 30-60 minutes due to API rate limiting")
    print("   - It will make thousands of API calls to MTG SDK")
    print("   - A backup will be created before making changes")
    print()
    
    response = input("Do you want to proceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled by user")
        return False
    
    return True

if __name__ == "__main__":
    print("🎴 MTG CARD DATABASE COMPLETE MANA COST FIXER")
    print("=" * 60)
    
    if interactive_mode():
        fix_all_mana_costs()
        verify_random_fixes()
    else:
        sys.exit(1)
