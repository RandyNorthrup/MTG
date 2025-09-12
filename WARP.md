# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Core Commands

### Development Startup
```bash
# Windows - Automated setup and run
./RUN_WINDOWS.bat

# Unix/Linux/macOS - Automated setup and run
./run_unix.sh

# Manual setup
python -m venv .venv
pip install -r requirements.txt
python main.py
```

### Common Development Commands
```bash
# Start application with custom deck configurations
python main.py --deck You=data/decks/custom_deck.txt --deck AI=data/decks/draconic_domination.txt:AI

# Generate card database from Scryfall data
python tools/scryfall_filter.py data/raw/default-cards.json data/cards/card_db_full.json --verbose --sort-name

# Clear caches when debugging
python scripts/clear_caches.py

# Test specific game functionality (debug tools)
python tools/game_debug_tests.py

# Update dependencies
pip install --upgrade -r requirements.txt

# Git workflow for development
git fetch origin
git rebase origin/main
```

### Testing and Debug
- Press F9 in the application to open the debug window with game state inspection
- Debug window provides phase/step advancement, mana manipulation, and verbose state dumps
- Use `tools/game_debug_tests.py` for interactive game testing

## Architecture Overview

### Core Architecture Pattern
This is a **modular MTG Commander game engine** with strict separation of concerns:

- **UI Layer** (`ui/`): Qt-based interface components that interact only through the API
- **Engine Layer** (`engine/`): Game logic, rules engine, card database, and state management  
- **API Facade** (`ui/game_app_api.py`): Central coordinator between UI and engine
- **Data Layer** (`data/`): Card databases, deck files, and game assets

### Key Architectural Components

#### GameController (`engine/game_controller.py`)
- Central orchestrator for all game logic
- Manages turn structure, phase transitions, and player actions
- Delegates to specialized engines (stack, rules, combat)
- Handles AI player integration

#### GameState (`engine/game_state.py`) 
- Immutable game state representation
- Player states, battlefield, stack, and phase tracking
- Turn sequence: UNTAP → UPKEEP → DRAW → MAIN1 → COMBAT → MAIN2 → END → CLEANUP

#### Rules Engine (`engine/rules_engine.py`)
- Parses card oracle text into structured abilities
- Handles triggered abilities, static effects, and activated abilities
- ETB triggers, death triggers, combat triggers, buff effects

#### Stack Engine (`engine/stack.py`)
- Strict Magic stack mechanics implementation
- Priority passing, spell resolution, triggered ability queuing

#### Phase Management (`engine/phase_hooks.py`)
- Canonical phase/step state management
- Phase sequence validation and advancement
- UI synchronization hooks

### UI Architecture

#### Modular Tab System
- **Home Tab**: Game launcher and quick actions
- **Decks Tab**: Deck builder with Commander format validation
- **Play Tab**: Lobby system and game interface
- Each tab is completely decoupled and interacts only via GameAppAPI

#### Card Database System
- Supports both JSON (`card_db.json`) and SQLite (`cards.db`) backends
- Automatic backend selection via `MTG_SQL` environment variable
- Card image caching with prefetching (`image_cache.py`)

## Development Patterns

### Adding New Game Features
1. Implement logic in appropriate `engine/` module
2. Add API methods to `GameAppAPI` if UI interaction needed
3. Create UI components in `ui/` that call API methods only
4. Test using debug window (F9) or `tools/game_debug_tests.py`

### Card Database Updates
1. Download Scryfall bulk data to `data/raw/`
2. Run `scryfall_filter.py` to generate filtered database
3. Enable SQL backend with `MTG_SQL=1` environment variable for performance
4. Use `card_fetch.py` for online card lookup during development

### Deck Management
- Deck files in `data/decks/*.txt` format
- Commander specified as last card or with "Commander:" prefix
- Press R in application to reload deck changes
- Commander format validation via `rules/commander_validator.py`

### AI Player Development
- Basic AI in `ai/basic_ai.py` with simple heuristics
- Enhanced AI controllers in `ai_players/ai_player_simple.py`
- AI automatically added when single-player game detected
- AI decision making integrated into phase/priority system

## Key Integration Points

### Phase Hooks System
All phase transitions must use `engine/phase_hooks.py` functions:
- `advance_phase()` - Move to next phase
- `advance_step()` - Move to next step within phase
- `set_phase()` - Jump to specific phase
- Never manipulate phase state directly

### GameAppAPI Usage
All UI components must interact through `GameAppAPI` methods:
- Never import engine modules directly from UI
- Use API for all game state queries and modifications
- API handles proper event delegation and state synchronization

### Stack Integration  
All spell casting and ability activation must go through `StackEngine`:
- Automatic priority handling
- Proper trigger timing
- Stack item resolution order

## Data Management

### Environment Variables
- `MTG_SQL=1` - Enable SQLite database backend for performance
- `MTG_SQL_BOOT=1` - Bootstrap SQLite from JSON on startup

### File Structure
- `data/cards/` - Card database files (JSON/SQLite)
- `data/decks/` - Deck files in text format
- `data/images/` - Cached card images
- `image_cache/` - Temporary image cache directory

### Cache Management
Use `scripts/clear_caches.py` to reset all caches when experiencing issues with:
- Card images not loading
- Database inconsistencies  
- Python bytecode conflicts

## Debugging and Development Tools

### Debug Window (F9)
- Real-time game state inspection
- Phase/step manual advancement
- Mana pool manipulation
- Player life modification
- Stack state viewing

### Game Debug Tests
Run `python tools/game_debug_tests.py` for interactive debugging with:
- Window size tracking
- Event filter monitoring
- Phase transition testing
- Verbose state dumps
