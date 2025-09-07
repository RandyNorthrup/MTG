import json, sys, argparse, re

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _score_printing(c):
    # Lower score is better
    score = 0
    if c.get('promo'): score += 1000
    if c.get('digital'): score += 500
    raw = str(c.get('collector_number', '9999')).split('★')[0]
    digits = ''.join(ch for ch in raw if ch.isdigit())
    score += int(digits) if digits.isdigit() else 9999
    return score

MANA_SYMBOL_RELEVANT = set("WUBRGX0123456789{}")

_MANA_TOKEN_RE = re.compile(r'\{([^}]+)\}')

def _mv_from_mana(mana_cost: str) -> int:
    if not mana_cost:
        return 0
    total = 0
    for sym in _MANA_TOKEN_RE.findall(mana_cost):
        s = sym.upper()
        if s.isdigit():
            total += int(s)
        elif s in ('X','Y','Z'):
            continue
        else:
            total += 1
    return total

TYPE_KEYWORDS = ("Land","Creature","Instant","Sorcery","Artifact","Enchantment","Planeswalker")

def _extract_types(type_line: str):
    if not type_line:
        return []
    tl = type_line.lower()
    return [k for k in TYPE_KEYWORDS if k.lower() in tl]

def _int_or_none(v):
    try:
        s = str(v)
        return int(s) if s.isdigit() else None
    except Exception:
        return None

def filter_cards(data, limit=None, verbose=False, case_dedupe=False):
    """
    case_dedupe=True treats Name / name / NAME as one (keeps best score).
    """
    by_name = {}
    keyfn = (lambda n: n.lower()) if case_dedupe else (lambda n: n)
    for card in data:
        # ADDED: fast rejects
        if not isinstance(card, dict):
            continue
        if card.get('lang') != 'en':
            continue
        if card.get('layout','') in {'token','art_series','double_faced_token'}:
            continue
        name = card.get('name')
        if not name:
            continue
        if card.get('side') == 'b':
            continue
        k = keyfn(name)
        existing = by_name.get(k)
        if existing is None or _score_printing(card) < _score_printing(existing):
            by_name[k] = card
            if limit and len(by_name) >= limit:
                break
    if verbose:
        total = sum(1 for c in data if isinstance(c, dict))
        print(f"[FILTER] Scanned={total} kept={len(by_name)}")
    return by_name

def convert(by_name, prune_empty=False, sort_name=False):
    # REMOVED dead preliminary loop + 'pass'
    out = []
    seq = (sorted(by_name.items(), key=lambda kv: kv[1]['name'].lower())
           if sort_name else by_name.items())
    for _, c in seq:
        name = c.get('name','')
        types = _extract_types(c.get('type_line',''))
        if prune_empty and (not types and not name):
            continue
        raw_cost_str = c.get('mana_cost','') or ''
        out.append({
            "id": c.get('id', name.replace(' ','_').lower()),
            "name": name,
            "types": types or ["Other"],
            "mana_cost": _mv_from_mana(raw_cost_str),
            "mana_cost_str": raw_cost_str,
            "power": _int_or_none(c.get('power')),
            "toughness": _int_or_none(c.get('toughness')),
            "text": c.get('oracle_text','') or '',
            "color_identity": c.get('color_identity') or c.get('colors') or [],
        })
    return out

def main():
    parser = argparse.ArgumentParser(description="Filter Scryfall bulk JSON into simplified DB.")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--limit", type=int, help="Stop after collecting this many unique names (debug).")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--prune-empty", action="store_true", help="Skip mostly empty entries.")
    parser.add_argument("--case-dedupe", action="store_true", help="Treat name case-insensitively when selecting best printing.")
    parser.add_argument("--sort-name", action="store_true", help="Deterministic alphabetical output order.")
    args = parser.parse_args()

    data = load(args.input)
    by_name = filter_cards(data, limit=args.limit, verbose=args.verbose, case_dedupe=args.case_dedupe)
    out = convert(by_name, prune_empty=args.prune_empty, sort_name=getattr(args,'sort_name',False))
    save(args.output, out)
    if args.verbose:
        print(f"[WRITE] {len(out)} cards -> {args.output}")

    # build name index earlier in file; assume variable card_index exists
    # Guard undefined by_name -> derive from card_index
    by_name = {c['name'].lower(): c for c in data}  # ensure defined

    q = (args.query or "").lower()
    limit = getattr(args, 'limit', None)
    results = []
    for name, card in by_name.items():
        if q and q not in name:
            continue
        results.append(card)
        if limit and len(results) >= limit:
            break
    # ...output logic...

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Usage: python tools/scryfall_filter.py <input_bulk.json> <output_card_db_full.json> [--limit N]")
        sys.exit(1)
    main()
