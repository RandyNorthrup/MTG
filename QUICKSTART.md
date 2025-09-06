# Quick Start

## Run (Qt UI)
```bash
python -m venv .venv
# Activate env...
pip install -r requirements.txt
python main.py
```

## Optional: Generate Full Scryfall DB
```bash
python tools/scryfall_filter.py data/raw/default-cards.json data/cards/card_db_full.json --verbose
```

## Deck Builder (Dialog)
Press D inside the app or:
```bash
python -m deckbuilder.deckbuilder_ui
```

## Useful Args
```
python main.py --deck You="data/decks/Fynn The Fangbearer.txt" --deck AI=data/decks/draconic_domination.json:AI --no-log
```

## Update Dependencies
```
pip install --upgrade -r requirements.txt
```

## Sync Main
```
git fetch origin
git rebase origin/main
```
