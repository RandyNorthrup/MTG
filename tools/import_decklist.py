import json, sys, re

def parse_decklist_text(text):
    commander = None
    cards = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.lower().startswith('sideboard'):
            continue
        if line.lower().startswith('commander:'):
            commander = line.split(':',1)[1].strip()
            continue
        m = re.match(r'^(\d+)\s+(.+)$', line)
        if m:
            count = int(m.group(1))
            name = m.group(2).strip()
            for _ in range(count):
                cards.append(name)
        else:
            cards.append(line)
    return { "name": "Imported Deck", "commander": commander, "cards": cards }

def map_names_to_ids(deck, card_db_by_name):
    if deck['commander'] is None:
        raise ValueError('Commander not specified in decklist. Use: Commander: <name>')
    try:
        commander_id = card_db_by_name[deck['commander']]['id']
    except KeyError:
        raise ValueError(f"Commander not found in DB: {deck['commander']}")

    ids = []
    for nm in deck['cards']:
        if nm == deck['commander']:
            continue
        c = card_db_by_name.get(nm) or next((v for k,v in card_db_by_name.items() if k.lower()==nm.lower()), None)
        if not c:
            print(f"[WARN] Not in DB: {nm}")
            continue
        ids.append(c['id'])
    return { "name": deck['name'], "commander": commander_id, "cards": ids }

def main(deck_txt_path, card_db_json_path, out_json_path):
    with open(deck_txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    with open(card_db_json_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
    by_name = { c['name']: c for c in db }
    deck_names = parse_decklist_text(text)
    deck_ids = map_names_to_ids(deck_names, by_name)
    with open(out_json_path, 'w', encoding='utf-8') as f:
        json.dump(deck_ids, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_json_path}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python import_decklist.py <decklist.txt> <card_db_full.json> <output_deck.json>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
