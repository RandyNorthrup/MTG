import os
import json
import re

from . import card_sql as _sql

_NORMALIZE_RE = re.compile(r'[^a-z0-9]+')
def _normalize_name(s: str) -> str:
    return _NORMALIZE_RE.sub(' ', s.lower()).strip()

_CARD_DB_CACHE = None   # (by_id, by_name_lower, by_norm, path)
_CARD_NAME_LIST = None  # cached sorted list of names for deck editor search
_USE_SQL = False

def enable_sql():
    global _USE_SQL
    _USE_SQL = True

def load_card_db(force: bool = False):  # patched: delegate to SQL if enabled
    global _CARD_DB_CACHE, _CARD_NAME_LIST
    if _USE_SQL and _sql.sql_enabled():
        # Lightweight pseudo-cache (expose same tuple shape but lazy lists)
        if _CARD_DB_CACHE is None or force:
            _CARD_DB_CACHE = ({}, {}, {}, 'cards.db')  # placeholders not used directly
            _CARD_NAME_LIST = _sql.list_all_names()
        return _CARD_DB_CACHE
    if _CARD_DB_CACHE is not None and not force:
        return _CARD_DB_CACHE
    base = os.path.join('data','cards','card_db.json')
    full = os.path.join('data','cards','card_db_full.json')
    path = full if os.path.exists(full) else base
    with open(path,'r',encoding='utf-8') as f:
        raw = json.load(f)
    raw_cards = list(raw.values()) if isinstance(raw, dict) else list(raw)
    cards = []
    for c in raw_cards:
        if isinstance(c, dict) and 'id' in c and 'name' in c:
            cards.append(c)
    by_id = {c['id']:c for c in cards}
    by_name_lower = {c['name'].lower(): c for c in cards}
    by_norm = {_normalize_name(c['name']): c for c in cards}
    _CARD_DB_CACHE = (by_id, by_name_lower, by_norm, path)
    _CARD_NAME_LIST = sorted(by_name_lower.keys())
    return _CARD_DB_CACHE

def get_card_name_list():
    if _USE_SQL and _sql.sql_enabled():
        return _sql.list_all_names()
    global _CARD_NAME_LIST
    if _CARD_NAME_LIST is None:
        load_card_db()
    by_id, *_ = load_card_db()
    return sorted({c['name'] for c in by_id.values()})

# OPTIONAL bootstrap (call once early if env var set)
def maybe_bootstrap_sql():
    if not (os.environ.get('MTG_SQL') or os.environ.get('MTG_SQL_BOOT')):
        return
    base = os.path.join('data','cards','card_db.json')
    full = os.path.join('data','cards','card_db_full.json')
    _sql.enable_or_bootstrap([full, base])
    enable_sql()
