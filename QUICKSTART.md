# Quick Start

## Run
```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```

## Turn Structure (Simplified Engine)
UNTAP → UPKEEP → DRAW (auto) → MAIN1 → COMBAT (Begin / Declare Attackers / Declare Blockers / Damage / End) → MAIN2 → END → CLEANUP (auto)

## Generate Full DB
```bash
python tools/scryfall_filter.py data/raw/default-cards.json data/cards/card_db_full.json --verbose
```

## Deck Builder
Press D or edit data/decks/custom_deck.txt then press R in Play tab.

## Example Args
```bash
python main.py --deck You="data/decks/custom_deck.txt" --deck AI=data/decks/draconic_domination.txt:AI
```

## Update Deps
```bash
pip install --upgrade -r requirements.txt
```

## Git Sync
```bash
git fetch origin
git rebase origin/main
```
```
