import json

COLOR_CODES = set(list("WUBRG"))

def read_banlist(path):
    banned = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            banned.add(line)
    return banned

def color_identity_from_commander(card):
    return set(card.get('color_identity', []))

def check_deck_legality(deck_json, card_db, banlist_path):
    """Validate Commander deck legality (singleton, color identity, banned)."""
    problems = []
    banned = read_banlist(banlist_path)

    commander_id = deck_json.get('commander')
    if not commander_id or commander_id not in card_db:
        problems.append('Missing commander or commander not found in DB.')
        return False, problems

    commander = card_db[commander_id]
    ci = color_identity_from_commander(commander)

    seen = {}
    for cid in deck_json.get('cards', []):
        seen[cid] = seen.get(cid, 0) + 1
    for cid, count in seen.items():
        name = card_db.get(cid, {}).get('name', cid)
        if name.lower().startswith(('plains','island','swamp','mountain','forest')):
            continue
        if count > 1:
            problems.append(f'Singleton violation: {name} appears {count}x.')

    def within_color_identity(card):
        cci = set(card.get('color_identity', []))
        return cci.issubset(ci)

    for cid in deck_json.get('cards', []):
        c = card_db.get(cid)
        if not c:
            problems.append(f'Card not found in DB: {cid}')
            continue
        if not within_color_identity(c):
            problems.append(f'Color identity violation: {c.get("name","?")}')
        if c.get('name') in banned:
            problems.append(f'BANNED: {c.get("name")}')
    ok = len(problems) == 0
    return ok, problems
