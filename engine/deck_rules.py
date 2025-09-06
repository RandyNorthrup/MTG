from collections import Counter
from typing import Iterable, Dict, Set, Tuple, List

BASIC_NAMES = {'plains','island','swamp','mountain','forest'}

def validate_commander_deck(
    commander_id: str,
    card_ids: Iterable[str],
    card_db: Iterable[Dict],
    banned: Set[str]
) -> Tuple[bool, List[str]]:
    """
    Validate a Commander deck (commander + 99 others).
    Rules:
      - Commander present
      - Total 100 cards (incl. commander)
      - Singleton (except basic lands)
      - Banlist
      - Color identity
    """
    issues: List[str] = []
    if not commander_id:
        return False, ["Missing commander"]
    by_id = {c['id']: c for c in card_db if 'id' in c}
    commander = by_id.get(commander_id)
    if not commander:
        return False, ["Commander not found in card DB"]

    others = list(card_ids)
    if len(others) + 1 != 100:
        issues.append(f"Deck size {len(others)+1} (expected 100 incl. commander)")

    if commander.get('name') in banned:
        issues.append(f"Commander banned: {commander.get('name')}")

    banned_hits = [by_id[c]['name'] for c in others if c in by_id and by_id[c].get('name') in banned]
    if banned_hits:
        issues.append("Banned cards: " + ", ".join(sorted(set(banned_hits))[:5]))

    names = [by_id[c]['name'] for c in others if c in by_id]
    dupes = [n for n, cnt in Counter(names).items() if cnt > 1 and n.lower() not in BASIC_NAMES]
    if dupes:
        issues.append("Non-singleton: " + ", ".join(dupes[:5]))

    cmd_colors = set(commander.get('color_identity') or [])
    if cmd_colors:
        off = []
        for cid in others:
            card = by_id.get(cid)
            if not card:
                continue
            ci = set(card.get('color_identity') or [])
            if not ci.issubset(cmd_colors):
                off.append(card.get('name'))
        if off:
            issues.append("Off-color: " + ", ".join(off[:5]))

    return (len(issues) == 0), issues
    if cmd_colors:
        off_color = []
        for cid in others:
            card = by_id.get(cid)
            if not card:
                continue
            ci = set(card.get('color_identity') or [])
            if not ci.issubset(cmd_colors):
                off_color.append(card.get('name'))
        if off_color:
            issues.append("Off-color: " + ", ".join(off_color[:5]))

    return (len(issues) == 0), issues
