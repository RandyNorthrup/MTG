from typing import Dict, List, Any, Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from .game_state import GameState
from .keywords import StaticBuffAbility

class ContinuousEffect:
    def __init__(self, layer: int, fn: Callable[['GameState'], None], duration: str | None = None):
        self.layer = layer
        self.fn = fn
        self.duration = duration
        self.active = True

class ContinuousEngine:
    """
    Applies continuous effects, including static buffs, player counters, statuses, and global effects.
    Recompute after zone changes or at periodic ticks.
    Also manages dynamic continuous effects (layer system).
    """
    def __init__(self, game):
        self.game = game
        self._global_effects: List[Any] = []  # List of global continuous effects
        self._player_status: Dict[int, Dict[str, Any]] = {}  # player_id -> status dict
        self.effects: List[ContinuousEffect] = []  # dynamic continuous effects (layer system)

    def add_effect(self, eff: ContinuousEffect):
        self.effects.append(eff)

    def prune_eot(self):
        self.effects = [e for e in self.effects if not (e.duration == 'eot')]

    def recompute(self):
        # --- Clear previous effective stats and statuses ---
        for p in self.game.players:
            for perm in p.battlefield:
                card = getattr(perm, 'card', perm)
                for attr in ('eff_power', 'eff_toughness', 'eff_keywords', 'eff_types'):
                    if hasattr(card, attr):
                        delattr(card, attr)
            # Reset player statuses/counters
            self._player_status[p.player_id] = {}

        # --- Apply static buffs and continuous effects ---
        for p in self.game.players:
            for perm in p.battlefield:
                card = perm.card
                # StaticBuffAbility and other static abilities
                for ab in getattr(card, 'oracle_abilities', []) or []:
                    self._apply_static_effect(card, ab)

        # --- Apply global effects (e.g., from emblems, enchantments, etc.) ---
        for effect in self._global_effects:
            self._apply_global_effect(effect)

        # --- Player counters/statuses (e.g., poison, monarch, initiative, etc.) ---
        for p in self.game.players:
            self._apply_player_status(p)

        # --- Apply dynamic continuous effects (layer system) ---
        for eff in sorted([e for e in self.effects if e.active], key=lambda e: e.layer):
            try:
                eff.fn(self.game)
            except Exception as ex:
                # Continuous effect error (debug print removed)

    def _apply_static_effect(self, source_card, ability):
        # StaticBuffAbility: power/toughness buffs, keyword grants, etc.
        if isinstance(ability, StaticBuffAbility):
            controller = source_card.controller_id
            for p in self.game.players:
                for perm in p.battlefield:
                    c = perm.card
                    if c.controller_id != controller:
                        continue
                    if 'Creature' not in c.types:
                        continue
                    if ability.other_only and c.id == source_card.id:
                        continue
                    base_p = c.power if c.power is not None else 0
                    base_t = c.toughness if c.toughness is not None else 0
                    eff_p = getattr(c, 'eff_power', base_p)
                    eff_t = getattr(c, 'eff_toughness', base_t)
                    setattr(c, 'eff_power', eff_p + ability.power)
                    setattr(c, 'eff_toughness', eff_t + ability.toughness)
                    # Keywords (e.g., flying, vigilance)
                    if getattr(ability, 'keywords', None):
                        kws = set(getattr(c, 'eff_keywords', set()))
                        kws.update(ability.keywords)
                        setattr(c, 'eff_keywords', kws)
        # Extend: handle other static ability types here (e.g., type-changing, color-changing, etc.)

    def _apply_global_effect(self, effect):
        # Placeholder for global continuous effects (e.g., "Creatures can't attack", "Players can't gain life")
        pass

    def _apply_player_status(self, player):
        # Example: poison counters, monarch, initiative, emblem effects, etc.
        pass

    def add_global_effect(self, effect):
        """Register a global continuous effect (e.g., from an emblem or enchantment)."""
        self._global_effects.append(effect)

    def remove_global_effect(self, effect):
        if effect in self._global_effects:
            self._global_effects.remove(effect)

    def get_player_status(self, player_id: int) -> Dict[str, Any]:
        """Return the status/counter dict for a player."""
        return self._player_status.get(player_id, {})

    def set_player_status(self, player_id: int, key: str, value: Any):
        if player_id not in self._player_status:
            self._player_status[player_id] = {}
        self._player_status[player_id][key] = value

    def clear_player_status(self, player_id: int, key: str):
        if player_id in self._player_status and key in self._player_status[player_id]:
            del self._player_status[player_id][key]

    def get_all_statuses(self) -> Dict[int, Dict[str, Any]]:
        """Return all player statuses."""
        return self._player_status

    # --- Advanced: Layered effect hooks (for future extensibility) ---
    def apply_layered_effects(self):
        """
        Placeholder for full layer system (type, color, ability, p/t, etc.).
        Call this after recompute() if you implement full layer logic.
        """
        pass

def attach_continuous(game):
    if hasattr(game, 'continuous'):
        return game.continuous
    game.continuous = ContinuousEngine(game)
    game.continuous.recompute()
    return game.continuous
