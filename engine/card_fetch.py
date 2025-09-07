import os, re, json, random
from typing import List, Tuple, Dict, Any
from engine.card_db import load_card_db
from image_cache import ensure_card_image
from engine.rules_engine import parse_and_attach
from engine.card_engine import Card
from . import card_sql as _sql

# --- SDK availability & toggle ---
try:
    from mtgsdk import Card as MTGSDKCard  # type: ignore
    _HAVE_MTGSDK = True
except Exception:  # pragma: no cover
    _HAVE_MTGSDK = False

_SDK_ONLINE = False
def set_sdk_online(flag: bool):
    global _SDK_ONLINE
    _SDK_ONLINE = bool(flag and _HAVE_MTGSDK)

_NORMALIZE_RE = re.compile(r'[^a-z0-9]+')
def _normalize_name(s: str) -> str:
    return _NORMALIZE_RE.sub(' ', s.lower()).strip()

# Track injected cards (for diagnostics / caching)
_INJECTED = {}

# -------- SDK Fetch Helpers --------
def _sdk_card_pick(name: str):
    if not (_SDK_ONLINE and _HAVE_MTGSDK):
        raise KeyError(name)
    q = MTGSDKCard.where(name=name).all()
    if not q:
        q = MTGSDKCard.where(page=1).all()
    for c in q:
        if c.name.lower() == name.lower():
            return c
    if q:
        return q[0]
    raise KeyError(name)

def _sdk_fetch_rulings(card_obj):
    try:
        raw = MTGSDKCard.rulings(card_obj.id)
        if raw:
            return [f"{r.get('date','')}: {r.get('text','')}" for r in raw]
    except Exception:
        pass
    return []

def _sdk_fetch_card(name: str) -> Dict[str, Any]:
    pick = _sdk_card_pick(name)
    cid = pick.id or pick.multiverse_id or (pick.set + ":" + pick.number)
    types = []
    if pick.type:
        main = pick.type.split('—')[0].strip()
        for t in main.replace('-', ' ').split():
            if t and t[0].isalpha():
                types.append(t)
    mana_cost_str = pick.mana_cost or ""
    total_cost = 0
    for num in re.findall(r'\{(\d+)\}', mana_cost_str):
        total_cost += int(num)
    total_cost += len(re.findall(r'\{[WUBRG]\}', mana_cost_str))
    rulings = _sdk_fetch_rulings(pick)
    card_dict = {
        'id': cid,
        'name': pick.name,
        'types': types or ['Card'],
        'mana_cost': total_cost,
        'mana_cost_str': mana_cost_str,
        'power': pick.power if (pick.power and pick.power.isdigit()) else None,
        'toughness': pick.toughness if (pick.toughness and pick.toughness.isdigit()) else None,
        'text': pick.text or "",
        'color_identity': pick.color_identity or [],
        'rulings': rulings
    }
    _sql.upsert_card(card_dict)
    return card_dict

def _inject_card(c, caches):
    by_id, by_name_lower, by_norm, _ = caches
    by_id[c['id']] = c
    by_name_lower[c['name'].lower()] = c
    by_norm[_normalize_name(c['name'])] = c
    _INJECTED[c['id']] = c

# -------- Resolution / Build --------
def _resolve_entry(entry: str, caches, deck_path: str, db_path: str):
    by_id, by_name_lower, by_norm, _ = caches
    if entry in by_id:
        return by_id[entry]
    low = entry.lower()
    c = by_name_lower.get(low)
    if c:
        return c
    c = by_norm.get(_normalize_name(entry))
    if c:
        return c
    candidates = [v for k, v in by_name_lower.items() if k.startswith(low)]
    if len(candidates) == 1:
        return candidates[0]
    sql_hit = _sql.fetch_by_exact(entry) or _sql.fetch_by_norm_or_prefix(entry)
    if sql_hit:
        return sql_hit
    if _SDK_ONLINE and _HAVE_MTGSDK:
        try:
            fetched = _sdk_fetch_card(entry)
            _inject_card(fetched, caches)
            return fetched
        except KeyError:
            pass
    raise KeyError(f"Card '{entry}' not found (deck={deck_path} db={db_path}{' sdk' if _SDK_ONLINE else ''})")

def _build_cards(entries: List[str], commander_name: str, *, caches, deck_path: str, owner_id: int):
    by_id, by_name_lower, by_norm, db_path = caches
    commander_src = _resolve_entry(commander_name, caches, deck_path, db_path) if commander_name else None
    cards = []
    for e in entries:
        src = _resolve_entry(e, caches, deck_path, db_path)
        if commander_src and src['id'] == commander_src['id']:
            continue
        card_obj = Card(
            id=src['id'], name=src['name'], types=src['types'], mana_cost=src['mana_cost'],
            power=src.get('power'), toughness=src.get('toughness'), text=src.get('text', ''),
            is_commander=False, color_identity=src.get('color_identity', []),
            owner_id=owner_id, controller_id=owner_id
        )
        if 'mana_cost_str' in src:
            setattr(card_obj, 'mana_cost_str', src['mana_cost_str'])
        parse_and_attach(card_obj)
        cards.append(card_obj)
    commander_obj = None
    if commander_src:
        commander_obj = Card(
            id=commander_src['id'], name=commander_src['name'], types=commander_src['types'],
            mana_cost=commander_src['mana_cost'], power=commander_src.get('power'),
            toughness=commander_src.get('toughness'), text=commander_src.get('text', ''),
            is_commander=True, color_identity=commander_src.get('color_identity', []),
            owner_id=owner_id, controller_id=owner_id
        )
        if 'mana_cost_str' in commander_src:
            setattr(commander_obj, 'mana_cost_str', commander_src['mana_cost_str'])
        parse_and_attach(commander_obj)
    return cards, commander_obj

# -------- Public API --------
def parse_deck_txt_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    entries = []
    commander = None
    last = None
    with open(path, 'r', encoding='utf-8-sig') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            low = line.lower()
            if low.startswith('commander:'):
                cand = line.split(':', 1)[1].strip()
                if cand:
                    commander = cand
                continue
            m = re.match(r'^(\d+)\s+(.+)$', line)
            if m:
                ct = int(m.group(1)); name = m.group(2).strip()
                if ct > 0 and name:
                    entries.extend([name] * ct)
                    last = name
            else:
                entries.append(line); last = line
    if commander is None:
        commander = last
    return entries, commander

def load_deck(path: str, owner_id: int):
    caches = load_card_db()
    by_id, by_name_lower, by_norm, db_path = caches
    entries, commander_name = parse_deck_txt_file(path)
    return _build_cards(entries, commander_name,
                        caches=caches, deck_path=path, owner_id=owner_id)

def load_banlist(path: str):
    banned = set()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    banned.add(line)
    return banned

def enrich_game_with_sdk(game):
    if not (_SDK_ONLINE and _HAVE_MTGSDK):
        return
    seen = set()
    for pl in game.players:
        pools = []
        if pl.commander:
            pools.append([pl.commander])
        pools.append(pl.library)
        for group in pools:
            for card in group:
                if not card or card.name in seen:
                    continue
                need = (not getattr(card, 'mana_cost_str', None) or
                        not getattr(card, 'text', None) or
                        not hasattr(card, 'rulings'))
                if not need:
                    continue
                try:
                    data = _sdk_fetch_card(card.name)
                except KeyError:
                    continue
                if data.get('mana_cost_str'):
                    setattr(card, 'mana_cost_str', data['mana_cost_str'])
                if data.get('text'):
                    card.text = data['text']
                if data.get('power') and data.get('toughness'):
                    try:
                        card.power = int(data['power']); card.toughness = int(data['toughness'])
                    except Exception:
                        pass
                if 'rulings' in data:
                    setattr(card, 'rulings', data['rulings'])
                try:
                    parse_and_attach(card)
                except Exception:
                    pass
                seen.add(card.name)

def prewarm_card_images(players, limit_per_library=25):
    for pl in players:
        if getattr(pl, 'commander', None):
            ensure_card_image(pl.commander.id)
        for c in list(getattr(pl, 'library', []))[:limit_per_library]:
            ensure_card_image(c.id)
