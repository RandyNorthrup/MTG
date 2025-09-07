# MTG Commander (Qt)

A modular, extensible Magic: The Gathering Commander game engine and GUI, written in Python with PySide6 (Qt).

## Features

- Modular UI: Home, Decks, Lobby/Play tabs (no gameplay logic in MainWindow)
- Card database and fetch logic fully separated (`engine/card_db.py`, `engine/card_fetch.py`)
- Local multiplayer and AI support
- Deck builder/editor, pending match queue, and debug tools
- Comprehensive rules and validation (Commander, singleton, color identity, etc.)

## Requirements

- Python 3.8+
- PySide6
- (Optional) [mtgsdk](https://github.com/MagicTheGathering/mtgsdk-python) for online card lookup

## Setup

1. Clone the repo:
   ```
   git clone https://github.com/youruser/MTG.git
   cd MTG
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. (Optional) For online card lookup:
   ```
   pip install mtgsdk
   ```

4. Ensure you have the `data/` directory with:
   - `data/cards/card_db.json`
   - `data/decks/` (with at least one deck file)
   - `data/images/` (for card images and backgrounds)

## Running

```bash
python main.py
```

## Project Structure

- `main.py` — Entry point, minimal UI shell, delegates all logic to API and modules
- `engine/card_db.py` — Card database loading and lookup
- `engine/card_fetch.py` — Card fetching, deck parsing, SDK integration, image prewarm
- `engine/game_controller.py` — Game logic, turn/phase/stack management
- `ui/game_app_api.py` — Facade for all gameplay, deck, and lobby operations
- `ui/home_tab.py`, `ui/decks_tab.py`, `ui/play_tab.py` — Modular UI tabs
- `data/` — Card data, decks, images

## Development

- All gameplay, deck, and lobby logic must be in modules or the API, not in MainWindow or tabs.
- Use `.gitignore` to avoid committing cache, user, and build files.

## License

MIT License
## Performance Tips
- Use `--no-log` to suppress phase logs.
- Full DB loads once on startup.

## Contributing
See docs/Workflow.txt (rebase + PR guidelines).
