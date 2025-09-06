from dataclasses import dataclass

@dataclass
class Ability:
    kind: str          # 'triggered' | 'static'
    raw_text: str

@dataclass
class TriggeredAbility(Ability):
    trigger: str       # 'ETB' | 'ATTACK' | 'CREATURE_ETB_YOU'
    effect_text: str

@dataclass
class StaticKeywordAbility(Ability):
    keyword: str       # e.g. 'Flying','Trample','Deathtouch'

@dataclass
class ActivatedAbility(Ability):
    raw_cost: str              # original cost string before ':'
    mana_cost: dict            # parsed mana symbols dict
    tap_cost: bool             # requires {T}
    effect_text: str
    needs_target: bool
    target_hint: str | None    # e.g. 'creature', 'player', None

@dataclass
class StaticBuffAbility(Ability):
    other_only: bool
    power: int
    toughness: int

@dataclass
class TriggerEvent:
    source_card_id: str
    ability: Ability
    context: dict  # event related data (e.g. {'zone_from':'BATTLEFIELD'})

# NOTE: TriggeredAbility.trigger may now also be 'DEATH'
