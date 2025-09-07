import random
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QMessageBox

from engine.game_controller import GameController
from engine.game_state import GameState
from engine.rules_engine import init_rules
from image_cache import ensure_card_image
from engine.game_ids import generate_game_id, register_game_id
from engine.phase_hooks import register_phase_controller

class GameAppAPI:
    """
    Facade exposing game + lobby + deck + phase operations for UI tabs.
    MainWindow now only creates this and wires it into tabs.
    """
    def __init__(self, main_window, game, ai_ids, args, new_game_factory):
        self.w = main_window
        self.args = args
        self._new_game_factory = new_game_factory
        desired_logging = not (args and args.no_log)
        self.controller = GameController(game, ai_ids, logging_enabled=False)  # CHANGED: start muted
        self._desired_logging_flag = desired_logging                           # NEW
        register_phase_controller(self.controller)  # ensure centralized phase logic
        self.game = self.controller.game
        self.game_id = generate_game_id()
        register_game_id(self.game_id)
        self.game.game_id = self.game_id
        self._opening_sequence_done = False
        from engine.phase_hooks import install_phase_log_deduper  # ensure deduper before any phase logs
        install_phase_log_deduper(self.controller)
        self.pending_match_active = False  # ensure defined early
        self._debug_win = None
        self._game_window = None  # gameplay window (created later)

    # --- Accessors for tabs ---
    def get_game(self):
        return self.game

    def get_controller(self):
        return self.controller

    # --- Match / Lobby lifecycle ---
    def ensure_ai_opponent(self):
        self.controller.ensure_ai_opponent(self._new_game_factory)

    def create_pending_match(self):
        if self.pending_match_active:
            return
        self.pending_match_active = True                     # MOVED: set flag before rebuild
        player_deck = getattr(self.game.players[0], 'source_path', None) or getattr(self.w, 'current_deck_path', None)
        specs = [(self.game.players[0].name, player_deck, False)]
        self._rebuild_game_with_specs(specs)
        self._sync_lobby(True)
        self._log("[QUEUE] Pending match created. Awaiting players (max 4).")

    def add_ai_player_pending(self):
        if not self.pending_match_active or len(self.game.players) >= 4:
            return
        used_paths = {getattr(p, 'source_path', None) for p in self.game.players}
        import os
        decks_dir = os.path.join('data', 'decks')
        try:
            deck_files = [os.path.join(decks_dir, f) for f in os.listdir(decks_dir)
                          if f.lower().endswith('.txt')]
        except Exception:
            deck_files = []
        ai_path = None
        for p in sorted(deck_files):
            if p not in used_paths:
                ai_path = p
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
        specs = [(self.game.players[0].name, getattr(self.game.players[0], 'source_path', None), False)]
        self._rebuild_game_with_specs(specs)
        self._sync_lobby(False)
        self._log("[QUEUE] Pending match canceled.")

    def start_pending_match(self):
        if not self.pending_match_active:
            return
        # Require at least 2 players; auto-add one AI if only 1 and decks available
        if len(self.game.players) == 1:
            self.ensure_ai_opponent()
        if len(self.game.players) == 1:
            QMessageBox.information(self.w, "Need Another Player",
                                    "You must add at least one more player (AI or human) before starting.")
            return
        self.pending_match_active = False
        # Proceed with normal start (roll if multi-player)
        if len(self.game.players) > 1:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, self.prompt_first_player_roll)
        else:
            self.start_game_without_roll()
        self._sync_lobby(False)
        self._log(f"[QUEUE] Match initialized with {len(self.game.players)} player(s).")

    # Direct lobby start (legacy)
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

    # --- Core start helpers ---
    def finalize_start_after_roll(self, starter_index: int):
        if not self.controller.in_game:
            self.controller.enter_match()
        self.controller.set_starter(starter_index)
        self._handle_opening_hands_and_mulligans()
        # REMOVED early self.controller.log_phase()
        self.open_game_window()               # CHANGED
        self._phase_ui()

    def start_game_without_roll(self):
        if len(self.game.players) == 1:
            self.ensure_ai_opponent()
            if len(self.game.players) > 1:
                QTimer.singleShot(50, self.prompt_first_player_roll)
                return
        if not self.controller.in_game:
            self.controller.enter_match()
        self.controller.set_starter(0)
        self._handle_opening_hands_and_mulligans()
        # REMOVED early self.controller.log_phase()
        self.open_game_window()               # CHANGED
        self._phase_ui()

    def prompt_first_player_roll(self):
        if self.controller.first_player_decided or len(self.game.players) < 2:
            return
        box = QMessageBox(self.w)
        box.setWindowTitle("Determine First Player")
        box.setText("Roll to determine who goes first.")
        roll_btn = box.addButton("Roll", QMessageBox.AcceptRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is roll_btn:
            winner, _ = self.controller.perform_first_player_roll()
            wn = self.game.players[winner].name
            choose = QMessageBox(self.w)
            choose.setWindowTitle("Roll Result")
            choose.setText(f"{wn} wins the roll.\nChoose turn order.")
            go_first = choose.addButton("Go First", QMessageBox.AcceptRole)
            pass_btn = choose.addButton("Pass", QMessageBox.DestructiveRole)
            choose.exec()
            starter = (winner + 1) % len(self.game.players) if choose.clickedButton() is pass_btn else winner
            self.finalize_start_after_roll(starter)

    # --- Game progression ---
    def advance_phase(self):  # CHANGED: ensure single AI tick & UI update without timers
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        # controller.advance_phase is patched by phase_hooks
        self.controller.advance_phase()
        self.controller.tick(lambda: None)
        self._phase_ui()

    def skip_combat(self):  # NEW
        if hasattr(self.controller, "request_skip_combat"):
            self.controller.request_skip_combat()
            self._phase_ui()

    def declare_attackers_committed(self):  # NEW (UI can call when attackers chosen)
        if hasattr(self.controller, "mark_combat_attackers_declared"):
            self.controller.mark_combat_attackers_declared()
            self._phase_ui()

    def ai_tick(self):  # CHANGED: remove dependency on window timer
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        pa = self._current_play_area()
        self.controller.tick(lambda: (
            pa.refresh_board() if (pa and hasattr(pa, "refresh_board")) else None
        ))
        self._phase_ui()

    # --- Player utilities ---
    def reload_player0(self, deck_path: str):
        if not deck_path:
            return
        import os
        if not os.path.exists(deck_path):
            QMessageBox.warning(self.w, "Reload", f"{deck_path} not found.")
            return
        try:
            self.controller.reload_player0(self._new_game_factory, deck_path)
        except Exception as ex:
            QMessageBox.critical(self.w, "Reload Failed", str(ex))
            return
        self.game = self.controller.game
        pa = self._current_play_area()
        if pa and hasattr(pa, "set_game"):
            pa.set_game(self.game)
        self._log("[RELOAD] Player 0 deck reloaded.")
        if hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()
        self._sync_lobby(self.pending_match_active)

    # --- Debug window ---
    def toggle_debug_window(self):
        try:
            from tools.game_debug_tests import GameDebugWindow
        except Exception as ex:
            QMessageBox.information(self.w, "Debug Window", f"Unavailable: {ex}")
            return
        if self._debug_win and self._debug_win.isVisible():
            self._debug_win.close()
            self._debug_win = None
        else:
            pa = self._current_play_area()
            self._debug_win = GameDebugWindow(self.game, pa, self.w if pa is None else self._game_window)
            # NEW: always-on-top
            self._debug_win.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self._debug_win.show()
            self._debug_win.raise_()
            self._debug_win.activateWindow()

    def shutdown(self):
        """
        Close any auxiliary windows / stop background activity.
        Called by MainWindow.closeEvent.
        """
        # close debug UI
        try:
            if self._debug_win:
                self._debug_win.close()
        except Exception:
            pass
        self._debug_win = None
        # close game window
        try:
            if self._game_window:
                self._game_window.close()
        except Exception:
            pass
        self._game_window = None
        # future: stop controller threads/loops if any
        # (controller currently ticked manually, so no action)

    # --- Key handling (can be called by MainWindow or Play tab) ---
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

    # --- Internal helpers ---
    def _rebuild_game_with_specs(self, specs):
        game, ai_ids = self._new_game_factory(specs, ai_enabled=True)
        # FIX: ensure we capture prior desired logging flag before recreating controller
        desired_logging = getattr(self, "_desired_logging_flag", True)
        # preserve previous controller logging_enabled just in case (not used until unlock)
        prev_logging_runtime = getattr(self.controller, "logging_enabled", False)
        self.controller = GameController(game, ai_ids, logging_enabled=False)  # start muted
        self._desired_logging_flag = desired_logging
        register_phase_controller(self.controller)
        from engine.phase_hooks import install_phase_log_deduper as install_phase_log_adapter
        install_phase_log_adapter(self.controller)
        self.game = self.controller.game
        self.game.game_id = self.game_id
        if self._game_window:
            try:
                self._game_window.close()
            except Exception:
                pass
            self._game_window = None
        pa = self._current_play_area()
        if pa and hasattr(pa, "set_game"):
            pa.set_game(self.game)
        if hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()
        self._phase_ui()
        # Skip auto-adding AI while in lobby pending mode
        if len(game.players) == 1 and not self.pending_match_active:
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
            while True:
                hand_names = ", ".join(c.name for c in human.hand)
                box = QMessageBox(self.w)
                box.setWindowTitle("Opening Hand")
                box.setText(
                    f"Opening Hand ({len(human.hand)}):\n{hand_names or '(empty)'}\n\n"
                    "Mulligan? (London mulligan: draw 7 each time then put cards on bottom equal to mulligans taken"
                    f"{' (first free in multiplayer)' if is_multi else ''})"
                )
                mull = box.addButton("Mulligan", QMessageBox.DestructiveRole)
                keep = box.addButton("Keep", QMessageBox.AcceptRole)
                box.exec()
                if box.clickedButton() is keep:
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
                    import random as _r
                    idxs = _r.sample(range(len(human.hand)), effective)
                    idxs.sort(reverse=True)
                    moving = []
                    for i in idxs:
                        moving.append(human.hand.pop(i))
                    human.library.extend(moving)
        self._opening_sequence_done = True
        setattr(self.game, '_opening_hands_deferred', False)
        # NEW: unlock phases & enable logging now (first visible phase log happens here)
        if hasattr(self.controller, 'unlock_phases'):
            self.controller.unlock_phases()
        self.controller.logging_enabled = self._desired_logging_flag
        if self.controller.logging_enabled and hasattr(self.controller, 'log_phase'):
            self.controller.log_phase()

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

    # --- Game window management (NEW) ---
    def open_game_window(self):
        if self._game_window:
            self._game_window.raise_(); self._game_window.activateWindow()
            return
        from ui.game_window import GameWindow
        # Create as independent top-level (no parent) so both windows stay interactive
        self._game_window = GameWindow(self, self.game_id)
        # (No setParent / modality; just position & focus handled inside GameWindow)
        self._game_window.show()
        self._game_window.raise_()
        self._game_window.activateWindow()

    def attach_game_window(self, gw):
        self._game_window = gw

    def handle_game_window_closed(self):
        self._game_window = None

    # --- NEW: unified play area accessor ---
    def _current_play_area(self):
        if self._game_window and hasattr(self._game_window, "play_area"):
            return self._game_window.play_area
        return None

    # Legacy compatibility (home tab / older code may still call):
    _open_settings_tab = open_settings
    # Legacy compatibility (home tab / older code may still call):
    _open_settings_tab = open_settings
    _open_settings_tab = open_settings
