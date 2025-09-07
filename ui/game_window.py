from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from ui.ui_manager import PlayArea

class GameWindow(QMainWindow):
    """Standalone play / board window used for roll + mulligan dialogs."""
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.setWindowTitle("Game Board")
        self.setMinimumSize(1280, 720)  # ADDED enforce minimum board size
        self.play_area = PlayArea(api.game)
        if hasattr(self.play_area, "enable_drag_and_drop"):
            self.play_area.enable_drag_and_drop()

        root = QWidget(); self.setCentralWidget(root)
        v = QVBoxLayout(root); v.setContentsMargins(6,6,6,6); v.setSpacing(4)

        bar = QHBoxLayout()
        self.phase_lbl = QLabel("Phase: —")
        self.phase_lbl.setStyleSheet("font-weight:bold;")
        btn_adv = QPushButton("Advance (Space)")
        btn_adv.clicked.connect(api.advance_phase)
        btn_dbg = QPushButton("Debug")
        btn_dbg.clicked.connect(api.toggle_debug_window)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        bar.addWidget(self.phase_lbl)
        bar.addStretch(1)
        bar.addWidget(btn_adv)
        bar.addWidget(btn_dbg)
        bar.addWidget(btn_close)
        v.addLayout(bar)

        v.addWidget(self.play_area, 1)

        # Ensure initial size is at least the minimum even if platform defaulted smaller
        if self.width() < 1280 or self.height() < 720:  # ADDED
            self.resize(max(self.width(), 1280), max(self.height(), 720))
        self._phase_timer = QTimer(self)
        self._phase_timer.timeout.connect(self.refresh_phase)
        self._phase_timer.start(750)
        self.refresh_phase()

    def refresh_phase(self):
        phase = getattr(self.api.controller, 'phase', '?')
        step = getattr(self.api.controller, 'step', None)
        ap_name = getattr(self.api.controller, 'active_player_name', "—")
        if step and step != phase:
            self.phase_lbl.setText(f"Phase: {phase} ({step})  Active: {ap_name}")
        else:
            self.phase_lbl.setText(f"Phase: {phase}  Active: {ap_name}")

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
        self.api.handle_key(e.key())
        super().keyPressEvent(e)

    def closeEvent(self, ev):
        if getattr(self.api, 'board_window', None) is self:
            self.api.board_window = None
        super().closeEvent(ev)
        # Drop always-on-top shortly after showing so both windows stay interactive
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))

        # After UI constructed (buttons exist) ensure correct initial visibility
        QTimer.singleShot(0, self._refresh_combat_buttons)

    def _current_phase(self):
        return getattr(getattr(self.api, 'game', None), 'phase', 'Beginning')

    def _is_my_turn(self):  # ADDED
        g = getattr(self.api, 'game', None)
        if not g or not hasattr(g, 'active_player'):
            return False
        # Assuming local human player is index 0
        return g.active_player == 0

    def _refresh_combat_buttons(self):
        # Unified visibility rules
        ph = self._current_phase()
        ctrl = getattr(self.api, 'controller', None)
        waiting = bool(getattr(ctrl, '_combat_wait_attackers', False) or
                       getattr(ctrl, '_combat_waiting_for_attackers', False))
        my_turn = self._is_my_turn()
        # End Phase only on your turn
        if hasattr(self, 'btn_end_phase'):
            self.btn_end_phase.setVisible(my_turn)
            auto_begin = (getattr(ctrl, '_hl_phase', '') == "Beginning" and
                          getattr(ctrl, '_begin_seq_running', False))
            self.btn_end_phase.setEnabled(my_turn and not auto_begin)
        # Skip Combat only on your turn while waiting for attackers
        if hasattr(self, 'btn_skip_combat'):
            show_skip = my_turn and ph == "Combat" and waiting
            self.btn_skip_combat.setVisible(show_skip)
            self.btn_skip_combat.setEnabled(show_skip)

    # --- Added backward compatibility wrapper (fix AttributeError) ---
    def _update_skip_combat_btn(self):
        """Legacy name kept for older calls; now just refreshes combat buttons."""
        self._refresh_combat_buttons()

    def _end_phase(self):
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "End Phase",
                                "Are you sure you want to end the current phase?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        self.api.advance_phase()
        self._refresh_combat_buttons()

    def _skip_combat_confirm(self):
        if QMessageBox.question(self, "Skip Combat",
                                "Skip the entire combat phase?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        self.api.skip_combat()
        self._refresh_combat_buttons()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
        self.api.handle_key(e.key())
        super().keyPressEvent(e)
        self._refresh_combat_buttons()

    # Optionally a method UI could call when attackers declared:
    def attackers_declared(self):  # OPTIONAL helper hook
        self.api.declare_attackers_committed()
        self._refresh_combat_buttons()
        self.btn_skip_combat.setEnabled(show)

    def _end_phase(self):
        if not self._confirm("End Phase", "Are you sure you want to end the current phase?"):
            return
        self.api.advance_phase()
        if hasattr(self.play_area, "refresh_board"):
            self.play_area.refresh_board()

    def _skip_combat_confirm(self):
        if not self._confirm("Skip Combat", "You have attackers available.\nSkip the entire combat phase?"):
            return
        self._skip_combat()

    def _skip_combat(self):
        # Advance through all combat phases directly to Main2
        combat_tokens = {'BEGINCOMBAT', 'DECLAREATTACKERS', 'DECLAREBLOCKERS', 'COMBATDAMAGE', 'ENDCOMBAT'}
        safety = 0
        while safety < 15:
            safety += 1
            tok = self._normalize_phase_token()
            if tok == 'MAIN2':
                break
            # If we haven't reached combat yet, step forward until we enter or pass it
            if tok == 'MAIN1' or tok in combat_tokens:
                self.api.advance_phase()
            else:
                # Not in pre-combat or combat (maybe already past)
                break
        if hasattr(self.play_area, "refresh_board"):
            self.play_area.refresh_board()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close(); return
        self.api.handle_key(e.key())
        if hasattr(self.play_area, "refresh_board"):
            self.play_area.refresh_board()

    def closeEvent(self, ev):
        try:
            self.api.handle_game_window_closed()
        except Exception:
            pass
        super().closeEvent(ev)
        super().closeEvent(ev)

    def _confirm(self, title: str, text: str):  # ADDED
        from PySide6.QtWidgets import QMessageBox
        return QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) == QMessageBox.Yes

    def open(self):
        mw = getattr(self.api, 'w', None)
        if mw:
            try:
                g = mw.frameGeometry()
                # Ensure not smaller than minimums
                w = max(1280, int(g.width() * 0.9))
                h = max(720, int(g.height() * 0.9))
                self.resize(w, h)
                c = g.center()
                self.move(c.x() - self.width() // 2, c.y() - self.height() // 2)
            except Exception:
                pass
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.show()
        self.raise_()
        self.activateWindow()
        # Drop always-on-top shortly after showing so both windows stay interactive
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))
        self.raise_()
        self.activateWindow()
        # Drop always-on-top shortly after showing so both windows stay interactive
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))
        self.raise_()
        self.activateWindow()
        # Drop always-on-top shortly after showing so both windows stay interactive
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))
        QTimer.singleShot(400, lambda: (self.setWindowFlag(Qt.WindowStaysOnTopHint, False), self.show()))
