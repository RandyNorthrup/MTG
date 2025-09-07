import re
from typing import List
from .ability import Ability, TriggeredAbility, StaticKeywordAbility
from .ability import TriggerEvent  # NEW
from .ability import ActivatedAbility  # NEW
from .ability import StaticBuffAbility  # NEW
from engine.mana import ManaPool, parse_mana_cost  # added parse_mana_cost for cost parsing
# Regex patterns (very small subset)
_PAT_ETB = re.compile(r'^\s*when\s+.*?enters the battlefield,\s*(.+)$', re.IGNORECASE)
_PAT_ATTACK = re.compile(r'^\s*whenever\s+.*?attacks,\s*(.+)$', re.IGNORECASE)
_PAT_CREATURE_ETB_YOU = re.compile(r'^\s*whenever\s+(?:a|another)\s+creature\s+enters the battlefield under your control,\s*(.+)$', re.IGNORECASE)
_PAT_DIES = re.compile(r'^\s*wh(?:en|enever)\s+.*?\bdies,\s*(.+)$', re.IGNORECASE)  # NEW
_PAT_BUFF = re.compile(r'^\s*(other\s+)?creatures you control get \+(\d+)\s*/\s*\+(\d+)', re.IGNORECASE)  # NEW

# Activated ability pattern: "<COST>: <effect>"
# COST tokens separated by commas. Recognizes {T}, mana symbols, and leading numbers / color letters.
_ACTIVATED_SPLIT = re.compile(r'^\s*(.+?)\s*:\s*(.+)$')

_KEYWORDS = ("Flying","Trample","Deathtouch","Vigilance","Haste","Reach","Lifelink","Menace","First strike","Double strike")

def parse_oracle_text(raw: str) -> List[Ability]:
    """
    Convert a (possibly multi-line) oracle text into a list of structured abilities.
    Non‑matching lines are ignored (kept only as raw text if nothing matches).
    """
    if not raw:
        return []
    abilities: List[Ability] = []
    # Split on newlines / periods (keep it simple)
    # We'll first split on newline, then further split sentences.
    candidates: List[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Break on ". " for multiple sentences on same line
        parts = [p.strip() for p in re.split(r'\.\s+', line) if p.strip()]
        candidates.extend(parts)

    for line in candidates:
        lline = line.lower()
        # Trigger: Creature ETB under your control (check before generic ETB)
        m = _PAT_CREATURE_ETB_YOU.match(line)
        if m:
            abilities.append(TriggeredAbility(kind='triggered',
                                              raw_text=line,
                                              trigger='CREATURE_ETB_YOU',
                                              effect_text=m.group(1)))
            continue
        # Generic ETB (When ~ enters the battlefield, ...)
        m = _PAT_ETB.match(line)
        if m:
            abilities.append(TriggeredAbility(kind='triggered',
                                              raw_text=line,
                                              trigger='ETB',
                                              effect_text=m.group(1)))
            continue
        # Attack trigger
        m = _PAT_ATTACK.match(line)
        if m:
            abilities.append(TriggeredAbility(kind='triggered',
                                              raw_text=line,
                                              trigger='ATTACK',
                                              effect_text=m.group(1)))
            continue
        # Death trigger
        m = _PAT_DIES.match(line)  # NEW death pattern
        if m:
            abilities.append(TriggeredAbility(kind='triggered',
                                              raw_text=line,
                                              trigger='DEATH',
                                              effect_text=m.group(1)))
            continue
        # Buffs (newly added)
        m = _PAT_BUFF.match(line)  # NEW buff before activated parse
        if m:
            abilities.append(StaticBuffAbility(kind='static',
                                               raw_text=line,
                                               other_only=bool(m.group(1)),
                                               power=int(m.group(2)),
                                               toughness=int(m.group(3))))
            continue
        # Activated abilities (newly added)
        act = _parse_activated(line)
        if act:
            abilities.append(act)
            continue
        # Keyword (any presence)
        for kw in _KEYWORDS:
            if kw.lower() in lline.split(',')[0]:  # basic containment
                abilities.append(StaticKeywordAbility(kind='static',
                                                      raw_text=line,
                                                      keyword=kw))
                break
    # If nothing recognized, optionally store whole text as a single raw Ability
    if not abilities:
        abilities.append(Ability(kind='raw', raw_text=raw))
    return abilities

def _parse_activated(line: str):
    m = _ACTIVATED_SPLIT.match(line)
    if not m:
        return None
    raw_cost, effect = m.group(1).strip(), m.group(2).strip()
    tap_cost = False
    mana_part_tokens = []
    other_tokens = []
    # Split on commas
    for tok in [t.strip() for t in raw_cost.split(',') if t.strip()]:
        if '{T}' in tok.upper() or tok.upper() == 'T':
            tap_cost = True
        else:
            mana_part_tokens.append(tok)
    mana_cost_string = ''.join(tok if tok.startswith('{') else f'{{{tok}}}' for tok in mana_part_tokens)
    mana_cost = parse_mana_cost(mana_cost_string)
    et_lower = effect.lower()
    needs_target = 'target ' in et_lower
    target_hint = None
    if 'target creature' in et_lower:
        target_hint = 'creature'
    elif 'target player' in et_lower:
        target_hint = 'player'
    return ActivatedAbility(kind='activated',
                            raw_text=line,
                            raw_cost=raw_cost,
                            mana_cost=mana_cost,
                            tap_cost=tap_cost,
                            effect_text=effect,
                            needs_target=needs_target,
                            target_hint=target_hint)

class RulesEngine:
    """
    Registry of parsed abilities. Actual effect resolution is deferred
    (stub hooks provided for future expansion).
    """
    def __init__(self, game):
        self.game = game
        self.card_abilities = {}  # card.id -> list[Ability]
        self.trigger_queue: list[TriggerEvent] = []        # NEW
        self.processing = False                           # guard against re-entrancy
        self.pending_activation = None  # (card, ability) while selecting target

    def register_card(self, card):
        if hasattr(card, 'oracle_abilities'):
            self.card_abilities[card.id] = card.oracle_abilities

    # --- Event hook stubs (to be wired into game flow later) ---
    def on_enter_battlefield(self, card):
        # Fire ETB triggers belonging to that card
        for ab in self.card_abilities.get(card.id, []):
            if isinstance(ab, TriggeredAbility) and ab.trigger == 'ETB':
                self._queue_effect(card, ab)

    def on_card_attacks(self, card):
        for ab in self.card_abilities.get(card.id, []):
            if isinstance(ab, TriggeredAbility) and ab.trigger == 'ATTACK':
                self._queue_effect(card, ab)

    def on_creature_enters_under_your_control(self, controller_id, creature_card):
        # Loop over permanents you control for CREATURE_ETB_YOU triggers
        for cid, abilities in self.card_abilities.items():
            for ab in abilities:
                if isinstance(ab, TriggeredAbility) and ab.trigger == 'CREATURE_ETB_YOU':
                    # We would verify controller ownership; omitted for prototype
                    self._queue_effect(self._find_card(cid), ab)

    def on_card_dies(self, card):  # NEW death event hook
        for ab in self.card_abilities.get(card.id, []):
            if isinstance(ab, TriggeredAbility) and ab.trigger == 'DEATH':
                self._enqueue(card, ab, {"event": "DEATH"})

    # Replace old _queue_effect with enqueue logic
    def _queue_effect(self, source_card, ability):
        self._enqueue(source_card, ability, {"event": ability.trigger})

    def _enqueue(self, source_card, ability, context):
        if source_card is None:
            return
        evt = TriggerEvent(source_card_id=source_card.id, ability=ability, context=context)
        self.trigger_queue.append(evt)
        if getattr(self.game, 'debug_rules', False):
            print(f"[RULES] Queued {ability.trigger}: {source_card.name} -> {getattr(ability,'effect_text','')}")

    def process_trigger_queue(self, limit: int = 16):
        """
        Resolve queued triggers in FIFO order (prototype: just log).
        limit prevents infinite loops.
        """
        if self.processing:
            return
        self.processing = True
        try:
            count = 0
            while self.trigger_queue and count < limit:
                evt = self.trigger_queue.pop(0)
                card = self._find_card(evt.source_card_id)
                if getattr(self.game, 'debug_rules', False):
                    print(f"[RULES][RESOLVE] {evt.ability.trigger} from {getattr(card,'name','?')} :: {getattr(evt.ability,'effect_text','')}")
                # Future: translate effect_text into actions.
                count += 1
            if count == limit and self.trigger_queue:
                print("[RULES] Trigger resolution limit reached; remaining queued.")
        finally:
            self.processing = False

    # --- Activation API (NEW) ---
    def list_activated(self, card):
        return [ab for ab in self.card_abilities.get(card.id, []) if isinstance(ab, ActivatedAbility)]

    def can_activate(self, controller_id, card, ability: ActivatedAbility):
        # Tap check
        perm = self._find_permanent(card.id)
        if not perm:
            return False
        if ability.tap_cost and getattr(perm, 'tapped', False):
            return False
        # Mana check (ensure pool exists)
        player = self.game.players[controller_id]
        if not hasattr(player, 'mana_pool'):
            player.mana_pool = ManaPool()
        return player.mana_pool.can_pay(ability.mana_cost)

    def start_activation(self, controller_id, card, ability: ActivatedAbility):
        if not self.can_activate(controller_id, card, ability):
            if getattr(self.game,'debug_rules',False):
                print(f"[RULES] Cannot activate {card.name}")
            return False
        if ability.needs_target:
            self.pending_activation = (controller_id, card, ability)
            return True
        # No target: resolve immediately
        self._resolve_activation(controller_id, card, ability, None)
        return True

    def provide_target(self, target_card):
        if not self.pending_activation:
            return False
        controller_id, card, ability = self.pending_activation
        self.pending_activation = None
        self._resolve_activation(controller_id, card, ability, target_card)
        return True

    def _resolve_activation(self, controller_id, card, ability: ActivatedAbility, target_card):
        player = self.game.players[controller_id]
        pool = getattr(player, 'mana_pool', None)
        if not pool:
            player.mana_pool = ManaPool()
            pool = player.mana_pool
        if not pool.can_pay(ability.mana_cost):
            return
        pool.pay(ability.mana_cost)
        perm = self._find_permanent(card.id)
        if ability.tap_cost and perm and not getattr(perm, 'tapped', False):
            # reuse existing tap routine without generating mana
            self.game.tap_for_mana(controller_id, perm, produce_mana=False)
        fake = TriggeredAbility(kind='triggered',
                                raw_text=ability.raw_text,
                                trigger='ACTIVATED',
                                effect_text=ability.effect_text)
        self._enqueue(card, fake, {"event": "ACTIVATED",
                                   "target": getattr(target_card, 'name', None)})

    # --- Internal helper stubs ---
    def _find_card(self, cid):
        # Linear search across zones (prototype)
        for p in self.game.players:
            for zone in (p.battlefield, p.hand, p.graveyard, getattr(p,'exile',[])):
                for obj in zone:
                    card = getattr(obj, 'card', obj)
                    if getattr(card, 'id', None) == cid:
                        return card
        return None

    def _find_permanent(self, cid):
        for p in self.game.players:
            for perm in p.battlefield:
                if getattr(perm.card,'id',None)==cid:
                    return perm
        return None


def init_rules(game):
    engine = RulesEngine(game)
    game.rules_engine = engine
    # Register existing battlefield permanents
    for p in game.players:
        for perm in p.battlefield:
            card = getattr(perm, 'card', perm)
            if hasattr(card, 'oracle_abilities'):
                engine.register_card(card)
    return engine


def parse_and_attach(card):
    text = getattr(card, 'text', '') or ''
    abilities = parse_oracle_text(text)
    card.oracle_abilities = abilities
    return abilities
