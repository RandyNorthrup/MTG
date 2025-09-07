# MTG Commander (Prototype)

## Features
- Commander rules baseline (40 life, commander tax/damage)
- Zones & turn structure
- Basic AI (goldfish style)
- Qt UI (Home / Decks / Play)
- Text deck editor (.txt)
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
- Missing images: first load fetches / caches
- Card not found: regenerate DB or use --sdk-online
- Stuck phase: press SPACE; check console
- Mulligan prompt appears only with 2+ players

## Performance Tips
- Use --no-log for less console noise
- Keep filtered DB small for faster startup
- Limit image prefetch on slow disks

## Contributing
Small focused PRs (engine/UI separation). Avoid committing large generated JSON. Use .txt decks.

## Goals
Playable Commander sandbox for prototyping & simple AI experiments. Baseline multiplayer-ready architecture with extensible engine and deck iteration workflow.

Controls (current):
A declare attackers (active player 0)  
R reload custom_deck.txt  
D deck editor info popup  
S toggle scoreboard  
L toggle phase logging  
H help  
SPACE advance phase / resolve top of stack  
ESC quit  

## Troubleshooting
- Missing images: first load lazy-downloads (ensure network if using SDK fallback).
- Card not found: regenerate DB or use --sdk-online.
- Stuck phase: press SPACE; check console for exceptions.
- Mulligan / roll prompt only appears with 2+ players.

## Performance Tips
Use --no-log for quieter loop. Limit deck size / image prefetch on low-end machines.

## Contributing
Small, focused PRs. Avoid committing large generated JSON blobs. Use text deck lists (.txt).
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
