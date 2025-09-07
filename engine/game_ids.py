import os, random, datetime

_IDS_PATH = os.path.join("data", "game_ids.txt")

def _ensure_file():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(_IDS_PATH):
        with open(_IDS_PATH, "w", encoding="utf-8") as f:
            f.write("")

def load_existing_ids():
    _ensure_file()
    bases = set()
    with open(_IDS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            base = line.split('-', 1)[0]  # ignore appended timestamp
            bases.add(base)
    return bases

def generate_game_id() -> str:
    """
    Returns a unique 10-digit numeric id appended with a UTC timestamp:
      <10digits>-YYYYMMDDHHMMSS
    Uniqueness enforced on the 10-digit portion.
    """
    existing_bases = load_existing_ids()
    while True:
        base = "".join(random.choice("0123456789") for _ in range(10))
        if base not in existing_bases:
            ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            return f"{base}-{ts}"

def register_game_id(gid: str):
    _ensure_file()
    with open(_IDS_PATH, "a", encoding="utf-8") as f:
        f.write(gid + "\n")
