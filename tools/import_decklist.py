import sys, re, json, os

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
            cnt = int(m.group(1)); name = m.group(2).strip()
            cards.extend([name]*cnt)
        else:
            cards.append(line)
    return commander, cards

def write_txt(path, commander, cards):
    if not commander:
        raise ValueError("Commander: <name> line required.")
    counts = {}
    for c in cards:
        counts[c] = counts.get(c,0)+1
    lines = [f"Commander: {commander}"] + [f"{ct} {name}" for name, ct in sorted(counts.items())]
    with open(path,'w',encoding='utf-8') as f:
        f.write("\n".join(lines)+"\n")
    print(f"[WRITE] {path}")

def verify_names(cards, commander, card_db_path):
    with open(card_db_path,'r',encoding='utf-8') as f:
        db = json.load(f)
    names = {c['name'].lower() for c in db if isinstance(c,dict) and c.get('name')}
    missing = [n for n in [commander]+cards if n.lower() not in names]
    if missing:
        print("[WARN] Missing in DB:", ", ".join(missing[:10]))
    return missing

def main(deck_txt_in, card_db_json, out_txt):
    with open(deck_txt_in,'r',encoding='utf-8') as f:
        text = f.read()
    commander, cards = parse_decklist_text(text)
    verify_names(cards, commander, card_db_json)
    write_txt(out_txt, commander, cards)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python tools/import_decklist.py <input_decklist.txt> <card_db_full.json> <output_deck.txt>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
