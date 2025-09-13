from dataclasses import dataclass, field
from typing import Dict, List
from .keywords import card_keywords

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
        """Toggle a creature as an attacker following MTG Comprehensive Rules 508.1"""
        if self.game.active_player != player_id:
            return  # Only active player can declare attackers
        
        if 'Creature' not in perm.card.types:
            return  # Only creatures can attack (CR 508.1a)
        
        if perm.tapped:
            return  # Tapped creatures can't attack (CR 508.1c)
        
        # Check for summoning sickness (CR 302.6 and CR 508.1c)
        if perm.summoning_sick:
            # Check if creature has haste (CR 508.1c)
            creature_keywords = card_keywords(perm.card)
            if 'haste' not in creature_keywords:
                return  # Creature with summoning sickness can't attack unless it has haste
        
        # Check for other attack restrictions
        if not self._can_attack(perm):
            return
        
        # Toggle attacker status
        if perm in self.state.attackers:
            self.state.attackers.remove(perm)
        else:
            self.state.attackers.append(perm)
            
            # Emit attack event for triggered abilities
            try:
                from engine.ability_engine import emit_game_event, TriggerCondition
                emit_game_event(TriggerCondition.ATTACKS, 
                              source=perm.card, controller=player_id)
            except ImportError:
                pass

    def attackers_committed(self):
        self.state.committed = True

    # ---- Block assignment (defending player) ----
    def _can_attack(self, perm) -> bool:
        """Check if a creature can attack according to MTG rules."""
        # Basic checks already done in toggle_attacker
        # This is for additional attack restrictions that could be added later
        # For example: "Creatures you control can't attack" effects
        return True
    
    def _can_block(self, blocker_perm, attacker_perm) -> bool:
        """Check if a blocker can block an attacker according to MTG CR 509.1"""
        atk_kws = card_keywords(attacker_perm.card)
        blk_kws = card_keywords(blocker_perm.card)
        
        # CR 509.1b: Creature with flying can only be blocked by creatures with flying or reach
        if 'flying' in atk_kws and not (('flying' in blk_kws) or ('reach' in blk_kws)):
            return False
        
        # CR 509.1c: Landwalk abilities (simplified - would need to check land types)
        # This would require more complex land type checking
        
        # CR 509.1d: Creature with fear can only be blocked by artifact or black creatures
        if 'fear' in atk_kws:
            if 'Artifact' not in blocker_perm.card.types and 'Black' not in getattr(blocker_perm.card, 'colors', []):
                return False
        
        # CR 509.1e: Creature with intimidate can only be blocked by artifact creatures or creatures that share a color
        if 'intimidate' in atk_kws:
            blocker_colors = getattr(blocker_perm.card, 'colors', [])
            attacker_colors = getattr(attacker_perm.card, 'colors', [])
            if 'Artifact' not in blocker_perm.card.types and not any(c in blocker_colors for c in attacker_colors):
                return False
        
        # Additional blocking restrictions can be added here
        return True
    
    def toggle_blocker(self, defending_player_id: int, blocker_perm, attacker_perm):
        """Toggle a creature as a blocker following MTG Comprehensive Rules 509.1"""
        if self.state.committed is False:
            return  # Can only declare blockers after attackers are committed
        
        if self.game.active_player == defending_player_id:
            return  # Defending player (not active player) declares blockers
        
        if 'Creature' not in blocker_perm.card.types:
            return  # Only creatures can block (CR 509.1a)
        
        if blocker_perm.tapped:
            return  # Tapped creatures can't block (CR 509.1a)
        
        if attacker_perm not in self.state.attackers:
            return  # Can only block actual attackers
        
        # Check if this blocker can legally block this attacker
        if not self._can_block(blocker_perm, attacker_perm):
            return
        
        # Remove blocker from any other attacker it might be blocking (one blocker per attacker in simplified model)
        for lst in self.state.blockers.values():
            if blocker_perm in lst:
                lst.remove(blocker_perm)
        
        aid = attacker_perm.card.id
        self.state.blockers.setdefault(aid, [])
        
        # Toggle blocker assignment
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
            
            # Emit death event for triggered abilities
            try:
                from engine.ability_engine import emit_game_event, TriggerCondition
                emit_game_event(TriggerCondition.DIES, 
                              affected=perm.card, controller=perm.card.controller_id)
            except ImportError:
                pass
            
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
