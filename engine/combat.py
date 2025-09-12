from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .keywords import card_keywords  # NEW

@dataclass
class CombatState:
    attackers: List[object] = field(default_factory=list)              # list of attacking permanents
    blockers: Dict[str, List[object]] = field(default_factory=dict)    # attacker card.id -> list of blockers
    committed: bool = False

class CombatManager:
    def __init__(self, game):
        self.game = game
        self.state = CombatState()

    # ---- Declaration phase ----
    def toggle_attacker(self, player_id: int, perm):
        if self.game.active_player != player_id:
            return
        if 'Creature' not in perm.card.types:
            return
        if perm.tapped:  # simplistic summoning sickness / tapped check
            return
        # Haste handling skipped (no summoning sickness model). Accept as-is.
        if perm in self.state.attackers:
            self.state.attackers.remove(perm)
        else:
            self.state.attackers.append(perm)

    def attackers_committed(self):
        self.state.committed = True

    # ---- Block assignment (defending player) ----
    def toggle_blocker(self, defending_player_id: int, blocker_perm, attacker_perm):
        if self.state.committed is False:
            return
        if 'Creature' not in blocker_perm.card.types:
            return
        if blocker_perm.tapped:
            return
        # Flying restriction (attacker with flying requires blocker with flying or reach)
        atk_kws = card_keywords(attacker_perm.card)
        blk_kws = card_keywords(blocker_perm.card)
        if 'flying' in atk_kws and not (('flying' in blk_kws) or ('reach' in blk_kws)):
            return
        # Menace (simplified): needs at least 2 different blockers -> allow selection but enforce on commit
        # (Commit enforcement handled when assigning damage; if <2 blockers on menace attacker treat as unblocked)
        # ensure blocker not already blocking another attacker (simplified single assignment)
        for lst in self.state.blockers.values():
            if blocker_perm in lst:
                lst.remove(blocker_perm)
        aid = attacker_perm.card.id
        self.state.blockers.setdefault(aid, [])
        if attacker_perm not in self.state.attackers:
            return
        if blocker_perm in self.state.blockers[aid]:
            self.state.blockers[aid].remove(blocker_perm)
        else:
            self.state.blockers[aid].append(blocker_perm)

    # ---- Damage ----
    def assign_and_deal_damage(self):
        # Unblocked -> player damage
        for atk in list(self.state.attackers):
            atk_card = atk.card
            atk_power = _safe_int(getattr(atk_card, 'eff_power', atk_card.power))
            if atk_power <= 0:
                continue
            atk_kws = card_keywords(atk_card)
            block_list = self.state.blockers.get(atk_card.id, [])
            # Menace enforcement: if attacker has menace and <2 blockers -> treat as unblocked
            if 'menace' in atk_kws and len(block_list) < 2:
                block_list = []
            if not block_list:
                defending_id = _next_player(self.game, self.game.active_player)
                self._deal_damage_to_player(atk, defending_id, atk_power, lifelink=('lifelink' in atk_kws))
            else:
                first_blocker = block_list[0]
                lethal_needed = 1 if 'deathtouch' in atk_kws else _safe_int(getattr(first_blocker.card,'eff_toughness', first_blocker.card.toughness))
                assign_to_blocker = min(atk_power, lethal_needed)
                spill = 0
                if 'trample' in atk_kws:
                    spill = max(0, atk_power - lethal_needed)
                # Damage to blocker
                _mark_damage(first_blocker, assign_to_blocker)
                if 'lifelink' in atk_kws:
                    self._gain_life(atk_card.controller_id, assign_to_blocker)
                if spill > 0:
                    defending_id = _next_player(self.game, self.game.active_player)
                    self._deal_damage_to_player(atk, defending_id, spill, lifelink=('lifelink' in atk_kws))
                # Blockers deal damage back
                total_block_power = 0
                for b in block_list:
                    bp = _safe_int(getattr(b.card,'eff_power', b.card.power))
                    if bp > 0:
                        total_block_power += bp
                        if 'lifelink' in card_keywords(b.card):
                            self._gain_life(b.card.controller_id, bp)
                        if 'deathtouch' in card_keywords(b.card):
                            # Mark lethal
                            _mark_damage(atk, max(_safe_int(getattr(atk_card,'eff_toughness', atk_card.toughness)),1))
                _mark_damage(atk, total_block_power)
        self._cleanup_lethal()
        self.state = CombatState()

    def _deal_damage_to_player(self, attacking_perm, player_id, amount, lifelink=False):
        self.game.players[player_id].life -= amount
        if lifelink:
            self._gain_life(attacking_perm.card.controller_id, amount)

    def _gain_life(self, player_id, amount):
        self.game.players[player_id].life += amount

    def _cleanup_lethal(self):
        deaths = []
        for p in self.game.players:
            for perm in list(p.battlefield):
                dmg = getattr(perm, 'damage_marked', 0)
                tou = _safe_int(perm.card.toughness)
                if tou > 0 and dmg >= tou:
                    deaths.append(perm)
        for perm in deaths:
            owner = self.game.players[perm.card.owner_id]
            if perm in owner.battlefield:
                owner.battlefield.remove(perm)
            owner.graveyard.append(perm.card)
            if hasattr(self.game, 'rules_engine'):
                self.game.rules_engine.on_card_dies(perm.card)

def _mark_damage(perm, amount: int):
    if amount <= 0:
        return
    cur = getattr(perm, 'damage_marked', 0)
    setattr(perm, 'damage_marked', cur + amount)

def _safe_int(v):
    try:
        return int(v)
    except Exception:
        return 0

def _next_player(game, pid):
    return (pid + 1) % len(game.players)

# ---- Integration helper ----
def attach_combat(game):
    if hasattr(game, 'combat'):
        return game.combat
    game.combat = CombatManager(game)
    return game.combat
