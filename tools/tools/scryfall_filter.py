import json, sys

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main(in_path, out_path):
    data = load(in_path)
    by_name = {}
    for card in data:
        if card.get('lang') != 'en':
            continue
        if card.get('layout') in {'token','art_series'}:
            continue
        name = card.get('name')
        if not name:
            continue

        if name not in by_name:
            by_name[name] = card
        else:
            existing = by_name[name]
            def score(c):
                s = 0
                if c.get('promo'): s += 5
                if c.get('digital'): s += 5
                try:
                    s += int(str(c.get('collector_number','9999')).split('★')[0])
                except:
                    s += 9999
                return s
            if score(card) < score(existing):
                by_name[name] = card

    out = []
    for name, c in by_name.items():
        ci = c.get('color_identity') or c.get('colors') or []
        types = []
        tl = c.get('type_line','')
        if 'Land' in tl: types.append('Land')
        if 'Creature' in tl: types.append('Creature')
        if 'Instant' in tl: types.append('Instant')
        if 'Sorcery' in tl: types.append('Sorcery')
        if 'Artifact' in tl: types.append('Artifact')
        if 'Enchantment' in tl: types.append('Enchantment')
        if 'Planeswalker' in tl: types.append('Planeswalker')

        power = None; toughness = None
        try:
            power = int(c.get('power')) if c.get('power') and str(c.get('power')).isdigit() else None
            toughness = int(c.get('toughness')) if c.get('toughness') and str(c.get('toughness')).isdigit() else None
        except:
            pass

        mc_str = c.get('mana_cost','')
        total_cost = 0
        num = ''
        for ch in mc_str:
            if ch.isdigit():
                num += ch
            elif ch == '}':
                if num:
                    total_cost += int(num)
                    num = ''
            elif ch in '{WUBRG':
                total_cost += 1
        if num:
            total_cost += int(num)

        out.append({
            "id": c.get('id', name.replace(' ','_').lower()),
            "name": name,
            "types": types or ["Other"],
            "mana_cost": total_cost,
            "power": power,
            "toughness": toughness,
            "text": c.get('oracle_text','') or '',
            "color_identity": ci,
        })
    save(out_path, out)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python scryfall_filter.py <input_bulk_default_cards.json> <output_card_db_full.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
