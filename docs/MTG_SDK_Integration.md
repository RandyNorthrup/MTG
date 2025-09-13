# MTG SDK Integration

## Overview

The MTG Commander game now includes comprehensive integration with the official Magic: The Gathering API via the `mtgsdk` Python package. This enhancement provides accurate mana costs, card types, and properties directly from Wizards of the Coast's official card database.

## Features

### ✅ **Accurate Mana Costs**
- Proper mana cost strings like `{2}{U}{U}` for Counterspell
- Correct Converted Mana Cost (CMC) calculations
- Support for complex costs including hybrid, phyrexian, and X costs

### ✅ **Enhanced Card Properties**
- Official card text and abilities
- Correct power/toughness values
- Proper color identity for Commander format
- Complete type lines including subtypes

### ✅ **Smart Caching**
- API responses are cached to avoid repeated network calls
- Faster subsequent deck loading
- Offline play support after initial card fetching

### ✅ **Fallback Support**
- Works with existing local card database
- Graceful degradation if API is unavailable
- Enhanced data when online, functional offline

## Usage

### Enable SDK Integration
Run the game with the `--sdk-online` flag:
```bash
python main.py --sdk-online
```

### Command Line Examples
```bash
# Enable MTG SDK for enhanced card data
python main.py --sdk-online

# Use custom deck with SDK enhancement
python main.py --deck "My Deck=./my_deck.txt" --sdk-online

# Multiple players with SDK
python main.py --deck "Player1=./deck1.txt" --deck "Player2=./deck2.txt:AI" --sdk-online
```

### Programmatic Usage
```python
from engine.card_fetch import set_sdk_online, load_deck

# Enable SDK integration
set_sdk_online(True)

# Load a deck with enhanced card data
cards, commander = load_deck("./my_deck.txt", owner_id=0)

# Cards now have proper mana_cost_str and enhanced properties
for card in cards[:5]:
    print(f"{card.name}: {card.mana_cost_str} (CMC {card.mana_cost})")
```

## Technical Details

### Card Data Enhancement
When SDK integration is enabled, cards are enhanced with:
- **mana_cost_str**: Official mana cost notation (e.g., `{2}{U}{U}`)
- **mana_cost**: Calculated CMC value
- **text**: Official card text and abilities
- **power/toughness**: Correct creature stats
- **color_identity**: Proper Commander color identity
- **types**: Complete type line including supertypes and subtypes

### Example Enhancements

| Card | Local DB | With MTG SDK |
|------|----------|--------------|
| Lightning Bolt | mana_cost: 1 | mana_cost_str: `{R}`, mana_cost: 1 |
| Counterspell | mana_cost: 2 | mana_cost_str: `{U}{U}`, mana_cost: 2 |
| Sol Ring | mana_cost: 1 | mana_cost_str: `{1}`, mana_cost: 1 |
| Forest | mana_cost: 0 | mana_cost_str: "", types: ["Basic", "Land"] |

### Mana Cost Parsing
The system now properly parses complex mana costs:
```python
from engine.card_engine import parse_mana_cost_str

# Parse Cryptic Command's cost
cost = parse_mana_cost_str("{1}{U}{U}{U}")
# Returns: {'1': 1, 'U': 3}

# Parse hybrid costs
cost = parse_mana_cost_str("{2/U}{2/U}")
# Returns: {'2/U': 2}
```

### Cache Management
```python
from engine.card_fetch import get_api_cache_stats, clear_api_cache

# View cache statistics
stats = get_api_cache_stats()
print(f"Cache: {stats['hits']} hits, {stats['misses']} misses")

# Clear cache if needed
clear_api_cache()
```

## Benefits for Gameplay

### 🎯 **Accurate Casting**
- Proper mana cost validation
- Correct mana pool interactions
- Accurate spell timing and restrictions

### 🎯 **Commander Format Support**
- Proper color identity validation
- Correct commander casting cost increases
- Accurate color restriction enforcement

### 🎯 **Enhanced AI**
- AI can make better decisions with accurate costs
- Proper mana curve evaluation
- Correct threat assessment based on real CMC

## Installation

The MTG SDK is automatically installed when you run:
```bash
pip install mtgsdk
```

Or if you see the warning message, install manually:
```bash
pip install mtgsdk
```

## Performance Considerations

- **First Load**: Slower due to API calls (one-time per card)
- **Subsequent Loads**: Fast due to caching
- **Network Required**: Only for initial enhancement
- **Offline Play**: Fully functional after initial card fetching

## Troubleshooting

### Common Issues

**"MTG SDK not available"**
```bash
pip install mtgsdk
```

**API Rate Limiting**
The system includes built-in caching and reasonable request spacing.

**Network Issues**
The game falls back to local database if API is unavailable.

**Basic Land Issues**
The system has special handling for basic lands to ensure correct data.

## Advanced Features

### Custom Card Enhancement
```python
from engine.card_fetch import enhance_existing_card

# Enhance a card object with API data
enhanced_card = enhance_existing_card(my_card)
```

### Batch Processing
The system automatically handles batch processing during deck loading with progress indicators and caching.

## Future Enhancements

- [ ] Set-specific card preferences
- [ ] Alternative cost support (Flashback, Kicker, etc.)
- [ ] Advanced filtering and search
- [ ] Integration with card images
- [ ] Support for non-English cards

---

*This integration uses the official Magic: The Gathering API provided by magicthegathering.io and respects all rate limits and usage guidelines.*
