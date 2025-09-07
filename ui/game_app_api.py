import os
import random
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox
from engine.game_controller import GameController
from engine.game_state import GameState
from typing import Optional

class GameAppAPI:
    """Facade for gameplay, UI, and engine delegation."""

    def __init__(self, main_window, game: GameState, ai_ids, args, new_game_factory):
        self.w = main_window
        self.args = args
        self._new_game_factory = new_game_factory
        self.controller = GameController(game, ai_ids, logging_enabled=not (args and args.no_log))
        self.game = self.controller.game
        self._opening_sequence_done = False
        self.pending_match_active = False  # <-- Ensure this attribute always exists
        self._debug_win = None
        self.board_window = None

    # --- Gameplay/Turn/Phase mechanics: delegate to engine ---
    def toggle_attacker(self, card):
        self.controller.toggle_attacker(card)

    def has_attackers(self):
        return self.controller.has_attackers()

    def commit_attackers(self):
        self.controller.commit_attackers()

    def handle_blocker_click(self, card):
        self.controller.handle_blocker_click(card)

    def commit_blockers(self):
        self.controller.commit_blockers()

    def advance_to_phase(self, phase_name):
        self.controller.advance_to_phase(phase_name)

    def play_land(self, card):
        self.controller.play_land(card)

    def cast_spell(self, card):
        self.controller.cast_spell(card)

    # --- Game Window Management (ADDED) ---------------------------------
    def open_game_window(self):
        """Create or focus the dedicated board window."""
        if self.board_window and self.board_window.isVisible():
            self.board_window.raise_()
            self.board_window.activateWindow()
            return
        try:
            from ui.game_window import GameWindow
        except Exception as ex:
            self._log(f"[BOARD] Failed to open game window: {ex}")
            return
        self.board_window = GameWindow(self)
        self.board_window.show()

    def _ensure_game_window(self):
        """Guarantee a visible board window before interactive dialogs."""
        if not self.board_window or not self.board_window.isVisible():
            self.open_game_window()

    # Settings
    def open_settings(self):
        if hasattr(self.w, "open_settings_window"):
            self.w.open_settings_window()

    # Accessors
    def get_game(self): return self.game
    def get_controller(self): return self.controller

    # Lobby / match flow
    def ensure_ai_opponent(self):
        self.controller.ensure_ai_opponent(self._new_game_factory)

    def create_pending_match(self):
        if self.pending_match_active:
            return
        player_deck = getattr(self.game.players[0], 'source_path', None)
        specs = [(self.game.players[0].name, player_deck, False)]
        self._rebuild_game_with_specs(specs)
        self.pending_match_active = True
        self._sync_lobby(True)
        self._log("[QUEUE] Pending match created. Awaiting players (max 4).")

    def add_ai_player_pending(self):
        if not self.pending_match_active or len(self.game.players) >= 4:
            return
        used_paths = {getattr(p, 'source_path', None) for p in self.game.players}
        decks_dir = os.path.join('data', 'decks')
        try:
            deck_files = [os.path.join(decks_dir, f)
                          for f in os.listdir(decks_dir) if f.lower().endswith('.txt')]
        except Exception:
            deck_files = []
        ai_path = None
        for pth in sorted(deck_files):
            if pth not in used_paths:
                ai_path = pth
                break
        if not ai_path:
            ai_path = os.path.join(decks_dir, 'missing_ai_deck.txt')
        specs = []
        for pl in self.game.players:
            is_ai = pl.player_id in self.controller.ai_controllers
            specs.append((pl.name, getattr(pl, 'source_path', None), is_ai))
        ai_name = f"AI{len(specs)}"
        specs.append((ai_name, ai_path, True))
        self._rebuild_game_with_specs(specs)
        self._sync_lobby(True)
        self._log(f"[QUEUE] Added AI player '{ai_name}' ({len(self.game.players)}/4).")

    def cancel_pending_match(self):
        if not self.pending_match_active:
            return
        self.pending_match_active = False
        specs = [(self.game.players[0].name,
                  getattr(self.game.players[0], 'source_path', None), False)]
        self._rebuild_game_with_specs(specs)
        self._sync_lobby(False)
        self._log("[QUEUE] Pending match canceled.")

    def start_pending_match(self):
        if not self.pending_match_active:
            return
        self.pending_match_active = False
        if len(self.game.players) > 1:
            QTimer.singleShot(50, self.prompt_first_player_roll)
        else:
            self.start_game_without_roll()
        self._sync_lobby(False)
        self._log(f"[QUEUE] Match initialized with {len(self.game.players)} player(s).")

    def enter_match_now(self):
        if self.pending_match_active:
            return
        self.ensure_ai_opponent()
        if len(self.game.players) > 1:
            QTimer.singleShot(50, self.prompt_first_player_roll)
        else:
            self.start_game_without_roll()
        self._sync_lobby(False)
        self._log("[LOBBY] Local match prepared.")

    # Start / mulligans
    def finalize_start_after_roll(self, starter_index: int):
        self._ensure_game_window()                     # ADDED
        if not self.controller.in_game:
            self.controller.enter_match()
        self.controller.set_starter(starter_index)
        self._handle_opening_hands_and_mulligans()
        self.controller.log_phase()
        self._phase_ui()

    def start_game_without_roll(self):
        self._ensure_game_window()                     # ADDED
        if len(self.game.players) == 1:
            self.ensure_ai_opponent()
            if len(self.game.players) > 1:
                QTimer.singleShot(50, self.prompt_first_player_roll)
                return
        if not self.controller.in_game:
            self.controller.enter_match()
        self.controller.set_starter(0)
        self._handle_opening_hands_and_mulligans()
        self.controller.log_phase()
        self._phase_ui()

    def prompt_first_player_roll(self):
        if self.controller.first_player_decided or len(self.game.players) < 2:
            return
        self._ensure_game_window()    # (if present in your version) safe call; ignore if method absent
        host = getattr(self, 'board_window', None) or self.w
        box = QMessageBox(host)
        box.setWindowTitle("Determine First Player")
        box.setText("Roll to determine who goes first.")
        roll_btn = box.addButton("Roll", QMessageBox.AcceptRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not roll_btn:
            return
        winner, _rolls = self.controller.perform_first_player_roll()
        wn = self.game.players[winner].name
        # If AI (non-player0) wins the roll, it always auto-passes (player 0 goes first).
        if winner != 0 and winner in getattr(self.controller, 'ai_controllers', {}):
            starter = (winner + 1) % len(self.game.players)
            self._log(f"[ROLL] {wn} (AI) wins roll, auto-passes. {self.game.players[starter].name} starts.")
            self.finalize_start_after_roll(starter)
            return
        # Human (player 0) wins: offer choice to go first or pass.
        if winner == 0:
            choose = QMessageBox(host)
            choose.setWindowTitle("Roll Result")
            choose.setText(f"You win the roll.\nChoose turn order.")
            go_first = choose.addButton("Go First", QMessageBox.AcceptRole)
            pass_btn = choose.addButton("Pass", QMessageBox.DestructiveRole)
            choose.exec()
            starter = (winner + 1) % len(self.game.players) if choose.clickedButton() is pass_btn else winner
            self._log(f"[ROLL] Player wins roll and chooses {'to pass' if starter != winner else 'to go first'}.")
            self.finalize_start_after_roll(starter)
            return
        # Non-player0 human winner (if supported): that winner chooses; losing player0 gets no dialog.
        choose = QMessageBox(host)
        choose.setWindowTitle("Roll Result")
        choose.setText(f"{wn} wins the roll.\nWinner chooses turn order.")
        go_first = choose.addButton("Go First", QMessageBox.AcceptRole)
        pass_btn = choose.addButton("Pass", QMessageBox.DestructiveRole)
        choose.exec()
        starter = (winner + 1) % len(self.game.players) if choose.clickedButton() is pass_btn else winner
        self._log(f"[ROLL] {wn} wins roll and chooses {'to pass' if starter != winner else 'to go first'}.")
        self.finalize_start_after_roll(starter)

    # Turn / phases
    def advance_phase(self):  # already mapped by earlier changes
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        self.controller.advance_step()   # ensure strict step advance
        self._phase_ui()

    def ai_tick(self):
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        play_area = getattr(self.board_window, 'play_area', None)
        self.controller.tick(lambda: (
            play_area and getattr(play_area, 'refresh_board', lambda: None)()
        ))
        self._phase_ui()

    # Player utilities
    def reload_player0(self, deck_path: str):
        if not deck_path:
            return
        if not os.path.exists(deck_path):
            QMessageBox.warning(self.w, "Reload", f"{deck_path} not found.")
            return
        try:
            self.controller.reload_player0(self._new_game_factory, deck_path)
        except Exception as ex:
            QMessageBox.critical(self.w, "Reload Failed", str(ex))
            return
        self.game = self.controller.game
        if hasattr(self.w, 'play_area') and hasattr(self.w.play_area, 'set_game'):
            self.w.play_area.set_game(self.game)
        self._log("[RELOAD] Player 0 deck reloaded.")
        if hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()
        self._sync_lobby(self.pending_match_active)

    # Debug
    def toggle_debug_window(self):
        host = self.board_window or self.w
        try:
            from tools.game_debug_tests import GameDebugWindow
        except Exception as ex:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(host, "Debug Window", f"Unavailable: {ex}")
            return
        if self._debug_win and self._debug_win.isVisible():
            self._debug_win.close()
            self._debug_win = None
        else:
            play_area = getattr(self.board_window, 'play_area', None)
            # CHANGED: pass main_window explicitly (self.w) plus board_window
            self._debug_win = GameDebugWindow(self.game, play_area, self.w, board_window=self.board_window)
            self._debug_win.show()

    # Keys
    def handle_key(self, key):
        from PySide6.QtCore import Qt
        if key == Qt.Key_Space:
            if self.controller.in_game and self.controller.first_player_decided:
                if hasattr(self.game, 'stack') and self.game.stack.can_resolve():
                    self.game.stack.resolve_top(self.game)
                else:
                    self.advance_phase()
                    self.controller.log_phase()
        elif key == Qt.Key_L:
            self.controller.logging_enabled = not self.controller.logging_enabled
            self.w.logging_enabled = self.controller.logging_enabled
            print(f"[LOG] Phase logging {'enabled' if self.controller.logging_enabled else 'disabled'}")
        elif key == Qt.Key_F9:
            self.toggle_debug_window()
        elif key == Qt.Key_F5 and hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()

    # Shutdown
    def shutdown(self):
        try:
            if self._debug_win and self._debug_win.isVisible():
                self._debug_win.close()
        except Exception:
            pass
        if self.board_window:
            try:
                self.board_window.close()
            except Exception:
                pass

    # Internal helpers
    def _rebuild_game_with_specs(self, specs):
        game, ai_ids = self._new_game_factory(specs, ai_enabled=True)
        logging_flag = self.controller.logging_enabled
        self.controller = GameController(game, ai_ids, logging_enabled=logging_flag)
        self.game = self.controller.game
        self.w.logging_enabled = self.controller.logging_enabled
        if hasattr(self.w, 'play_area') and hasattr(self.w.play_area, 'set_game'):
            self.w.play_area.set_game(self.game)
        if hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()
        self._phase_ui()
        if len(game.players) == 1:
            self.ensure_ai_opponent()

    def _handle_opening_hands_and_mulligans(self):
        if self._opening_sequence_done or not getattr(self.game, '_opening_hands_deferred', False):
            return
        for pl in self.game.players:
            if not hasattr(pl, 'hand'):
                pl.hand = []
            if not pl.hand:
                for _ in range(7):
                    if pl.library:
                        pl.hand.append(pl.library.pop(0))
            pl.mulligans_taken = 0
        is_multi = len(self.game.players) > 2
        human = self.game.players[0] if self.game.players else None
        if human:
            self._ensure_game_window()                 # ADDED
            host = self.board_window or self.w         # ADDED
            while True:
                hand_names = ", ".join(c.name for c in human.hand)
                box = QMessageBox(host)            # CHANGED parent
                box.setWindowTitle("Opening Hand")
                box.setText(
                    f"Opening Hand ({len(human.hand)}):\n{hand_names or '(empty)'}\n\n"
                    "Mulligan? (London mulligan: draw 7; bottom cards = mulligans taken"
                    f"{' (first free in multiplayer)' if is_multi else ''})"
                )
                mull_btn = box.addButton("Mulligan", QMessageBox.DestructiveRole)
                keep_btn = box.addButton("Keep", QMessageBox.AcceptRole)
                box.exec()
                if box.clickedButton() is keep_btn:
                    break
                human.mulligans_taken += 1
                returned = human.hand[:]
                human.hand.clear()
                human.library = returned + human.library
                random.shuffle(human.library)
                for _ in range(7):
                    if human.library:
                        human.hand.append(human.library.pop(0))
                effective = human.mulligans_taken - (1 if is_multi and human.mulligans_taken == 1 else 0)
                if effective > 0 and len(human.hand) > effective:
                    idxs = random.sample(range(len(human.hand)), effective)
                    idxs.sort(reverse=True)
                    moving = [human.hand.pop(i) for i in idxs]
                    human.library.extend(moving)
        self._opening_sequence_done = True
        setattr(self.game, '_opening_hands_deferred', False)

    def _phase_ui(self):
        """
        Lightweight UI sync: any object with 'phase_lbl' or 'phase_label'
        will be updated directly; no legacy phase modules used.
        """
        host = getattr(self, 'board_window', None) or self.w
        txt = f"{self.controller.phase}"
        if hasattr(self.controller, 'step') and self.controller.step != self.controller.phase:
            txt = f"{self.controller.phase} / {self.controller.step}"
        ap_name = getattr(self.controller, 'active_player_name', "—")
        txt = f"{txt}  Active: {ap_name}"
        for attr in ('phase_lbl', 'phase_label'):
            lbl = getattr(host, attr, None)
            if lbl:
                try:
                    lbl.setText(txt)
                except Exception:
                    pass

    def _sync_lobby(self, active: bool):
        if hasattr(self.w, 'lobby_widget') and hasattr(self.w.lobby_widget, 'sync_pending_controls'):
            self.w.lobby_widget.sync_pending_controls(active)

    def _log(self, msg: str):
        if self.controller.logging_enabled:
            print(msg)
            self.w._update_phase_ui()

    def _sync_lobby(self, active: bool):
        if hasattr(self.w, 'lobby_widget') and hasattr(self.w.lobby_widget, 'sync_pending_controls'):
            self.w.lobby_widget.sync_pending_controls(active)

    def _log(self, msg: str):
        if self.controller.logging_enabled:
            print(msg)
            pass
        self._debug_win = None
        try:
            if self._game_window:
                self._game_window.close()
        except Exception:
            pass
        self._game_window = None

    # --- Keyboard -----------------------------------------------------------
    def handle_key(self, key):
        from PySide6.QtCore import Qt
        if key == Qt.Key_Space:
            if self.controller.in_game and self.controller.first_player_decided:
                if hasattr(self.game, 'stack') and self.game.stack.can_resolve():
                    self.game.stack.resolve_top(self.game)
                else:
                    self.advance_phase()
        elif key == Qt.Key_L:
            self.controller.logging_enabled = not self.controller.logging_enabled
            self.w.logging_enabled = self.controller.logging_enabled
            print(f"[LOG] Phase logging {'enabled' if self.controller.logging_enabled else 'disabled'}")
        elif key == Qt.Key_F9:
            self.toggle_debug_window()
        elif key == Qt.Key_F5 and hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()

    # --- UI sync / logging helpers -----------------------------------------
    def _phase_ui(self):
        if hasattr(self.w, '_update_phase_ui'):
            self.w._update_phase_ui()

    def _sync_lobby(self, active: bool):
        if hasattr(self.w, 'lobby_widget') and hasattr(self.w.lobby_widget, 'sync_pending_controls'):
            self.w.lobby_widget.sync_pending_controls(active)

    def _log(self, msg):
        if self.controller.logging_enabled:
            print(msg)

    def open_settings(self):
        """Open (or lazily create) the Settings tab via SettingsTabManager."""
        if not getattr(self.w, 'settings_manager', None):
            from ui.settings_tab import SettingsTabManager
            self.w.settings_manager = SettingsTabManager(self)
        self.w.settings_manager.open()
        self.w.settings_manager = SettingsTabManager(self)
        self.w.settings_manager.open()
        self.w.settings_manager = SettingsTabManager(self)
        self.w.settings_manager.open()
        self.w.settings_manager.open()

    # --- Gameplay/Turn/Phase mechanics for UI delegation ---

    def toggle_attacker(self, card):
        # Find the permanent and toggle as attacker
        perm = self._find_perm(card.id)
        if perm:
            self.game.combat.toggle_attacker(0, perm)

    def has_attackers(self):
        return bool(getattr(self.game.combat.state, "attackers", []))

    def commit_attackers(self):
        self.game.combat.attackers_committed()
        self.controller.advance_step()  # or whatever advances to block phase

    def handle_blocker_click(self, card):
        perm = self._find_perm(card.id)
        if not perm:
            return
        sel = getattr(self, '_pending_blocker', None)
        if sel is None:
            if perm.card.controller_id == 1:
                self._pending_blocker = perm
        else:
            if perm in self.game.combat.state.attackers:
                self.game.combat.toggle_blocker(1, sel, perm)
                self._pending_blocker = None
            elif perm.card.controller_id == 1:
                self._pending_blocker = perm

    def commit_blockers(self):
        self.controller.advance_step()  # or whatever advances to combat damage
        try:
            self.game.combat.assign_and_deal_damage()
        except Exception:
            pass
        self.controller.advance_step()  # advance to next phase

    def advance_to_phase(self, phase_name):
        # Implement logic to advance to a specific phase if needed
        # For now, just call advance_step until phase matches
        while self.controller.phase != phase_name:
            self.controller.advance_step()

    def play_land(self, card):
        self.game.play_land(0, card)

    def cast_spell(self, card):
        # Implement autotap and cast logic here, previously in PlayArea
        ps = self.game.players[0]
        if not hasattr(ps, 'mana_pool'):
            from engine.mana import ManaPool
            ps.mana_pool = ManaPool()
        pool = ps.mana_pool
        from engine.mana import parse_mana_cost
        cost_dict = parse_mana_cost(getattr(card, 'mana_cost_str', None))
        if not cost_dict:
            generic_need = card.mana_cost if isinstance(card.mana_cost, int) else 0
            if generic_need:
                cost_dict = {'G': generic_need}
        colored_needs = {c: n for c, n in cost_dict.items() if c in ('W', 'U', 'B', 'R', 'G') and n > 0}
        def land_color(perm):
            n = perm.card.name.lower()
            for t, c in [('plains', 'W'), ('island', 'U'), ('swamp', 'B'), ('mountain', 'R'), ('forest', 'G')]:
                if t in n:
                    return c
            return 'G'
        untapped = [perm for perm in ps.battlefield if 'Land' in perm.card.types and not perm.tapped]
        for color, need in list(colored_needs.items()):
            while need > 0:
                found = next((l for l in untapped if land_color(l) == color), None)
                if not found:
                    break
                self.game.tap_for_mana(0, found)
                pool.add(color, 1)
                untapped.remove(found)
                need -= 1
            colored_needs[color] = need
        remaining = cost_dict.get('G', 0) + sum(rem for rem in colored_needs.values() if rem > 0)
        for land in list(untapped):
            if remaining <= 0:
                break
            sym = land_color(land)
            self.game.tap_for_mana(0, land)
            pool.add(sym, 1)
            remaining -= 1
        if not pool.can_pay(cost_dict):
            return
        pool.pay(cost_dict)
        self.game.cast_spell(0, card)

    def _find_perm(self, card_id):
        for p in self.game.players:
            for perm in p.battlefield:
                if getattr(perm.card, 'id', None) == card_id:
                    return perm
        return None
