# Quick Start

## Run
```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```

## Turn Structure
UNTAP → UPKEEP → DRAW → MAIN1 → COMBAT (Begin / Declare Attackers / Declare Blockers / Damage / End) → MAIN2 → END → CLEANUP

## Generate DB
```bash
python tools/scryfall_filter.py data/raw/default-cards.json data/cards/card_db_full.json --verbose --sort-name
```

## Deck Editing
Use data/decks/*.txt (Commander: line optional; last card defaults as commander). Save, then press R in app.

## Args example
```bash
python main.py --deck You=data/decks/custom_deck.txt --deck AI=data/decks/draconic_domination.txt:AI
```

## Update deps
```bash
pip install --upgrade -r requirements.txt
```

## Git sync
```bash
git fetch origin
git rebase origin/main
```
```
