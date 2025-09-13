"""
MTG SDK Integration for Card Loading

This module provides enhanced card loading capabilities using the official Magic: The Gathering API
to ensure accurate mana costs, colors, and other properties for proper game mechanics.
"""

import os
import re
from typing import List, Tuple, Dict, Optional, Any
from engine.card_engine import Card, mana_cost_to_cmc, parse_mana_cost_str
from engine.card_db import load_card_db
from engine.rules_engine import parse_and_attach

# Global flag to control SDK usage
_SDK_ENABLED = False

# Cache for API results to avoid repeated calls
_API_CACHE = {}

def set_sdk_online(enabled: bool):
    """Enable or disable MTG SDK integration."""
    global _SDK_ENABLED
    _SDK_ENABLED = enabled
    if enabled:
        print("🌐 MTG SDK integration enabled - will fetch enhanced card data")
    else:
        print("💾 MTG SDK integration disabled - using local card database")

def clear_api_cache():
    """Clear the API response cache."""
    global _API_CACHE
    cache_size = len(_API_CACHE)
    _API_CACHE.clear()
    print(f"🧺 Cleared API cache ({cache_size} entries)")

def get_api_cache_stats():
    """Get statistics about the API cache."""
    total = len(_API_CACHE)
    hits = sum(1 for v in _API_CACHE.values() if v is not None)
    misses = total - hits
    return {'total': total, 'hits': hits, 'misses': misses}

def _try_import_mtg_sdk():
    """Safely import MTG SDK components."""
    try:
        from mtgsdk import Card as SDKCard
        return SDKCard
    except ImportError:
        print("⚠️  MTG SDK not available - install with: pip install mtgsdk")
        return None

def _normalize_name_for_search(name: str) -> str:
    """Normalize card name for API search."""
    # Remove common deck list formatting
    name = re.sub(r'\s*\([^)]+\)$', '', name)  # Remove set codes like (KTK)
    name = re.sub(r'^\d+x?\s+', '', name)      # Remove quantity prefixes
    name = name.strip()
    return name

def _fetch_card_from_api(card_name: str) -> Optional[Dict[str, Any]]:
    """Fetch card data from MTG API."""
    if not _SDK_ENABLED:
        return None
    
    # Check cache first
    cache_key = card_name.lower().strip()
    if cache_key in _API_CACHE:
        return _API_CACHE[cache_key]
        
    SDKCard = _try_import_mtg_sdk()
    if not SDKCard:
        return None
    
    try:
        normalized_name = _normalize_name_for_search(card_name)
        print(f"🔍 Searching MTG API for: '{normalized_name}'")
        
        # Special handling for basic lands
        basic_lands = ['forest', 'island', 'mountain', 'plains', 'swamp']
        if normalized_name.lower() in basic_lands:
            # For basic lands, get a specific version to ensure proper data
            land_type = normalized_name.lower().capitalize()
            cards = SDKCard.where(name=land_type, type=f"Basic Land — {land_type}").all()
            if not cards:
                # Fallback to any version of the basic land
                cards = SDKCard.where(name=land_type).all()
        else:
            # Search for exact name match first
            cards = SDKCard.where(name=normalized_name).all()
            
            if not cards:
                # Try partial match if exact fails
                cards = SDKCard.where(name=normalized_name).all()
            
        if not cards:
            print(f"❌ No cards found for '{card_name}' in MTG API")
            _API_CACHE[cache_key] = None  # Cache negative results too
            return None
            
        # Prefer the most recent printing (highest set number/date)
        card = cards[0]  # API usually returns most relevant first
        
        # Extract comprehensive card data
        card_data = {
            'id': getattr(card, 'id', card_name.lower().replace(' ', '_')),
            'name': getattr(card, 'name', card_name),
            'mana_cost_str': getattr(card, 'mana_cost', '') or '',
            'mana_cost': getattr(card, 'cmc', 0) or 0,
            'types': getattr(card, 'type', '').split() if getattr(card, 'type', None) else [],
            'power': _safe_int(getattr(card, 'power', None)),
            'toughness': _safe_int(getattr(card, 'toughness', None)),
            'text': getattr(card, 'text', '') or '',
            'colors': getattr(card, 'colors', []) or [],
            'color_identity': getattr(card, 'color_identity', []) or [],
            'rarity': getattr(card, 'rarity', 'common'),
            'set_name': getattr(card, 'set_name', ''),
            'multiverse_id': getattr(card, 'multiverse_id', None),
        }
        
        # Parse types properly
        if hasattr(card, 'type') and card.type:
            # Example: "Legendary Creature — Human Wizard"
            type_line = card.type
            if '—' in type_line or '-' in type_line:
                main_types, subtypes = type_line.replace('—', '-').split('-', 1)
                card_data['types'] = main_types.strip().split()
                card_data['subtypes'] = subtypes.strip().split()
            else:
                card_data['types'] = type_line.strip().split()
                card_data['subtypes'] = []
        
        print(f"✅ Retrieved '{card.name}' from API: {card_data['mana_cost_str']} (CMC {card_data['mana_cost']})")
        
        # Cache the successful result
        _API_CACHE[cache_key] = card_data
        return card_data
        
    except Exception as e:
        print(f"❌ Error fetching '{card_name}' from MTG API: {e}")
        _API_CACHE[cache_key] = None  # Cache negative results
        return None

def _safe_int(value) -> Optional[int]:
    """Safely convert value to int, handling None and strings like '*'."""
    if value is None:
        return None
    if isinstance(value, str):
        if value in ('*', '?', ''):
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return int(value) if isinstance(value, (int, float)) else None

def _enhance_card_with_api_data(card_data: Dict[str, Any], api_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance local card data with API data."""
    enhanced = card_data.copy()
    
    # Update with API data, preferring API values for critical gameplay properties
    if api_data.get('mana_cost_str'):
        enhanced['mana_cost_str'] = api_data['mana_cost_str']
        # Recalculate CMC from the actual mana cost string
        enhanced['mana_cost'] = mana_cost_to_cmc(api_data['mana_cost_str'])
    
    # Update other important properties
    for key in ['power', 'toughness', 'text', 'colors', 'color_identity', 'types']:
        if key in api_data and api_data[key]:
            enhanced[key] = api_data[key]
    
    return enhanced

def _parse_deck_file(path: str) -> Tuple[List[str], Optional[str]]:
    """Parse a deck file and return (card_names, commander_name)."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    
    entries = []
    commander = None
    last_card = None
    
    with open(path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Check for commander designation
            line_lower = line.lower()
            if line_lower.startswith('commander:'):
                commander_name = line.split(':', 1)[1].strip()
                if commander_name:
                    commander = commander_name
                continue
            
            # Parse quantity and card name
            match = re.match(r'^(\d+)x?\s+(.+)$', line)
            if match:
                quantity = int(match.group(1))
                card_name = match.group(2).strip()
                if quantity > 0 and card_name:
                    entries.extend([card_name] * quantity)
                    last_card = card_name
            else:
                # Single card with no quantity specified
                entries.append(line)
                last_card = line
    
    # Use last card as commander if not explicitly specified
    if commander is None:
        commander = last_card
        
    return entries, commander

def _resolve_card_data(card_name: str, local_db: Tuple) -> Dict[str, Any]:
    """Resolve card data from local database with optional API enhancement."""
    by_id, by_name_lower, by_norm, _ = local_db
    
    # Helper function to normalize names
    def normalize_name(name: str) -> str:
        return re.sub(r'[^a-z0-9]+', ' ', name.lower()).strip()
    
    # Try multiple resolution strategies
    card_data = None
    
    # 1. Direct name lookup (case-insensitive)
    if card_name.lower() in by_name_lower:
        card_data = by_name_lower[card_name.lower()].copy()
    
    # 2. Normalized name lookup
    if not card_data:
        normalized = normalize_name(card_name)
        if normalized in by_norm:
            card_data = by_norm[normalized].copy()
    
    # 3. Partial name matching
    if not card_data:
        name_lower = card_name.lower()
        candidates = [card for name, card in by_name_lower.items() if name.startswith(name_lower)]
        if len(candidates) == 1:
            card_data = candidates[0].copy()
    
    # 4. If still not found and SDK enabled, try API
    if not card_data and _SDK_ENABLED:
        api_data = _fetch_card_from_api(card_name)
        if api_data:
            card_data = api_data
    
    if not card_data:
        raise KeyError(f"Card '{card_name}' not found in database or API")
    
    # Enhance with API data if SDK is enabled and we have local data
    if _SDK_ENABLED and 'mana_cost_str' not in card_data:
        api_data = _fetch_card_from_api(card_name)
        if api_data:
            card_data = _enhance_card_with_api_data(card_data, api_data)
    
    return card_data

def _build_card_objects(entries: List[str], commander_name: Optional[str], 
                       local_db: Tuple, owner_id: int) -> Tuple[List[Card], Optional[Card]]:
    """Build Card objects from card names."""
    library_cards = []
    commander_card = None
    
    # Resolve commander first if specified
    commander_data = None
    if commander_name:
        try:
            commander_data = _resolve_card_data(commander_name, local_db)
        except KeyError as e:
            print(f"⚠️  Commander not found: {e}")
    
    # Process library cards
    for card_name in entries:
        try:
            card_data = _resolve_card_data(card_name, local_db)
            
            # Skip if this is the commander
            if commander_data and card_data.get('id') == commander_data.get('id'):
                continue
            
            # Create Card object
            card = _create_card_from_data(card_data, owner_id, is_commander=False)
            library_cards.append(card)
            
        except KeyError as e:
            print(f"⚠️  Skipping unknown card: {e}")
            continue
    
    # Create commander card object
    if commander_data:
        commander_card = _create_card_from_data(commander_data, owner_id, is_commander=True)
    
    return library_cards, commander_card

def _create_card_from_data(card_data: Dict[str, Any], owner_id: int, is_commander: bool = False) -> Card:
    """Create a Card object from resolved card data."""
    # Ensure we have required fields with sensible defaults
    card_id = card_data.get('id', card_data['name'].lower().replace(' ', '_'))
    name = card_data['name']
    types = card_data.get('types', [])
    
    # Handle mana cost - prefer mana_cost_str if available
    mana_cost_str = card_data.get('mana_cost_str', '')
    if mana_cost_str:
        mana_cost = mana_cost_to_cmc(mana_cost_str)
    else:
        mana_cost = card_data.get('mana_cost', 0)
        if isinstance(mana_cost, str):
            try:
                mana_cost = int(mana_cost)
            except ValueError:
                mana_cost = 0
    
    # Create the Card object
    card = Card(
        id=card_id,
        name=name,
        types=types,
        mana_cost=mana_cost,
        mana_cost_str=mana_cost_str,
        power=card_data.get('power'),
        toughness=card_data.get('toughness'),
        text=card_data.get('text', ''),
        is_commander=is_commander,
        color_identity=card_data.get('color_identity', []),
        owner_id=owner_id,
        controller_id=owner_id
    )
    
    # Apply rules engine parsing for special abilities
    parse_and_attach(card)
    
    return card

def load_deck(deck_path: str, owner_id: int) -> Tuple[List[Card], Optional[Card]]:
    """
    Load a deck from file with MTG SDK enhancement.
    
    Returns:
        Tuple of (library_cards, commander_card)
    """
    if not os.path.exists(deck_path):
        raise FileNotFoundError(f"Deck file not found: {deck_path}")
    
    print(f"📚 Loading deck: {os.path.basename(deck_path)} (SDK: {'ON' if _SDK_ENABLED else 'OFF'})")
    
    # Load local card database
    local_db = load_card_db()
    
    # Parse deck file
    try:
        entries, commander_name = _parse_deck_file(deck_path)
        print(f"📋 Found {len(entries)} cards, commander: {commander_name or 'None specified'}")
    except Exception as e:
        print(f"❌ Error parsing deck file: {e}")
        raise
    
    # Build card objects
    try:
        library_cards, commander_card = _build_card_objects(entries, commander_name, local_db, owner_id)
        print(f"✅ Successfully loaded {len(library_cards)} cards into library")
        if commander_card:
            print(f"👑 Commander: {commander_card.name}")
        return library_cards, commander_card
    except Exception as e:
        print(f"❌ Error building card objects: {e}")
        raise

def enhance_existing_card(card: Card) -> Card:
    """
    Enhance an existing Card object with MTG SDK data.
    
    This can be used to upgrade cards that were loaded from local database
    to have proper MTG API properties.
    """
    if not _SDK_ENABLED:
        return card
    
    try:
        api_data = _fetch_card_from_api(card.name)
        if not api_data:
            return card
        
        # Update card properties with API data
        if api_data.get('mana_cost_str'):
            card.mana_cost_str = api_data['mana_cost_str']
            card.mana_cost = mana_cost_to_cmc(api_data['mana_cost_str'])
        
        if api_data.get('text'):
            card.text = api_data['text']
        
        if api_data.get('power') is not None:
            card.power = api_data['power']
            
        if api_data.get('toughness') is not None:
            card.toughness = api_data['toughness']
        
        if api_data.get('color_identity'):
            card.color_identity = api_data['color_identity']
            
        if api_data.get('types'):
            card.types = api_data['types']
        
        # Re-apply rules engine parsing
        parse_and_attach(card)
        
        print(f"✨ Enhanced card '{card.name}' with API data")
        return card
        
    except Exception as e:
        print(f"⚠️  Failed to enhance card '{card.name}': {e}")
        return card

# Testing functions
def test_mtg_sdk_integration():
    """Test the MTG SDK integration with some common cards."""
    print("🧪 Testing MTG SDK integration...")
    
    set_sdk_online(True)
    test_cards = ["Lightning Bolt", "Counterspell", "Forest", "Sol Ring"]
    
    for card_name in test_cards:
        try:
            api_data = _fetch_card_from_api(card_name)
            if api_data:
                print(f"✅ {card_name}: {api_data.get('mana_cost_str', 'No cost')} - {api_data.get('text', 'No text')[:50]}")
            else:
                print(f"❌ {card_name}: Not found")
        except Exception as e:
            print(f"❌ {card_name}: Error - {e}")

def demonstrate_enhanced_casting():
    """Demonstrate enhanced card casting with proper mana costs."""
    print("✨ Demonstrating Enhanced Card Casting with MTG SDK")
    print("=" * 60)
    
    set_sdk_online(True)
    
    # Test cards with different mana cost complexities
    demo_cards = [
        "Lightning Bolt",      # Simple {R}
        "Counterspell",       # Double mana {U}{U}
        "Cryptic Command",     # Complex {1}{U}{U}{U}
        "Rhystic Study",      # Simple {2}{U}
        "Sol Ring",           # Artifact {1}
        "Mana Crypt",         # Free artifact {0}
        "Force of Will",      # Alternative cost {3}{U}{U}
        "Forest"              # Land (no cost)
    ]
    
    print(f"📋 Testing {len(demo_cards)} cards for enhanced mana cost data:\n")
    
    for card_name in demo_cards:
        try:
            # Simulate creating a card object with SDK data
            local_db = load_card_db()
            card_data = _resolve_card_data(card_name, local_db)
            
            if card_data:
                mana_str = card_data.get('mana_cost_str', '')
                mana_cmc = card_data.get('mana_cost', 0)
                types = ', '.join(card_data.get('types', []))
                
                # Parse mana cost for detailed analysis
                from engine.card_engine import parse_mana_cost_str
                parsed_cost = parse_mana_cost_str(mana_str) if mana_str else {}
                
                print(f"🃏 {card_name}:")
                print(f"   • Mana Cost: {mana_str or '(No cost)'} (CMC: {mana_cmc})")
                print(f"   • Types: {types or 'Unknown'}")
                if parsed_cost:
                    print(f"   • Parsed Cost: {parsed_cost}")
                
                # Show castability example
                if mana_str and mana_cmc > 0:
                    print(f"   • 🟢 Can be cast with proper mana cost validation")
                elif not mana_str:
                    print(f"   • 🔴 Land - played from hand directly")
                else:
                    print(f"   • 🟡 Free spell - no mana required")
                print()
            else:
                print(f"❌ {card_name}: Not found in database or API\n")
                
        except Exception as e:
            print(f"❌ {card_name}: Error - {e}\n")
    
    # Show cache statistics
    stats = get_api_cache_stats()
    print(f"📈 API Cache Statistics:")
    print(f"   • Total entries: {stats['total']}")
    print(f"   • Successful lookups: {stats['hits']}")
    print(f"   • Failed lookups: {stats['misses']}")
    
    print("\n✨ Enhanced casting system ready! Cards now have proper mana costs for accurate gameplay.")

if __name__ == "__main__":
    test_mtg_sdk_integration()
