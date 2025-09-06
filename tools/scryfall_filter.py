import json, sys, argparse

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _score_printing(c):
    """
    Lower score preferred: non-promo, non-digital, lowest collector number.
    """
    score = 0
    if c.get('promo'): score += 1000
    if c.get('digital'): score += 500
    raw = str(c.get('collector_number', '9999')).split('★')[0]
    try:
        score += int(''.join(ch for ch in raw if ch.isdigit()) or 9999)
    except:
        score += 9999
    return score

MANA_SYMBOL_RELEVANT = set("WUBRGX0123456789{}")

def _mv_from_mana(mana_cost: str) -> int:
    """
    Approximate converted mana value: count digits & colored symbols.
    Ignores hybrid / phyrexian nuance (acceptable for prototype).
    """
    if not mana_cost:
        return 0
    total = 0
    token = ''
    inside = False
    for ch in mana_cost:
        if ch == '{':
            inside = True
            token = ''
        elif ch == '}':
            inside = False
            sym = token.upper()
            if sym.isdigit():
                total += int(sym)
            elif sym in ('X','Y','Z'):
                # X treated as 0 (variable)
                pass
            else:
                # Hybrid / phyrexian / single symbol all count as 1
                total += 1
        elif inside and ch in MANA_SYMBOL_RELEVANT:
            token += ch
    return total

TYPE_KEYWORDS = ("Land","Creature","Instant","Sorcery","Artifact","Enchantment","Planeswalker")

def _extract_types(type_line: str):
    if not type_line:
        return []
    return [k for k in TYPE_KEYWORDS if k in type_line]

def _int_or_none(v):
    try:
        s = str(v)
        return int(s) if s.isdigit() else None
    except:
        return None

def filter_cards(data, limit=None, verbose=False):
    by_name = {}
    for card in data:
        if not isinstance(card, dict):
            continue
        if card.get('lang') != 'en':
            continue
        layout = card.get('layout','')
        if layout in {'token','art_series'}:
            continue
        name = card.get('name')
        if not name:
            continue
        # Transform / modal: keep face a (side 'a' or missing), drop side 'b'
        if card.get('side') == 'b':
            continue
        existing = by_name.get(name)
        if existing is None or _score_printing(card) < _score_printing(existing):
            by_name[name] = card
            if limit and len(by_name) >= limit:
                break
    if verbose:
        print(f"[FILTER] Selected {len(by_name)} unique names.")
    return by_name

def convert(by_name, prune_empty=False):
    out = []
    append = out.append
    for name, c in by_name.items():
        ci = c.get('color_identity') or c.get('colors') or []
        types = _extract_types(c.get('type_line',''))
        mv = _mv_from_mana(c.get('mana_cost',''))
        if prune_empty and (not types and not name):
            continue
        append({
            "id": c.get('id', name.replace(' ','_').lower()),
            "name": name,
            "types": types or ["Other"],
            "mana_cost": mv,
            "power": _int_or_none(c.get('power')),
            "toughness": _int_or_none(c.get('toughness')),
            "text": c.get('oracle_text','') or '',
            "color_identity": ci,
        })
    return out

def main():
    ap = argparse.ArgumentParser(description="Filter Scryfall bulk JSON into simplified DB.")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--limit", type=int, help="Stop after collecting this many unique names (debug).")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--prune-empty", action="store_true", help="Skip entries that would serialize mostly empty (safety).")
    args = ap.parse_args()

    data = load(args.input)
    by_name = filter_cards(data, limit=args.limit, verbose=args.verbose)
    out = convert(by_name, prune_empty=args.prune_empty)
    save(args.output, out)
    if args.verbose:
        print(f"[WRITE] {len(out)} cards -> {args.output}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Usage: python tools/scryfall_filter.py <input_bulk.json> <output_card_db_full.json> [--limit N]")
        sys.exit(1)
    main()
    main()
