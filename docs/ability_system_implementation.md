# MTG Ability System Implementation

## Overview
This document describes the comprehensive ability triggering system implemented for the MTG game engine, providing support for static, triggered, and activated abilities according to Magic: The Gathering Comprehensive Rules.

## Core Components

### 1. AbilityEngine (`engine/ability_engine.py`)
The central engine that manages all ability types and their interactions.

**Key Features:**
- **Ability Parsing**: Automatically parses card text to identify and classify abilities
- **Event System**: Robust event detection and emission for ability triggers
- **Cost Management**: Handles mana costs, tap costs, and other activation requirements
- **Effect Resolution**: Processes ability effects with built-in handlers

**Supported Ability Types:**
- **Static Abilities**: Continuous effects while on battlefield
- **Triggered Abilities**: Event-based abilities (ETB, attack, upkeep, death, etc.)
- **Activated Abilities**: Player-activated abilities with costs
- **Keyword Abilities**: Enhanced keyword detection and processing

### 2. Trigger Conditions
Comprehensive set of trigger conditions based on MTG rules:

```python
class TriggerCondition(Enum):
    ENTERS_BATTLEFIELD = "etb"
    LEAVES_BATTLEFIELD = "ltb"
    ATTACKS = "attacks"
    BLOCKS = "blocks"
    DEALS_COMBAT_DAMAGE = "deals_combat_damage"
    DEALS_DAMAGE = "deals_damage" 
    TAKES_DAMAGE = "takes_damage"
    DIES = "dies"
    BEGINNING_OF_UPKEEP = "beginning_of_upkeep"
    END_OF_TURN = "end_of_turn"
    CAST_SPELL = "cast_spell"
    # ... and more
```

### 3. Integration Points

#### Game Controller Integration
- AbilityEngine initialized with game state
- Automatic card registration during game setup
- Trigger processing integrated into phase transitions
- API methods for ability activation

#### Game State Integration
- ETB events emitted when permanents enter battlefield
- Attack events emitted during combat
- Death events emitted when creatures die
- Upkeep events emitted at beginning of upkeep

#### Combat Integration
- Attack triggers fire when creatures attack
- Combat damage triggers support
- Death triggers from combat damage

## Implementation Highlights

### Ability Parsing
The system can automatically parse common ability patterns:

```python
# ETB Triggers
"When Creature enters the battlefield, draw a card."
"When ~ enters the battlefield, you gain 2 life."

# Attack Triggers  
"Whenever Creature attacks, it gets +1/+1 until end of turn."

# Activated Abilities
"{2}, {T}: Deal 1 damage to target creature."
"{T}: Add {G}."

# Upkeep Triggers
"At the beginning of your upkeep, draw a card."
```

### Event-Driven Architecture
Uses a listener pattern for efficient trigger detection:

```python
# Emit events from game actions
emit_game_event(TriggerCondition.ENTERS_BATTLEFIELD, 
               affected=card, controller=player_id)

# Listeners automatically detect relevant triggers
# and queue abilities for resolution
```

### Cost Management
Comprehensive cost checking and payment:

```python
# Check if ability can be activated
can_activate = ability_engine.can_activate_ability(player_id, card, ability_index)

# Pay costs and activate
success = ability_engine.activate_ability(player_id, card, ability_index, targets)
```

## Game Controller API

### New Methods Added
- `get_activated_abilities(card)` - Get all activated abilities for a card
- `can_activate_ability(player_id, card, ability_index)` - Check activation legality
- `activate_ability(player_id, card, ability_index, targets)` - Activate an ability
- `process_triggers()` - Process all pending triggered abilities

### Enhanced Card Registration  
All cards are automatically registered with the ability engine during game setup, parsing their text for abilities and setting up appropriate listeners.

## Effect Handlers

### Built-in Effect Processing
- **Card Draw**: Automatically handles "draw a card" effects
- **Life Gain**: Processes "gain N life" effects  
- **Mana Production**: Handles mana-producing abilities
- **Damage**: Framework for damage-dealing abilities

### Extensible Handler System
Custom effect handlers can be registered for specific ability types:

```python
def custom_handler(instance: AbilityInstance, event: TriggerEvent):
    # Custom effect processing
    pass

ability_engine.ability_handlers["custom_trigger"] = custom_handler
```

## Testing Coverage

Comprehensive test suite (`tests/test_ability_engine.py`) covering:
- **Ability Parsing**: ETB, attack, activated, and mana abilities
- **Triggered Abilities**: Event detection and resolution
- **Activated Abilities**: Cost checking and payment
- **Integration**: Multi-ability cards and battlefield requirements
- **Edge Cases**: Cards not on battlefield, insufficient costs, etc.

## MTG Rules Compliance

The system implements key aspects of MTG Comprehensive Rules:
- **CR 112**: Spells (including abilities on the stack)
- **CR 113**: Abilities (static, triggered, activated)
- **CR 608**: Resolving spells and abilities
- **CR 603**: Handling triggered abilities

## Future Enhancements

The architecture supports expansion for:
- **Modal Abilities**: Choose one or more effects
- **Replacement Effects**: Modify or replace events
- **Static Abilities**: Continuous effect management
- **Complex Timing**: Priority, stack interaction, and response windows
- **Targeting**: Full target validation and selection
- **X Costs**: Variable cost handling

## Usage Example

```python
# Card with ETB trigger
card = Card(text="When Creature enters the battlefield, draw a card.")

# Register with ability engine
ability_engine.register_card(card)

# Play card - ETB trigger fires automatically
game_state.cast_spell(player_id, card)  # Emits ETB event
ability_engine.process_triggered_abilities()  # Processes trigger

# Card with activated ability  
mana_creature = Card(text="{T}: Add {G}.")
ability_engine.register_card(mana_creature)

# Check if can activate
can_tap = ability_engine.can_activate_ability(player_id, mana_creature, 0)

# Activate ability
if can_tap:
    ability_engine.activate_ability(player_id, mana_creature, 0)
```

## Conclusion

This ability system provides a solid foundation for MTG-compliant card interactions, with automatic parsing, event-driven triggers, and extensible effect processing. The architecture supports the complexity of MTG while maintaining clean separation of concerns and testability.

The system successfully handles the most common ability types and provides hooks for future expansion to cover the full breadth of MTG's ability system.
