from typing import List, Tuple, Dict, Optional

# Official Magic: The Gathering turn structure (phases and steps)
PHASE_SEQUENCE: List[str] = [
    "beginning",
    "precombat_main",
    "combat",
    "postcombat_main",
    "ending"
]

PHASE_STEPS: Dict[str, List[str]] = {
    "beginning": ["untap", "upkeep", "draw"],
    "precombat_main": ["main1"],
    "combat": [
        "begin_combat",
        "declare_attackers",
        "declare_blockers",
        "combat_damage",
        "end_of_combat"
    ],
    "postcombat_main": ["main2"],
    "ending": ["end_step", "cleanup"]
}

# Flattened ordered (phase, step) pairs for full traversal.
FLAT_TURN_ORDER: List[Tuple[str, str]] = [
    (phase, step) for phase in PHASE_SEQUENCE for step in PHASE_STEPS[phase]
]

def first_step_of_phase(phase: str) -> str:
    return PHASE_STEPS[phase][0]

def is_last_step_in_phase(phase: str, step: str) -> bool:
    steps = PHASE_STEPS[phase]
    return steps and steps[-1] == step

def next_phase_after(phase: str) -> Optional[str]:
    try:
        idx = PHASE_SEQUENCE.index(phase)
    except ValueError:
        return None
    if idx + 1 < len(PHASE_SEQUENCE):
        return PHASE_SEQUENCE[idx + 1]
    return None

def next_flat_step(phase: str, step: str) -> Optional[Tuple[str, str]]:
    """
    Return the next (phase, step) pair in the strict turn order or None if end-of-turn.
    """
    try:
        phase_steps = PHASE_STEPS[phase]
        idx = phase_steps.index(step)
    except Exception:
        return None
    # next step inside phase
    if idx + 1 < len(phase_steps):
        return phase, phase_steps[idx + 1]
    # move to first step of next phase
    nxt = next_phase_after(phase)
    if nxt is None:
        return None
    return nxt, first_step_of_phase(nxt)
