from __future__ import annotations
from typing import List, Optional, Tuple
import re

_LINE_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")

def _clean_line(s: str) -> Optional[str]:
    """
    Returns a stripped line or None if the line is a comment/blank.
    Lines starting with '#' are treated as comments.
    """
    if not s:
        return None
    s = s.strip()
    if not s or s.startswith("#"):
        return None
    return s

def parse_commander_txt(path: str) -> Tuple[List[str], Optional[str]]:
    """
    Parse a plain-text Commander decklist like:
        31 Forest
        1 Sedge Scorpion
        ...

        1 Fynn, the Fangbearer

    We treat the **last non-empty, non-comment line** as the commander line.
    Everything above it is main-deck entries. Each line is "N Name".
    Returns: (entries_expanded, commander_name)
            - entries_expanded is a flat list of names repeated N times
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    # Filter comments/empty lines but keep order
    lines = [cl for cl in (_clean_line(x) for x in raw_lines) if cl is not None]
    if not lines:
        return [], None

    # Commander is the last non-empty line in this format
    commander_line = lines[-1]
    m_cmd = _LINE_RE.match(commander_line)
    if not m_cmd:
        commander_name = None
        main_lines = lines
    else:
        # quantity on the commander line is ignored (should be 1)
        commander_name = m_cmd.group(2)
        main_lines = lines[:-1]

    # Expand main-deck entries
    entries: List[str] = []
    for line in main_lines:
        m = _LINE_RE.match(line)
        if not m:
            continue  # ignore odd lines
        qty = int(m.group(1))
        name = m.group(2)
        entries.extend([name] * qty)

    # Remove one copy if commander also appears in the list
    if commander_name:
        try:
            entries.remove(commander_name)
        except ValueError:
            pass

    return entries, commander_name