import os, time, random
from typing import Callable, Dict, Iterable
from engine.mana import parse_mana_cost
from image_cache import ensure_card_image
from config import STARTING_LIFE
from engine.game_state import GameState, PlayerState
from ai.basic_ai import BasicAI
from engine.turn_manager import TurnManager
from engine.rules_engine import init_rules

# --- AI enhancer (moved from main) ---
def _enhance_ai_controllers(game: GameState, ai_controllers: Dict[int, BasicAI]):
    def card_total_cost(card):
        cost_dict = parse_mana_cost(getattr(card, 'mana_cost_str', ''))
        if not cost_dict:
            if isinstance(card.mana_cost, int):
                return card.mana_cost
            try:
                return int(card.mana_cost)
            except Exception:
                return 0
        return sum(cost_dict.values())

    def available_untapped_lands(player):
        lands = []
        for perm in getattr(player, 'battlefield', []):
            c = getattr(perm, 'card', perm)
            if 'Land' in c.types and not getattr(perm, 'tapped', False):
                lands.append(perm)
        return lands

    def tap_for_generic(game_ref, pid, needed):
        tapped = 0
        for perm in list(available_untapped_lands(game_ref.players[pid])):
            if tapped >= needed:
                break
            try:
                if hasattr(game_ref, 'tap_for_mana'):
                    game_ref.tap_for_mana(pid, perm)
                else:
                    perm.tapped = True
            except Exception:
                perm.tapped = True
            tapped += 1
        return tapped >= needed

    def safe_advance(game_ref):
        try:
            if hasattr(game_ref, 'turn_manager') and hasattr(game_ref.turn_manager, 'advance_phase'):
                game_ref.turn_manager.advance_phase()
            else:
                game_ref.next_phase()
        except Exception:
            pass

    def play_land_if_possible(ctrl, player):
        if getattr(ctrl, '_land_played_this_turn', False):
            return
        for card in list(player.hand):
            if 'Land' in card.types:
                try:
                    game.play_land(player.player_id, card)
                    ctrl._land_played_this_turn = True
                    return
                except Exception:
                    pass
                # fallback
                try:
                    player.hand.remove(card)
                    if hasattr(game, 'enter_battlefield'):
                        game.enter_battlefield(player.player_id, card)
                    else:
                        player.battlefield.append(type("Perm", (), {"card": card, "tapped": False})())
                    ctrl._land_played_this_turn = True
                    return
                except Exception:
                    continue

    def cast_spells(ctrl, player):
        attempts = 0
        progress = True
        while progress and attempts < 20:
            attempts += 1
            progress = False
            pool = [c for c in list(player.hand)
                    if 'Land' not in c.types and any(t in c.types for t in ('Creature','Enchantment','Artifact'))]
            if not pool: break
            pool.sort(key=card_total_cost)
            for card in pool:
                cost = card_total_cost(card)
                if cost == 0:
                    try:
                        game.cast_spell(player.player_id, card)
                        progress = True
                        break
                    except Exception:
                        continue
                lands = available_untapped_lands(player)
                if len(lands) >= cost and tap_for_generic(game, player.player_id, cost):
                    try:
                        game.cast_spell(player.player_id, card)
                        progress = True
                        break
                    except Exception:
                        pass

    def declare_attackers(ctrl, player):
        if not hasattr(game, 'combat'):
            return
        for perm in list(player.battlefield):
            card = getattr(perm, 'card', perm)
            if 'Creature' in card.types and not getattr(perm, 'tapped', False):
                try:
                    game.combat.toggle_attacker(player.player_id, perm)
                except Exception:
                    pass
        try:
            game.combat.attackers_committed()
        except Exception:
            pass
        if getattr(game, 'phase','').upper() == 'COMBAT_DECLARE':
            safe_advance(game)

    def assign_blockers(ctrl, player):
        if not hasattr(game,'combat'): return
        atk = game.combat.state.attackers
        if not atk: return
        used = set()
        for perm in list(player.battlefield):
            if len(used) >= len(atk): break
            card = getattr(perm,'card',perm)
            if 'Creature' in card.types and not getattr(perm,'tapped',False):
                attacker = atk[len(used)]
                try:
                    game.combat.toggle_blocker(player.player_id, perm, attacker)
                    used.add(perm)
                except Exception:
                    continue
        if getattr(game,'phase','').upper() == 'COMBAT_BLOCK':
            safe_advance(game)
            try:
                game.combat.assign_and_deal_damage()
            except Exception:
                pass
            for _ in range(3):
                if getattr(game,'phase','').upper() == 'MAIN2':
                    break
                safe_advance(game)

    def end_main_if_idle(ctrl, player):
        if getattr(game.stack,'can_resolve',lambda:False)():
            return
        safe_advance(game)

    for pid, ctrl in ai_controllers.items():
        def take_turn_bound(game_ref, pid=pid, controller=ctrl):
            phase = getattr(game_ref,'phase','').upper()
            player = game_ref.players[pid]
            if phase == 'UNTAP':
                controller._land_played_this_turn = False
                controller._phase_done = set()
            done = getattr(controller,'_phase_done', set())
            if phase == 'MAIN1' and phase not in done:
                play_land_if_possible(controller, player)
                cast_spells(controller, player)
                done.add(phase)
                end_main_if_idle(controller, player)
            elif phase == 'COMBAT_DECLARE' and game_ref.active_player == pid and phase not in done:
                declare_attackers(controller, player)
                done.add(phase)
            elif phase == 'COMBAT_BLOCK' and game_ref.active_player != pid and phase not in done:
                assign_blockers(controller, player)
                done.add(phase)
            elif phase == 'MAIN2' and phase not in done:
                cast_spells(controller, player)
                done.add(phase)
                end_main_if_idle(controller, player)
            controller._phase_done = done
        ctrl.take_turn = take_turn_bound


class GameController:
    """
    Decouples play logic from MainWindow UI.
    UI should:
      - call enter_match() when user starts game
      - call tick(refresh_callable) from a QTimer
      - delegate key actions (advance phase, space key, etc.)
    """
    def __init__(self, game: GameState, ai_ids: Iterable[int], *, logging_enabled: bool):
        self.game = game
        if not hasattr(self.game, 'turn_manager'):
            try:
                self.game.turn_manager = TurnManager(self.game)
            except Exception:
                pass
        self.logging_enabled = logging_enabled
        self.ai_controllers: Dict[int, BasicAI] = {pid: BasicAI(pid=pid) for pid in ai_ids}
        _enhance_ai_controllers(self.game, self.ai_controllers)

        # Flow state
        self.in_game = False
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        self._game_flow_started = False

        # Tick pacing
        self.auto_step_cooldown_ms = 1000
        self._last_auto_step_s = 0.0

    # ---------- Logging ----------
    def log_phase(self):
        if not self.logging_enabled: return
        try:
            ap = self.game.active_player
            nm = self.game.players[ap].name
            print(f"[PHASE] Active={nm} Phase={getattr(self.game,'phase','?')}")
        except Exception:
            pass

    # ---------- Game start ----------
    def enter_match(self):
        self.in_game = True
        self._begin_game_flow()

    def _begin_game_flow(self):
        if self._game_flow_started: return
        self._game_flow_started = True
        if len(self.game.players) > 1:
            # UI should prompt roll; controller waits
            return
        # single player immediate start
        if not self.opening_hands_drawn:
            self.draw_opening_hands()
        self.first_player_decided = True
        if self.logging_enabled:
            print("[START] Single-player game begun (no roll).")

    # ---------- Roll / mulligans ----------
    def perform_first_player_roll(self):
        """
        Pure logic: returns (winner_id, rolls_dict) after resolving ties internally.
        Caller (UI) then decides keep/pass and sets starter with set_starter(starter_id).
        """
        while True:
            rolls = {pl.player_id: random.randint(1,20) for pl in self.game.players}
            hi = max(rolls.values())
            winners = [pid for pid,v in rolls.items() if v==hi]
            if self.logging_enabled:
                print("[ROLL] " + ", ".join(f"{self.game.players[p].name}:{rolls[p]}" for p in rolls))
            if len(winners)==1:
                return winners[0], rolls
            if self.logging_enabled:
                print("[ROLL][TIE] Re-rolling...")

    def set_starter(self, starter_pid: int):
        self.game.active_player = starter_pid
        self.skip_first_draw_player = starter_pid
        self.skip_first_draw_used = False
        self.first_player_decided = True
        # Opening hand draw after small delay (UI can call draw_opening_hands immediately or via QTimer)
        self.draw_opening_hands()

    def draw_opening_hands(self):
        if self.opening_hands_drawn: return
        for pl in self.game.players:
            pl.hand = getattr(pl,'hand', [])
            while len(pl.hand) < 7 and pl.library:
                pl.hand.append(pl.library.pop(0))
        self.opening_hands_drawn = True
        if self.logging_enabled:
            print("[START] Opening hands drawn.")
        self.log_phase()

    # ---------- Phase control ----------
    def advance_phase(self):
        try:
            if hasattr(self.game,'turn_manager') and hasattr(self.game.turn_manager,'advance_phase'):
                self.game.turn_manager.advance_phase()
                return
        except Exception:
            pass
        try:
            self.game.next_phase()
        except Exception:
            pass

    # ---------- AI tick ----------
    def tick(self, refresh_callable: Callable[[], None] | None = None):
        if not (self.in_game and self.first_player_decided):
            return
        now = time.monotonic()
        if (now - self._last_auto_step_s) < (self.auto_step_cooldown_ms/1000):
            return
        self._last_auto_step_s = now

        # First draw skip
        try:
            if (getattr(self.game,'phase','').upper() == 'DRAW' and
                self.game.active_player == self.skip_first_draw_player and
                not self.skip_first_draw_used):
                pl = self.game.players[self.skip_first_draw_player]
                if pl.hand:
                    # naive "undo" last draw
                    put_back = pl.hand.pop()
                    pl.library.insert(0, put_back)
                    if self.logging_enabled:
                        print(f"[DRAW][RULE] Skipped first draw for {pl.name}.")
                self.skip_first_draw_used = True
        except Exception:
            pass

        # AI
        try:
            ap = self.game.active_player
            if ap in self.ai_controllers:
                self.ai_controllers[ap].take_turn(self.game)
        except Exception as ex:
            if self.logging_enabled:
                print(f"[AI][ERR] {ex}")

        # UI refresh
        if refresh_callable:
            try:
                refresh_callable()
            except Exception:
                pass

    # ---------- Deck / Opponent helpers ----------
    def ensure_ai_opponent(self, build_game_fn):
        """
        build_game_fn: callable(specs)->(new_game, ai_ids) (delegates to existing new_game)
        """
        if len(self.game.players) != 1:
            return False
        p0 = self.game.players[0]
        p0_path = getattr(p0,'source_path', None)
        decks_dir = os.path.join('data','decks')
        deck_files = sorted([os.path.join(decks_dir,f) for f in os.listdir(decks_dir)
                             if f.lower().endswith('.txt')])
        ai_path = None
        for cand in deck_files:
            if p0_path and os.path.abspath(cand) == os.path.abspath(p0_path):
                continue
            ai_path = cand
            break
        if not ai_path:
            ai_path = os.path.join(decks_dir,'missing_ai_deck.txt')
        specs = [
            (p0.name, p0_path, False),
            ("AI", ai_path, True)
        ]
        try:
            new_state, ai_ids = build_game_fn(specs, ai_enabled=True)
        except Exception as ex:
            if self.logging_enabled:
                print(f"[AI-AUTO][ERR] {ex}")
            return False
        self.game = new_state
        self.ai_controllers = {pid: BasicAI(pid=pid) for pid in ai_ids}
        _enhance_ai_controllers(self.game, self.ai_controllers)
        # reset flow
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        if self.logging_enabled:
            print("[AI-AUTO] Added AI opponent automatically.")
        return True

    def reload_player0(self, new_game_fn, path: str):
        """
        Rebuild game preserving other players' deck paths where possible.
        new_game_fn(specs, ai_enabled)->(game, ai_ids)
        """
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        specs = []
        for p in self.game.players:
            deck_path = path if p.player_id == 0 else getattr(p,'source_path', None)
            specs.append((p.name, deck_path, p.player_id in self.ai_controllers))
        new_state, ai_ids = new_game_fn(specs, ai_enabled=True)
        self.game = new_state
        self.ai_controllers = {pid: BasicAI(pid=pid) for pid in ai_ids}
        _enhance_ai_controllers(self.game, self.ai_controllers)
        self.first_player_decided = False
        self.opening_hands_drawn = False
        self.skip_first_draw_player = None
        self.skip_first_draw_used = False
        return self.game
