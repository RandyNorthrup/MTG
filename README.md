# MTG Commander (Qt)

A modular, extensible Magic: The Gathering Commander game engine and GUI, built with Python and Qt (PySide6).

## Features

- Modular UI: Home, Decks, Lobby/Play, and Settings tabs, each fully decoupled.
- Deck building and validation (Commander rules enforced).
- Multiplayer support (up to 4 players, AI or human).
- Modern rules engine and card database.
- Card image caching and prefetching.
- Debug window for in-depth game state inspection.
- Clean separation of UI, game logic, and data layers.

## Requirements

- Python 3.8+
- PySide6
- (Optional) [mtgsdk](https://github.com/MagicTheGathering/mtgsdk-python) for online card lookup

## Quick Start

1. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

2. Run the application:
    ```
    python main.py
    ```

3. Place your deck files in `data/decks/` (see sample format in that folder).

## Project Structure

- `main.py` — Entry point, main window shell, tab setup.
- `engine/` — Game logic, card database, card fetching, rules engine.
- `ui/` — All UI tabs, managers, and the GameAppAPI facade.
- `image_cache.py` — Card image caching and prefetching.
- `data/` — Card database, decks, images, and rules files.

## Modularity

- All gameplay, deck, and lobby logic is handled by `GameAppAPI` and engine modules.
- UI tabs are fully decoupled and interact only via the API.
- Card database and card fetching are in `engine/card_db.py` and `engine/card_fetch.py`.

## Development

- To add new tabs, create a new file in `ui/` and register it in `main.py`.
- To extend game logic, update or add modules in `engine/`.
- For debugging, press F9 in the app to open the debug window.

## License

MIT License

---

**Enjoy playing Commander on your desktop!**
