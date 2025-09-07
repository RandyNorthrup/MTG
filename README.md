# MTG Commander (Prototype)

## Features
- Commander rules baseline (40 life, commander tax/damage)
- Zones & turn structure
- Basic AI (goldfish style)
- Qt UI (Home / Decks / Lobby+Play)
- Embedded text deck editor (.txt)
- Scryfall filter tool

## Shortcuts
SPACE advance / resolve  
A declare attackers (player 0)  
R reload custom_deck.txt  
D deck editor info popup  
S toggle scoreboard  
L toggle phase logging  
H help  
ESC quit  

## Troubleshooting
- Missing images: first load will fetch/cache.
- Card not found: regenerate DB or use --sdk-online.
- Stuck phase: SPACE; check console.
- Mulligan prompt only with 2+ players.

## Performance Tips
- Use --no-log to reduce console noise.
- Keep deck DB trimmed (optional filtered DB).
- Limit image prefetch if on HDD.

## Contributing
Small focused PRs only (engine/UI separation). Avoid committing large generated JSON. Use .txt decks (no legacy JSON).

## Goals
Playable Commander sandbox for prototyping & AI experiments.
A declare attackers (active player 0)  
R reload custom_deck.txt  
D deck editor info popup  
S toggle scoreboard  
L toggle phase logging  
H help  
ESC quit  

## Troubleshooting
- Missing images: first load lazy-downloads (ensure network if using SDK fallback).
- Card not found: regenerate DB or use --sdk-online.
- Stuck phase: press SPACE; check console for exceptions.
- Mulligan prompt only appears with 2+ players.

## Contributing
Small, focused PRs. Omit large generated JSON (see .gitignore). Use text decks (.txt), not legacy JSON.

## Goals
Baseline playable Commander sandbox with extensible engine, simple AI, and deck iteration workflow.

## Performance Tips
Use --no-log for quieter loop. Limit deck size / image prefetch on low-end machines.
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
