# MTG Commander (Prototype)

## Features
- 1v1 Commander: 40 life, command zone & tax, commander damage
- Zones: Library / Hand / Battlefield / Graveyard / Exile / Command
- Turn engine: UNTAP → UPKEEP → DRAW → MAIN1 → (COMBAT: Begin / Declare Attackers / Declare Blockers / Damage / End) → MAIN2 → END → CLEANUP (auto‑chains through non‑priority steps)
- Basic AI: plays lands, casts simple permanents, attacks
- Qt UI: tabbed (Home / Decks / Play + Lobby), integrated deck editor
- Tools: Scryfall filter, text deck (*.txt) import

## Quick Run
```bash
python -m venv .venv
# activate env
pip install -r requirements.txt
python main.py
```

## Full Card Database (Scryfall)
```bash
python tools/scryfall_filter.py data/raw/default-cards.json data/cards/card_db_full.json --verbose
```

## Deck Builder
Press D in app or edit a text deck (e.g. data/decks/custom_deck.txt) then press R to reload.

## Shortcuts
Space: Resolve / advance phase
A: Declare attackers (player 0)
D: Deck builder
R: Reload custom_deck.txt
S: Toggle scoreboard
L: Toggle phase logging
H: Help
ESC: Quit

## Troubleshooting
- Missing cards: regenerate card_db_full.json
- Phase stuck: ensure game_state.ensure_progress exists (auto steps)  
- Empty library draw: current simplified rules = loss check on next state update

## Contributing
Submit PRs with concise diffs; keep large generated JSON out of repo (.gitignore covers).
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
