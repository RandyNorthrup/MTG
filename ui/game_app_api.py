import os
import random
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox, QDialog
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
        # Store reference to this API in the controller for UI updates
        self.controller._api_ref = self
        self.game = self.controller.game
        # Beginning phase step timer for automatic untap/upkeep/draw progression
        self._beginning_phase_timer = QTimer()
        self._beginning_phase_timer.timeout.connect(self._auto_advance_beginning_steps)
        self._beginning_phase_timer.setSingleShot(True)
        self._beginning_step_queue = []
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
        # Refresh UI after playing land
        self._force_immediate_ui_refresh()

    def cast_spell(self, card):
        self.controller.cast_spell(card)
        # Refresh UI after casting spell
        self._force_immediate_ui_refresh()
        
    # --- Enhanced Card Interaction Methods ---
    def get_current_player(self):
        """Get the current player (for enhanced card interactions)."""
        if self.game and self.game.players:
            active_id = getattr(self.game, 'active_player', 0)
            if 0 <= active_id < len(self.game.players):
                return self.game.players[active_id]
        return None
        
    def can_play_card(self, card):
        """Check if a card can be played from hand."""
        try:
            player = self.get_current_player()
            if not player:
                return False, "No active player"
            
            # Check if card is in player's hand
            if not hasattr(player, 'hand') or card not in player.hand:
                return False, "Card not in hand"
            
            # Basic playability checks
            card_types = getattr(card, 'types', [])
            
            # Land checks
            if "Land" in card_types:
                # Check if we can play a land this turn
                lands_played = getattr(self.game, 'land_played_this_turn', {}).get(player.player_id, False)
                if lands_played:
                    return False, "Already played a land this turn"
                return True, "Can play land"
            
            # Spell checks
            mana_cost = getattr(card, 'mana_cost', 0)
            current_mana = getattr(player, 'mana', 0)
            
            # Check mana availability
            if hasattr(player, 'mana_pool'):
                # Use mana pool if available
                from engine.mana import parse_mana_cost
                cost_dict = parse_mana_cost(getattr(card, 'mana_cost_str', str(mana_cost)))
                if not player.mana_pool.can_pay(cost_dict):
                    return False, "Insufficient mana"
            else:
                # Simple mana check
                if mana_cost > current_mana:
                    return False, f"Need {mana_cost} mana, have {current_mana}"
            
            # Phase/timing checks
            current_phase = getattr(self.controller, 'current_phase', 'main1')
            if "Sorcery" in card_types and current_phase not in ['main1', 'main2']:
                return False, "Sorceries can only be played during main phases"
            
            return True, "Card can be played"
            
        except Exception as e:
            return False, f"Error checking playability: {e}"
            
    def play_card_from_hand(self, card):
        """Play a card from hand (enhanced version)."""
        try:
            can_play, reason = self.can_play_card(card)
            if not can_play:
                print(f"Cannot play {getattr(card, 'name', 'card')}: {reason}")
                return False
                
            if "Land" in getattr(card, 'types', []):
                return self._play_land_enhanced(card)
            else:
                return self._cast_spell_enhanced(card)
        except Exception as e:
            print(f"Error playing card: {e}")
            return False
            
    def _play_land_enhanced(self, card):
        """Enhanced land playing with comprehensive error handling."""
        try:
            player = self.get_current_player()
            if not player:
                print(f"❌ No current player")
                return False
            
            # Validate the land can be played
            if not hasattr(player, 'hand') or card not in player.hand:
                print(f"❌ Card not in player's hand")
                return False
            
            if "Land" not in getattr(card, 'types', []):
                print(f"❌ Card is not a land")
                return False
            
            # Check if we can play a land this turn
            if hasattr(self.game, 'land_played_this_turn'):
                land_played = self.game.land_played_this_turn.get(player.player_id, False)
                if land_played:
                    print(f"❌ Already played a land this turn")
                    return False
            
            # Call the game state method directly instead of controller
            try:
                from engine.card_engine import ActionResult
                result = self.game.play_land(player.player_id, card)
                
                if result == ActionResult.OK:
                    print(f"✅ Land played successfully: {getattr(card, 'name', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Land play failed: {result}")
                    return False
                    
            except Exception as e:
                print(f"❌ Game state land play failed: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Critical error in land play: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _cast_spell_enhanced(self, card):
        """Enhanced spell casting with comprehensive error handling."""
        try:
            player = self.get_current_player()
            if not player:
                print(f"❌ No current player")
                return False
            
            # Validate the spell can be cast
            if not hasattr(player, 'hand') or card not in player.hand:
                print(f"❌ Card not in player's hand")
                return False
            
            card_types = getattr(card, 'types', [])
            if "Land" in card_types:
                print(f"❌ Cannot cast lands as spells")
                return False
            
            # Call the game state method directly
            try:
                from engine.card_engine import ActionResult
                result = self.game.cast_spell(player.player_id, card)
                
                if result == ActionResult.OK:
                    print(f"✅ Spell cast successfully: {getattr(card, 'name', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Spell cast failed: {result}")
                    return False
                    
            except Exception as e:
                print(f"❌ Game state spell cast failed: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Critical error in spell cast: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def tap_for_mana(self, player, permanent):
        """Tap a permanent for mana."""
        try:
            if not permanent or getattr(permanent, 'tapped', False):
                return False
                
            card = getattr(permanent, 'card', permanent)
            if 'Land' not in getattr(card, 'types', []):
                return False
                
            # Determine mana color from card
            mana_color = self._determine_mana_color(card)
            
            # Tap the permanent
            permanent.tapped = True
            if hasattr(card, 'tap'):
                card.tap()
                
            # Add mana to player's pool
            if hasattr(player, 'mana_pool'):
                player.mana_pool.add(mana_color, 1)
                print(f"Tapped {card.name} for {mana_color} mana")
                return True
                
            return False
        except Exception as e:
            print(f"Error tapping for mana: {e}")
            return False
            
    def _determine_mana_color(self, card):
        """Determine what color mana a card produces."""
        name = getattr(card, 'name', '').lower()
        text = getattr(card, 'text', '').lower()
        
        # Basic lands
        if 'plains' in name:
            return 'W'
        elif 'island' in name:
            return 'U'
        elif 'swamp' in name:
            return 'B'
        elif 'mountain' in name:
            return 'R'
        elif 'forest' in name:
            return 'G'
            
        # Parse mana symbols from text
        import re
        mana_symbols = re.findall(r'\{([WUBRG])\}', text)
        if mana_symbols:
            return mana_symbols[0]  # Return first found
            
        return 'C'  # Default to colorless
        
    def declare_attacker(self, card):
        """Declare a creature as an attacker."""
        try:
            # Use existing toggle_attacker method
            self.toggle_attacker(card)
            return True
        except Exception as e:
            print(f"Error declaring attacker: {e}")
            return False
            
    def activate_tap_ability(self, card):
        """Activate a tap ability of a card."""
        try:
            # Find the permanent on battlefield
            player = self.get_current_player()
            if not player or not hasattr(player, 'battlefield'):
                return False
                
            for perm in player.battlefield:
                if hasattr(perm, 'card') and perm.card == card:
                    # Check if it has a tap ability and is not tapped
                    if (not getattr(perm, 'tapped', False) and 
                        hasattr(card, 'text') and '{T}:' in card.text):
                        
                        # Tap the permanent
                        perm.tapped = True
                        if hasattr(card, 'tap'):
                            card.tap()
                            
                        # TODO: Parse and execute the actual ability
                        print(f"Activated tap ability of {card.name}")
                        return True
                        
            return False
        except Exception as e:
            print(f"Error activating tap ability: {e}")
            return False
            
    def show_card_details(self, card):
        """Show detailed information about a card."""
        # This would open a detailed card view
        # For now, just print the information
        print(f"=== {getattr(card, 'name', 'Unknown Card')} ===")
        print(f"Types: {'/'.join(getattr(card, 'types', []))}") 
        if hasattr(card, 'mana_cost'):
            print(f"Mana Cost: {card.mana_cost}")
        if hasattr(card, 'power') and hasattr(card, 'toughness'):
            print(f"P/T: {card.power}/{card.toughness}")
        if hasattr(card, 'text') and card.text:
            print(f"Text: {card.text}")
    
    # --- Drag and Drop Handler Methods ---
    def handle_card_drop_to_battlefield(self, card_data, zone_name=None):
        """Handle a card being dropped onto the battlefield with comprehensive error handling.
        
        The zone_name parameter is ignored - cards are automatically placed in the correct
        battlefield zone based on their card type (creatures, lands, artifacts, etc.).
        """
        
        try:
            # Get current player
            player = self.get_current_player()
            if not player or not hasattr(player, 'hand'):
                print(f"❌ API: No current player or player has no hand")
                return False
            
            # Find the target card
            target_card = None
            for card in player.hand:
                if getattr(card, 'id', None) == card_data:
                    target_card = card
                    break
            
            if not target_card:
                print(f"❌ API: Card {card_data} not found in player's hand")
                return False
            
            # Get card name for logging
            card_name = getattr(target_card, 'name', 'unknown card')
            card_types = getattr(target_card, 'types', [])
            
            print(f"🎯 API: Attempting to play {card_name} (types: {card_types})")
            
            # Check if card can be played
            can_play, reason = self.can_play_card(target_card)
            if not can_play:
                print(f"❌ Cannot play {card_name}: {reason}")
                return False
            
            # Play the card - let the game engine determine the correct placement
            if "Land" in card_types:
                print(f"🌱 Playing land: {card_name}")
                success = self._play_land_enhanced(target_card)
            else:
                print(f"✨ Casting spell: {card_name}")
                success = self._cast_spell_enhanced(target_card)
            
            if success:
                print(f"✅ {card_name} played successfully - will be placed in appropriate battlefield zone")
                
                # Give the game state a moment to update
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()
                
                # Force comprehensive UI refresh
                try:
                    self._force_immediate_ui_refresh()
                    print(f"✅ API: UI refresh completed")
                except Exception as ui_error:
                    print(f"❌ API: UI refresh failed: {ui_error}")
                    # Continue anyway - the card was played successfully
                
                return True
            else:
                print(f"❌ API: Failed to play {card_name}")
            
            return False
                
        except Exception as e:
            print(f"❌ API ERROR in handle_card_drop_to_battlefield: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def handle_card_drop_to_hand(self, card_data):
        """Handle a card being dropped back to hand (return from battlefield)."""
        try:
            # This would typically return a card from battlefield to hand
            # For now, just log the action
            print(f"Card {card_data} returned to hand")
            
            # In a full implementation, you would:
            # 1. Find the card on the battlefield
            # 2. Move it back to hand
            # 3. Update game state
            # 4. Refresh UI
            
            return True
            
        except Exception as e:
            print(f"Error handling card drop to hand: {e}")
            return False

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
        # Don't recreate game if already in active gameplay (prevents hand reset)
        if self.pending_match_active or self.controller.in_game or self.controller.first_player_decided:
            return
            
        # Ensure game and players exist before accessing them
        if not self.game or not hasattr(self.game, 'players') or not self.game.players:
            # Initialize with default player if none exist
            specs = [("You", None, False)]  # Default player with no deck path initially
        else:
            player_deck = getattr(self.game.players[0], 'source_path', None)
            player_name = getattr(self.game.players[0], 'name', 'You')
            specs = [(player_name, player_deck, False)]
            
        self._rebuild_game_with_specs(specs)
        self.pending_match_active = True
        self._sync_lobby(True)
        self._log("[QUEUE] Pending match created. Awaiting players (max 4).")

    def add_ai_player_pending(self):
        # Don't modify game if already in active gameplay (prevents hand reset)
        if not self.pending_match_active or self.controller.in_game or self.controller.first_player_decided:
            return
        
        # Ensure game and players exist before accessing them
        if not self.game or not hasattr(self.game, 'players') or not self.game.players:
            return
            
        if len(self.game.players) >= 4:
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
        # Don't recreate game if already in active gameplay (prevents hand reset)
        if not self.pending_match_active or self.controller.in_game or self.controller.first_player_decided:
            return
        self.pending_match_active = False
        
        # Ensure game and players exist before accessing them
        if not self.game or not hasattr(self.game, 'players') or not self.game.players:
            specs = [("You", None, False)]  # Default player
        else:
            player_name = getattr(self.game.players[0], 'name', 'You')
            player_deck = getattr(self.game.players[0], 'source_path', None)
            specs = [(player_name, player_deck, False)]
            
        self._rebuild_game_with_specs(specs)
        self._sync_lobby(False)
        self._log("[QUEUE] Pending match canceled.")

    def start_pending_match(self):
        if not self.pending_match_active:
            return
        self.pending_match_active = False
        
        # Ensure game and players exist before accessing them
        if not self.game or not hasattr(self.game, 'players') or not self.game.players:
            self._log("[ERROR] Cannot start match - no game or players initialized")
            return
            
        if len(self.game.players) > 1:
            # Ensure board window opens first, then prompt for roll immediately
            self._ensure_game_window()
            self.prompt_first_player_roll()
        else:
            self.start_game_without_roll()
        self._sync_lobby(False)
        self._log(f"[QUEUE] Match initialized with {len(self.game.players)} player(s).")

    def enter_match_now(self):
        if self.pending_match_active:
            return
        self.ensure_ai_opponent()
        if len(self.game.players) > 1:
            # Ensure board window opens first, then prompt for roll immediately
            self._ensure_game_window()
            self.prompt_first_player_roll()
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
        # NOW draw opening hands after roll is decided (correct MTG timing)
        self.controller.draw_opening_hands()
        self._handle_opening_hands_and_mulligans()
        self.controller.log_phase()
        self._phase_ui()
        # Trigger automatic beginning phase sequence for game start
        self._trigger_beginning_phase_sequence()
        # Force board window focus after game starts
        if self.board_window:
            self.board_window.show()
            self.board_window.raise_()
            self.board_window.activateWindow()

    def start_game_without_roll(self):
        self._ensure_game_window()                     # ADDED
        
        # Ensure game and players exist before accessing them
        if not self.game or not hasattr(self.game, 'players'):
            self._log("[ERROR] Cannot start game - no game or players initialized")
            return
            
        if len(self.game.players) == 1:
            self.ensure_ai_opponent()
            if len(self.game.players) > 1:
                # Ensure board window opens first, then prompt for roll immediately
                self._ensure_game_window()
                self.prompt_first_player_roll()
                return
        if not self.controller.in_game:
            self.controller.enter_match()
        self.controller.set_starter(0)
        # Draw opening hands after starter is set
        self.controller.draw_opening_hands()
        self._handle_opening_hands_and_mulligans()
        self.controller.log_phase()
        self._phase_ui()
        # Trigger automatic beginning phase sequence for game start
        self._trigger_beginning_phase_sequence()
        # Force board window focus after game starts  
        if self.board_window:
            self.board_window.show()
            self.board_window.raise_()
            self.board_window.activateWindow()

    def prompt_first_player_roll(self):
        if self.controller.first_player_decided or len(self.game.players) < 2:
            return
        
        # Ensure board window is open and use it as the dialog parent
        self._ensure_game_window()
        
        # Use the animated dice roll dialog
        from ui.dice_roll_dialog import DiceRollDialog
        host = self.board_window if self.board_window and self.board_window.isVisible() else self.w
        
        dice_dialog = DiceRollDialog(self.game.players, parent=host)
        dice_dialog.set_ai_controllers(getattr(self.controller, 'ai_controllers', {}))
        result = dice_dialog.exec()
        
        if result != QDialog.Accepted:
            return
            
        winner = dice_dialog.get_winner()
        rolls = dice_dialog.get_rolls()
        
        if winner is None:
            return
            
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
            choose.setText(f"You win the roll with {rolls.get(winner, '?')}!\nChoose turn order.")
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
        choose.setText(f"{wn} wins the roll with {rolls.get(winner, '?')}!\nWinner chooses turn order.")
        go_first = choose.addButton("Go First", QMessageBox.AcceptRole)
        pass_btn = choose.addButton("Pass", QMessageBox.DestructiveRole)
        choose.exec()
        starter = (winner + 1) % len(self.game.players) if choose.clickedButton() is pass_btn else winner
        self._log(f"[ROLL] {wn} wins roll and chooses {'to pass' if starter != winner else 'to go first'}.")
        self.finalize_start_after_roll(starter)

    # Turn / phases
    def advance_phase(self):
        """Advance to the next phase/step - called by player action, not timer."""
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        
        # Check if we're currently at cleanup (end of turn)
        current_phase = getattr(self.controller, 'current_phase', '')
        is_at_cleanup = (current_phase == 'cleanup')
        
        from engine.phase_hooks import advance_step
        advance_step(self.controller)
        
        # Check if we just moved to a new turn (cleanup → beginning phases)
        new_phase = getattr(self.controller, 'current_phase', '')
        if is_at_cleanup and new_phase == 'untap':
            # We've moved to a new turn, trigger automatic beginning phase sequence
            self._trigger_beginning_phase_sequence()
            return  # Let the timer handle the beginning phases
        
        # Sync the phase state with game state
        if hasattr(self.controller, 'sync_phase_state'):
            self.controller.sync_phase_state()
        
        # Update UI immediately after phase change
        self._phase_ui()
        self._force_immediate_ui_refresh()

    def handle_ai_turn(self):
        """Handle AI player actions when it's their turn (called manually, not on timer)."""
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
        
        current_ap = getattr(self.game, 'active_player', 0)
        if current_ap in getattr(self.controller, 'ai_controllers', {}):
            # AI makes decisions and takes actions
            try:
                ai = self.controller.ai_controllers[current_ap]
                if hasattr(ai, 'take_turn'):
                    ai.take_turn(self.game)
                # Refresh UI after AI action
                self._force_immediate_ui_refresh()
                self._phase_ui()
            except Exception:
                pass

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
        # Main window no longer has a play area - only board window is used
        self._log("[RELOAD] Player 0 deck reloaded.")
        if hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()
        self._sync_lobby(self.pending_match_active)

    # Debug
    def toggle_debug_window(self):
        """Toggle the new robust debug window."""
        if self._debug_win and self._debug_win.isVisible():
            self._debug_win.close()
            self._debug_win = None
        else:
            from ui.debug_window import DebugWindow
            self._debug_win = DebugWindow(self)
            self._debug_win.show()

    # Keys
    def handle_key(self, key):
        """Handle keyboard input for game actions."""
        from PySide6.QtCore import Qt
        
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
            
        if key == Qt.Key_Space:
            # Space: resolve stack or advance phase
            if hasattr(self.game, 'stack') and self.game.stack.can_resolve():
                self.game.stack.resolve_top(self.game)
                self._force_immediate_ui_refresh()
            else:
                self.advance_phase()
                # If it's now an AI player's turn, let them act
                self.handle_ai_turn()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            # Enter: manual phase advance
            self.advance_phase()
            self.handle_ai_turn()
        elif key == Qt.Key_L:
            self.controller.logging_enabled = not self.controller.logging_enabled
            self.w.logging_enabled = self.controller.logging_enabled
        elif key == Qt.Key_F9:
            self.toggle_debug_window()
        elif key == Qt.Key_F5 and hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()

    # Game quit/loss handling
    def handle_game_quit_loss(self):
        """Handle when player quits the game - record as loss and cleanup."""
        try:
            if self.controller.logging_enabled:
                # Player quit the game - recording loss (debug print removed)
                pass
            
            # Record the loss (basic implementation - could be extended with stats tracking)
            self._record_game_loss("quit")
            
            # Reset game state
            self.controller.in_game = False
            self.controller.first_player_decided = False
            
            # Update lobby state
            self._sync_lobby(False)
            
            if self.controller.logging_enabled:
                # Game state reset and loss recorded (debug print removed)
                pass
                
        except Exception as e:
            if self.controller.logging_enabled:
                # Error handling game quit (debug print removed)
                pass
    
    def handle_game_window_closed(self):
        """Handle when the game board window is closed (cleanup only)."""
        try:
            if self.controller.logging_enabled:
                # Board window closed (debug print removed)
                pass
            # Just cleanup, no loss recording since that's handled in closeEvent
        except Exception as e:
            if self.controller.logging_enabled:
                # Error handling game window close (debug print removed)
                pass
    
    def _record_game_loss(self, reason: str):
        """Record a game loss with the given reason."""
        try:
            # Basic loss recording - could be extended to write to file, database, etc.
            if self.controller.logging_enabled:
                players = [p.name for p in self.game.players] if self.game.players else ["Unknown"]
                player_name = players[0] if players else "You"
                # Loss recorded (debug print removed for production)
                pass
            
            # Here you could add:
            # - Write to a stats file
            # - Update player profile/database
            # - Send to online leaderboard
            # - etc.
            
        except Exception as e:
            if self.controller.logging_enabled:
                # Error recording loss (debug print removed)
                pass

    # Shutdown
    def shutdown(self):
        try:
            if hasattr(self, '_beginning_phase_timer'):
                self._beginning_phase_timer.stop()
            if self._debug_win and self._debug_win.isVisible():
                self._debug_win.close()
        except Exception:
            pass
    
    def _auto_advance_beginning_steps(self):
        """Automatically advance through beginning phase steps with 300ms delays."""
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
            
        if not self._beginning_step_queue:
            return
            
        # Get next step from queue
        next_step = self._beginning_step_queue.pop(0)
        
        # Set the phase
        from engine.phase_hooks import set_phase
        set_phase(self.controller, next_step)
        
        # Sync and refresh UI
        if hasattr(self.controller, 'sync_phase_state'):
            self.controller.sync_phase_state()
        self._force_immediate_ui_refresh()
        
        # If there are more steps, schedule the next one
        if self._beginning_step_queue:
            self._beginning_phase_timer.start(300)  # 300ms delay
    
    def _trigger_beginning_phase_sequence(self):
        """Start the automatic beginning phase sequence (untap → upkeep → draw)."""
        if not (self.controller.in_game and self.controller.first_player_decided):
            return
            
        # Queue up the beginning phase steps
        self._beginning_step_queue = ['untap', 'upkeep', 'draw']
        
        # Start the sequence after 300ms
        self._beginning_phase_timer.start(300)

    # Internal helpers
    def _rebuild_game_with_specs(self, specs):
        game, ai_ids = self._new_game_factory(specs, ai_enabled=True)
        logging_flag = self.controller.logging_enabled
        self.controller = GameController(game, ai_ids, logging_enabled=logging_flag)
        self.game = self.controller.game
        self.w.logging_enabled = self.controller.logging_enabled
        # Main window no longer has a play area - only board window is used
        if hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()
        self._phase_ui()
        if len(game.players) == 1:
            self.ensure_ai_opponent()

    def _handle_opening_hands_and_mulligans(self):
        if self._opening_sequence_done:
            return
        
        # Initialize mulligan counters (hands should already be drawn by controller)
        for pl in self.game.players:
            if not hasattr(pl, 'hand'):
                pl.hand = []
            pl.mulligans_taken = 0
            
        is_multi = len(self.game.players) > 2
        human = self.game.players[0] if self.game.players else None
        if human:
            self._ensure_game_window()                 # ADDED
            # Allow board window time to fully initialize
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            # Use board window if available and visible
            if self.board_window and self.board_window.isVisible():
                host = self.board_window
            else:
                host = self.w
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
                result = box.exec()
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
        
        # Mulligan sequence complete

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
            # Log message (debug print removed for production)
            pass
    
    def _force_immediate_ui_refresh(self):
        """Force an immediate UI refresh after game state changes."""
        try:
            print(f"🔄 API-REFRESH: Starting UI refresh...")
            
            # Check if board window exists and is visible
            if not hasattr(self, 'board_window') or not self.board_window:
                print(f"⚠️  API-REFRESH: No board window available")
                return
                
            if not self.board_window.isVisible():
                print(f"⚠️  API-REFRESH: Board window not visible")
                return
            
            print(f"🔍 API-REFRESH: Board window found and visible")
            
            # Try to refresh the game board's refresh_game_state method (from EnhancedGameBoard)
            try:
                # Method 1: Direct refresh_game_state on board window
                if hasattr(self.board_window, 'refresh_game_state'):
                    print(f"🔄 API-REFRESH: Calling board_window.refresh_game_state()...")
                    self.board_window.refresh_game_state()
                    print(f"✅ API-REFRESH: Direct board window refresh completed")
                    
                # Method 2: Refresh via play_area (enhanced game board)
                elif hasattr(self.board_window, 'play_area') and hasattr(self.board_window.play_area, 'refresh_game_state'):
                    print(f"🔄 API-REFRESH: Calling play_area.refresh_game_state()...")
                    self.board_window.play_area.refresh_game_state()
                    print(f"✅ API-REFRESH: Play area refresh completed")
                    
                # Method 3: Refresh via central widget
                elif hasattr(self.board_window, 'centralWidget'):
                    central_widget = self.board_window.centralWidget()
                    if hasattr(central_widget, 'refresh_game_state'):
                        print(f"🔄 API-REFRESH: Calling centralWidget.refresh_game_state()...")
                        central_widget.refresh_game_state()
                        print(f"✅ API-REFRESH: Central widget refresh completed")
                    else:
                        print(f"⚠️  API-REFRESH: Central widget has no refresh_game_state method")
                else:
                    print(f"⚠️  API-REFRESH: No valid refresh method found on board window")
                    
            except Exception as refresh_error:
                print(f"❌ API-REFRESH: Refresh method failed: {refresh_error}")
                import traceback
                traceback.print_exc()
            
            # Force window update and process events
            try:
                self.board_window.update()
                # Process any pending events to ensure UI updates
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()
                print(f"✅ API-REFRESH: Window update and event processing completed")
            except Exception as update_error:
                print(f"❌ API-REFRESH: Window update failed: {update_error}")
                
        except Exception as critical_error:
            print(f"❌ API-REFRESH: Critical refresh error: {critical_error}")
            import traceback
            traceback.print_exc()

    # --- Enhanced Lobby Integration Methods ---
    def get_players(self):
        """Get list of players for enhanced lobby."""
        return getattr(self.game, 'players', [])
    
    def create_match(self, name: str, max_players: int = 4, password: Optional[str] = None) -> bool:
        """Create a new match for enhanced lobby."""
        try:
            if not self.pending_match_active:
                self.create_pending_match()
                self._log(f"[MATCH] Created match '{name}' (max {max_players} players)")
            return True
        except Exception as e:
            self._log(f"[ERROR] Failed to create match: {e}")
            return False
    
    def join_match(self, match_id: str, password: Optional[str] = None) -> bool:
        """Join an existing match for enhanced lobby."""
        try:
            # For local matches, just add AI player
            if not self.pending_match_active:
                self.create_pending_match()
            self.add_ai_player_pending()
            self._log(f"[MATCH] Joined match {match_id}")
            return True
        except Exception as e:
            self._log(f"[ERROR] Failed to join match: {e}")
            return False
    
    def refresh_matches(self):
        """Refresh available matches list for enhanced lobby."""
        # Return mock matches for local play
        matches = []
        if not self.pending_match_active:
            matches.append({
                "id": "local_match_1",
                "name": "Local Commander Game",
                "players": 1,
                "max_players": 4,
                "status": "open"
            })
        else:
            matches.append({
                "id": "current_pending",
                "name": "Your Pending Match",
                "players": len(self.game.players),
                "max_players": 4,
                "status": "pending"
            })
        return matches
    
    def get_available_decks(self):
        """Get list of available decks for enhanced lobby."""
        decks = []
        decks_dir = os.path.join('data', 'decks')
        try:
            if os.path.exists(decks_dir):
                for filename in os.listdir(decks_dir):
                    if filename.lower().endswith('.txt'):
                        deck_path = os.path.join(decks_dir, filename)
                        deck_name = os.path.splitext(filename)[0]
                        decks.append({
                            "name": deck_name,
                            "path": deck_path,
                            "valid": True  # Could add validation here
                        })
        except Exception as e:
            self._log(f"[ERROR] Failed to load decks: {e}")
        return decks
    
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
        elif key == Qt.Key_F9:
            self.toggle_debug_window()
        elif key == Qt.Key_F5 and hasattr(self.w, 'decks_manager'):
            self.w.decks_manager.refresh()

    def handle_game_quit_loss(self):
        """Handle game quit by recording a loss and performing cleanup."""
        if hasattr(self.controller, 'in_game') and self.controller.in_game:
            # Record the loss for the human player
            if hasattr(self.game, 'players') and self.game.players:
                human_player = next((p for p in self.game.players if hasattr(p, 'is_human') and p.is_human), None)
                if human_player and hasattr(human_player, 'name'):
                    # You can extend this to record to a stats file or database
                    pass
            
            # Reset game state
            self.controller.in_game = False
            self.controller.first_player_decided = False
            
            # Clean up any game resources
            if hasattr(self, 'game'):
                self.game = None

    def open_settings(self):
        """Open (or lazily create) the Settings tab via SettingsTabManager."""
        if not getattr(self.w, 'settings_manager', None):
            from ui.settings_tab import SettingsTabManager
            self.w.settings_manager = SettingsTabManager(self)
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
        from engine.phase_hooks import advance_step
        advance_step(self.controller)  # or whatever advances to block phase

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
        from engine.phase_hooks import advance_step
        advance_step(self.controller)  # or whatever advances to combat damage
        try:
            self.game.combat.assign_and_deal_damage()
        except Exception:
            pass
        advance_step(self.controller)  # advance to next phase

    def advance_to_phase(self, phase_name):
        # Delegate to controller's advance_to_phase method
        self.controller.advance_to_phase(phase_name)

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
