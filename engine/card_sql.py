import os, json, sqlite3, re, threading
_DB_PATH = os.path.join('data', 'cards', 'cards.db')
_LOCK = threading.RLock()
_NORMALIZE_RE = re.compile(r'[^a-z0-9]+')

def normalize(name: str) -> str:
    return _NORMALIZE_RE.sub(' ', name.lower()).strip()

def get_conn():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_schema():
    with _LOCK:
        with get_conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS cards(
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_lower TEXT NOT NULL,
                norm TEXT NOT NULL,
                data TEXT NOT NULL
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_cards_lower ON cards(name_lower)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_cards_norm ON cards(norm)")

def load_json_into_sql(json_path: str):
    """One‑time migration from existing card_db.json / full file."""
    if not os.path.exists(json_path):
        return
    ensure_schema()
    with open(json_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    cards = list(raw.values()) if isinstance(raw, dict) else list(raw)
    with _LOCK, get_conn() as c:
        cur = c.cursor()
        to_insert = []
        for card in cards:
            if not isinstance(card, dict) or 'id' not in card or 'name' not in card:
                continue
            cid = str(card['id'])
            nm = card['name']
            jl = json.dumps(card, ensure_ascii=False)
            to_insert.append((cid, nm, nm.lower(), normalize(nm), jl))
        cur.executemany(
            "INSERT OR IGNORE INTO cards(id,name,name_lower,norm,data) VALUES(?,?,?,?,?)",
            to_insert
        )

def sql_enabled():
    return os.path.exists(_DB_PATH)

def enable_or_bootstrap(json_fallback_paths):
    """Call at startup: create DB if missing and migrate."""
    if sql_enabled():
        return
    # pick first existing json source
    for p in json_fallback_paths:
        if os.path.exists(p):
            load_json_into_sql(p)
            break

def fetch_by_id(cid: str):
    if not sql_enabled(): return None
    with _LOCK, get_conn() as c:
        r = c.execute("SELECT data FROM cards WHERE id=?", (cid,)).fetchone()
        return json.loads(r['data']) if r else None

def fetch_by_exact(name: str):
    if not sql_enabled(): return None
    low = name.lower()
    with _LOCK, get_conn() as c:
        r = c.execute("SELECT data FROM cards WHERE name_lower=?", (low,)).fetchone()
        return json.loads(r['data']) if r else None

def fetch_by_norm_or_prefix(name: str):
    if not sql_enabled(): return None
    norm = normalize(name)
    with _LOCK, get_conn() as c:
        r = c.execute("SELECT data FROM cards WHERE norm=?", (norm,)).fetchone()
        if r: return json.loads(r['data'])
        # unique prefix
        rows = c.execute("SELECT data FROM cards WHERE name_lower LIKE ? LIMIT 2",
                         (name.lower()+'%',)).fetchall()
        if len(rows) == 1:
            return json.loads(rows[0]['data'])
    return None

def list_all_names(limit=None):
    if not sql_enabled(): return []
    q = "SELECT name FROM cards ORDER BY name_lower"
    if limit: q += f" LIMIT {int(limit)}"
    with _LOCK, get_conn() as c:
        return [r['name'] for r in c.execute(q)]

def upsert_card(card_dict: dict):
    """Persist newly fetched (SDK) card."""
    if not sql_enabled(): return
    cid = str(card_dict['id'])
    nm = card_dict['name']
    with _LOCK, get_conn() as c:
        c.execute("""INSERT OR REPLACE INTO cards(id,name,name_lower,norm,data)
                     VALUES(?,?,?,?,?)""",
                  (cid, nm, nm.lower(), normalize(nm), json.dumps(card_dict, ensure_ascii=False)))
