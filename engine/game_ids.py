import os, random

_IDS_PATH = os.path.join("data", "game_ids.txt")

def _ensure_file():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(_IDS_PATH):
        with open(_IDS_PATH, "w", encoding="utf-8") as f:
            f.write("")

def load_existing_ids():
    _ensure_file()
    with open(_IDS_PATH, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def generate_game_id() -> str:
    existing = load_existing_ids()
    while True:
        gid = "".join(random.choice("0123456789") for _ in range(10))
        if gid not in existing:
            return gid

def register_game_id(gid: str):
    _ensure_file()
    with open(_IDS_PATH, "a", encoding="utf-8") as f:
        f.write(gid + "\n")
