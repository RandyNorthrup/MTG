# MTG Commander (Phase 1 + Phase 2 Tools)
A playable **Commander-format** prototype rebuilt on **Qt (PySide6)** for a flexible desktop UI (replacing the earlier Pygame shell). Phase 2 still includes full card database, deckbuilder, and legality checks.

## Features
- 1v1 Commander: 40 life, command zone & tax, commander damage
- Zones: Library / Hand / Battlefield / Graveyard / Exile / Command
- Turn engine: Untap → Upkeep → Draw → Main → Combat → Main2 → End
- Basic AI: plays lands, casts spells, attacks
- Qt UI: tabbed interface (Home / Decks / Play), scalable painting, hover highlight, commander cast tracking
- Tools: Scryfall DB filter, text deck import, integrated Qt deckbuilder dialog

## Quick Run
```
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Full Card Database (Scryfall)
1. Download Scryfall default bulk (oracle) JSON to data/raw/.
2. Generate:
   ```
   python tools/scryfall_filter.py data/raw/default-cards.json data/cards/card_db_full.json --verbose
   ```
3. The game auto-preferences card_db_full.json.

## Deck Builder (Qt Dialog)
Inside the app press D or:
```
python main.py --deck You=data/decks/Fynn\ The\ Fangbearer.txt
```
Or run only the deckbuilder dialog:
```
python -m deckbuilder.deckbuilder_ui
```

## Runtime Shortcuts (Main Window Focus)
- Space: Resolve stack / advance phase
- A: Declare attackers (player 0)
- D: Open deckbuilder dialog
- R: Reload player 0 custom_deck.json
- S: Toggle scoreboard overlay
- H: Help popup
- L: Toggle phase logging
- ESC / Ctrl+Q: Quit

## Deck Editing Flow
1. Open deckbuilder (D).
2. Search & add (left click), set commander (right click).
3. Save (writes data/decks/custom_deck.json).
4. Press R in Play tab to reload.

## Project Goals
- Playable Commander format (validation & flow) – implemented (baseline)
- Built-in deck editor (text + GUI) – Qt dialog
- Tabbed UI (Home / Decks / Play) – via QTabWidget
- Minimal AI opponent – unchanged logic
- Multiplayer-ready architecture – engine separation retained

## Troubleshooting
- Missing cards: regenerate DB with tools/scryfall_filter.py
- Validation errors: deckbuilder shows issues (size, singleton, color identity, banlist)
- Rendering glitches: ensure PySide6 version matches requirements.

## Performance Tips
- Use `--no-log` to suppress phase logs.
- Full DB loads once on startup.

## Contributing
See docs/Workflow.txt (rebase + PR guidelines).
