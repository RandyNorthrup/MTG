from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPlainTextEdit,
    QTabWidget, QToolBar, QComboBox, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QEvent
from engine.phase_hooks import PHASE_SEQUENCE, PHASE_STEPS, _PHASE_ORDER

class GameDebugWindow(QWidget):
    """
    Enhanced debug utility for in-process game debugging.
    Shows main/board window sizes, game state, stack, and provides command buttons and dropdowns.
    """
    def __init__(self, game, play_area, main_window, board_window=None):
        super().__init__()
        self.setWindowTitle("Game Debug")
        self.game = game
        self.play_area = play_area
        self.main_window = main_window
        self.board_window = board_window
        self._last_board_size = None
        self.controller = getattr(main_window, 'controller', getattr(main_window, 'api', None) and getattr(main_window.api, 'controller', None))

        # Install event filters for resize/close tracking
        if self.main_window:
            self.main_window.installEventFilter(self)
        if self.board_window:
            self.board_window.installEventFilter(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(8,8,8,8)
        root.setSpacing(8)

        # --- Toolbar with command buttons and dropdowns ---
        toolbar = QToolBar("Debug")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # Phase/step controls
        from engine.phase_hooks import advance_phase, advance_step, set_phase
        btn_next_phase = QPushButton("Next Phase")
        btn_next_phase.setToolTip("Advance to next phase")
        btn_next_phase.clicked.connect(lambda: self._advance_phase())
        toolbar.addWidget(btn_next_phase)

        btn_next_step = QPushButton("Next Step")
        btn_next_step.setToolTip("Advance to next step")
        btn_next_step.clicked.connect(lambda: advance_step(self.controller))
        toolbar.addWidget(btn_next_step)

        btn_new_turn = QPushButton("New Turn")
        btn_new_turn.setToolTip("Start a new turn")
        btn_new_turn.clicked.connect(self._start_new_turn)
        toolbar.addWidget(btn_new_turn)

        btn_clear_stack = QPushButton("Clear Stack")
        btn_clear_stack.setToolTip("Clear the stack")
        btn_clear_stack.clicked.connect(lambda: self.controller.clear_stack())
        toolbar.addWidget(btn_clear_stack)

        btn_log_phase = QPushButton("Log Phase")
        btn_log_phase.setToolTip("Log phase to stdout")
        btn_log_phase.clicked.connect(lambda: self.controller.log_phase())
        toolbar.addWidget(btn_log_phase)

        # Mana pool controls
        mana_colors = ['W', 'U', 'B', 'R', 'G', 'C']
        for color in mana_colors:
            btn = QPushButton(f"+{color}")
            btn.setToolTip(f"Add 1 {color} mana to selected player")
            btn.clicked.connect(lambda _, c=color: self._add_color_mana(c))
            toolbar.addWidget(btn)

        # Dropdown: select player
        self.player_dropdown = QComboBox()
        self._refresh_player_dropdown()
        toolbar.addWidget(QLabel("Player:"))
        toolbar.addWidget(self.player_dropdown)

        # Dropdown: select phase (use only valid canonical phases)
        self.phase_dropdown = QComboBox()
        self.phase_dropdown.addItems(_PHASE_ORDER)
        toolbar.addWidget(QLabel("Set Phase:"))
        toolbar.addWidget(self.phase_dropdown)
        btn_set_phase = QPushButton("Set")
        btn_set_phase.setToolTip("Set phase to selected value")
        btn_set_phase.clicked.connect(lambda: self._set_phase())
        toolbar.addWidget(btn_set_phase)

        # Command: set life
        toolbar.addWidget(QLabel("Set Life:"))
        self.life_input = QLineEdit()
        self.life_input.setFixedWidth(40)
        self.life_input.setPlaceholderText("life")
        toolbar.addWidget(self.life_input)
        btn_set_life = QPushButton("Set")
        btn_set_life.setToolTip("Set selected player's life")
        btn_set_life.clicked.connect(self._set_life)
        toolbar.addWidget(btn_set_life)

        root.addWidget(toolbar)

        # --- Info labels ---
        self.info_lbl = QLabel(self._build_info_text())
        self.info_lbl.setStyleSheet("font:10pt monospace;")
        self.info_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        root.addWidget(self.info_lbl)

        self.main_size_lbl = QLabel(self._main_size_text())
        self.main_size_lbl.setStyleSheet("font:9pt monospace;color:#5a5;")
        root.addWidget(self.main_size_lbl)

        self.board_size_lbl = QLabel(self._board_size_text())
        self.board_size_lbl.setStyleSheet("font:9pt monospace;color:#66c;")
        root.addWidget(self.board_size_lbl)

        # --- Log/Verbose Tabs ---
        self._tabs = QTabWidget()
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(140)
        self.log_box.setStyleSheet("font:10pt Consolas,monospace;")
        self.verbose_box = QPlainTextEdit()
        self.verbose_box.setReadOnly(True)
        self.verbose_box.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._tabs.addTab(self.log_box, "Log")
        self._tabs.addTab(self.verbose_box, "Verbose")
        root.addWidget(self._tabs, 1)

        # Verbose refresh
        verb_row = QHBoxLayout()
        self.btn_refresh_verbose = QPushButton("Refresh Verbose")
        self.btn_refresh_verbose.setToolTip("Refresh verbose game state dump")
        self.btn_refresh_verbose.clicked.connect(self._refresh_verbose)
        verb_row.addWidget(self.btn_refresh_verbose)
        verb_row.addStretch(1)
        root.addLayout(verb_row)
        self._refresh_verbose()

        # Periodic info refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._periodic_refresh)
        self._refresh_timer.start(1200)

        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self._update_size_labels()

    # --- Toolbar helpers ---
    def _refresh_player_dropdown(self):
        self.player_dropdown.clear()
        for p in getattr(self.game, 'players', []):
            self.player_dropdown.addItem(f"P{p.player_id}: {p.name}", p.player_id)

    def _set_life(self):
        try:
            idx = self.player_dropdown.currentIndex()
            pid = self.player_dropdown.itemData(idx)
            val = int(self.life_input.text())
            pl = next(p for p in self.game.players if p.player_id == pid)
            pl.life = val
            self._append_log(f"[life] set P{pid} to {val}")
        except Exception as ex:
            self._append_log(f"[life][err] {ex}")
        self._safe_refresh()

    def _add_color_mana(self, color):
        try:
            idx = self.player_dropdown.currentIndex()
            pid = self.player_dropdown.itemData(idx)
            pl = next(p for p in self.game.players if p.player_id == pid)
            pool = getattr(pl, 'mana_pool', None)
            if pool is None:
                pool = {}
                setattr(pl, 'mana_pool', pool)
            pool[color] = pool.get(color, 0) + 1
            self._append_log(f"[mana] +1{color} -> {pool}")
        except Exception as ex:
            self._append_log(f"[mana][err] {ex}")

    def _start_new_turn(self):
        try:
            if hasattr(self.controller, "start_new_turn"):
                self.controller.start_new_turn()
                self._append_log("[turn] started new turn")
            else:
                self._append_log("[turn][err] Controller missing start_new_turn")
        except Exception as ex:
            self._append_log(f"[turn][err] {ex}")
        self._safe_refresh()

    # --- Size text helpers ---
    def _main_size_text(self):
        if not self.main_window:
            return "Main Window: (unavailable)"
        sz = self.main_window.size()
        return f"Main Window: {sz.width()} x {sz.height()}"

    def _board_size_text(self):
        if self.board_window and self.board_window.isVisible():
            sz = self.board_window.size()
            self._last_board_size = (sz.width(), sz.height())
            return f"Board Window: {sz.width()} x {sz.height()}"
        if self._last_board_size:
            w, h = self._last_board_size
            return f"Board Window: (closed, last {w} x {h})"
        return "Board Window: (closed)"

    def _update_size_labels(self):
        if self.main_size_lbl:
            self.main_size_lbl.setText(self._main_size_text())
        if self.board_size_lbl:
            self.board_size_lbl.setText(self._board_size_text())

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Resize, QEvent.Close):
            if obj is self.main_window or obj is self.board_window:
                self._update_size_labels()
        return super().eventFilter(obj, ev)

    def _periodic_refresh(self):
        self.info_lbl.setText(self._build_info_text())
        self._update_size_labels()
        self._refresh_player_dropdown()
        self._refresh_verbose(auto=True)

    # --- UI helpers ---
    def _append_log(self, msg):
        self.log_box.append(msg)

    def _build_info_text(self):
        try:
            ap = getattr(self.game, 'active_player', 0)
            phase = getattr(self.game, 'phase', '?')
            players_lines = []
            for p in getattr(self.game, 'players', []):
                hand = len(getattr(p, 'hand', []))
                lib = len(getattr(p, 'library', []))
                bf = len(getattr(p, 'battlefield', []))
                players_lines.append(f"P{p.player_id} {p.name} L:{p.life} H:{hand} Lib:{lib} BF:{bf}")
            players_str = "\n".join(players_lines) if players_lines else "No players"
            stack_size = 0
            stack = getattr(self.game, 'stack', None)
            if isinstance(stack, list):
                stack_size = len(stack)
            elif hasattr(stack, 'items'):
                stack_size = len(stack.items)
            elif stack and hasattr(stack, '__len__'):
                stack_size = len(stack)
            return (f"Active: P{ap}  Phase: {phase}  Stack:{stack_size}\n"
                    f"{players_str}")
        except Exception as ex:
            return f"[err building info] {ex}"

    def _safe_refresh(self):
        if self.play_area and hasattr(self.play_area, 'refresh_board'):
            try:
                self.play_area.refresh_board()
            except Exception:
                pass
        self.info_lbl.setText(self._build_info_text())
        self._update_size_labels()

    def _refresh_verbose(self, auto=False):
        if auto and self._tabs.currentWidget() is not self.verbose_box:
            return
        self.verbose_box.setPlainText(self._build_verbose_dump())

    def _safe_len(self, obj):
        try:
            if callable(obj):
                obj = obj()
            return len(obj)
        except Exception:
            return 0

    def _iter_cards(self, obj, limit=None):
        try:
            if callable(obj):
                obj = obj()
            if isinstance(obj, dict):
                obj = obj.values()
            if not hasattr(obj, '__iter__'):
                return []
            seq = list(obj)
            return seq if limit is None else seq[:limit]
        except Exception:
            return []

    def _build_verbose_dump(self):
        g = self.game
        if not g:
            return "No game loaded."
        lines = []
        try:
            lines.append(f"GameID: {getattr(g, 'game_id', 'N/A')}")
            lines.append(f"Phase: {getattr(g, 'phase', '?')}")
            lines.append(f"Active Player Index: {getattr(g, 'active_player', '?')}")
            # Stack
            stack_obj = getattr(g, 'stack', None)
            stack_items = []
            try:
                if stack_obj:
                    if isinstance(stack_obj, list):
                        stack_items = stack_obj
                    else:
                        cand = getattr(stack_obj, 'items', stack_obj)
                        if callable(cand):
                            cand = cand()
                        if hasattr(cand, '__iter__'):
                            stack_items = list(cand)
            except Exception:
                stack_items = []
            lines.append(f"Stack ({len(stack_items)}):")
            for i, it in enumerate(stack_items):
                lines.append(f"  {i}: {getattr(it, 'name', type(it).__name__)}")
            # Players
            lines.append("Players:")
            for p in getattr(g, 'players', []):
                hand = getattr(p, 'hand', [])
                library = getattr(p, 'library', [])
                grave = getattr(p, 'graveyard', [])
                bf = getattr(p, 'battlefield', [])
                hand_n = self._safe_len(hand)
                lib_n = self._safe_len(library)
                gy_n = self._safe_len(grave)
                bf_n = self._safe_len(bf)
                lines.append(
                    f"  [{getattr(p,'player_id','?')}] {p.name}  Life={getattr(p,'life','?')} "
                    f"Hand={hand_n} Lib={lib_n} GY={gy_n} BF={bf_n}"
                )
                try:
                    cmdr = getattr(p, 'commander', None)
                    if cmdr:
                        lines.append(f"     Commander: {getattr(cmdr,'name','(unnamed)')}")
                except Exception:
                    pass
                for perm in self._iter_cards(bf, limit=12):
                    try:
                        status = []
                        if getattr(perm, 'tapped', False): status.append('T')
                        if getattr(perm, 'summoning_sick', getattr(perm,'summoning_sickness', False)): status.append('S')
                        pt = ""
                        if 'Creature' in getattr(perm, 'types', []):
                            pt = f" [{getattr(perm,'power','?')}/{getattr(perm,'toughness','?')}]"
                        lines.append(f"       - {perm.name}{pt}{' ('+', '.join(status)+')' if status else ''}")
                    except Exception:
                        continue
            ap = getattr(g, 'active_player', None)
            attackers = []
            if ap is not None and ap < self._safe_len(getattr(g, 'players', [])):
                try:
                    pl = g.players[ap]
                    for c in self._iter_cards(getattr(pl, 'battlefield', [])):
                        try:
                            if 'Creature' not in getattr(c, 'types', []): continue
                            if getattr(c, 'tapped', False): continue
                            sick = getattr(c, 'summoning_sick', getattr(c,'summoning_sickness', False))
                            if sick and not (getattr(c,'haste',False) or
                                             'Haste' in getattr(c,'keywords',[]) or
                                             'haste' in getattr(c,'text','').lower()):
                                continue
                            attackers.append(getattr(c,'name','?'))
                        except Exception:
                            pass
                except Exception:
                    pass
            lines.append(f"Potential Attackers ({len(attackers)}): {', '.join(attackers) if attackers else '-'}")
        except Exception as ex:
            lines.append(f"[ERROR building verbose dump (handled)]: {ex}")
        return "\n".join(lines)

    # --- Button actions ---
    def _set_phase(self):
        from engine.phase_hooks import set_phase
        try:
            phase = self.phase_dropdown.currentText()
            set_phase(self.controller, phase)
            self._append_log(f"[phase] set to {phase}")
        except Exception as ex:
            self._append_log(f"[phase][err] {ex}")
        self._safe_refresh()

    def _advance_phase(self):
        try:
            # Only use valid canonical phases for advancement
            current = getattr(self.controller, "current_phase", None)
            if current not in _PHASE_ORDER:
                idx = 0
            else:
                idx = _PHASE_ORDER.index(current)
            next_idx = (idx + 1) % len(_PHASE_ORDER)
            next_phase = _PHASE_ORDER[next_idx]
            from engine.phase_hooks import set_phase
            set_phase(self.controller, next_phase)
            self._append_log(f"[phase] advanced to {next_phase}")
        except Exception as ex:
            self._append_log(f"[phase][err] {ex}")
        self._safe_refresh()

    def _ai_step(self):
        try:
            if self.controller:
                # force immediate tick ignoring cooldown by resetting timer
                self.controller._last_auto_step_s = 0
                self.controller.tick(self._safe_refresh)
            else:
                self._append_log("[ai] controller missing")
        except Exception as ex:
            self._append_log(f"[ai][err] {ex}")
        self._safe_refresh()

    def _resolve_stack(self):
        try:
            if hasattr(self.game, 'stack') and self.game.stack.can_resolve():
                self.game.stack.resolve_top(self.game)
                self._append_log("[stack] resolved top")
            else:
                self._append_log("[stack] nothing to resolve")
        except Exception as ex:
            self._append_log(f"[stack][err] {ex}")
        self._safe_refresh()

    def _log_phase(self):
        try:
            if self.controller:
                self.controller.log_phase()
            self._append_log("[log] phase logged to stdout")
        except Exception as ex:
            self._append_log(f"[log][err] {ex}")

    def _add_life(self):
        try:
            ap = self.game.active_player
            pl = self.game.players[ap]
            pl.life += 5
            self._append_log(f"[life] +5 to {pl.name} now {pl.life}")
        except Exception as ex:
            self._append_log(f"[life][err] {ex}")
        self._safe_refresh()

    def _draw_card(self):
        try:
            ap = self.game.active_player
            pl = self.game.players[ap]
            if pl.library:
                card = pl.library.pop(0)
                pl.hand.append(card)
                self._append_log(f"[draw] {pl.name} drew {getattr(card,'name','?')}")
            else:
                self._append_log("[draw] library empty")
        except Exception as ex:
            self._append_log(f"[draw][err] {ex}")
        self._safe_refresh()

    def _add_mana(self):
        try:
            ap = self.game.active_player
            pl = self.game.players[ap]
            pool = getattr(pl, 'mana_pool', None)
            if pool is None:
                pool = {}
                setattr(pl, 'mana_pool', pool)
            pool['C'] = pool.get('C', 0) + 1
            self._append_log(f"[mana] +1C -> {pool}")
        except Exception as ex:
            self._append_log(f"[mana][err] {ex}")

    def _refresh_board(self):
        self._append_log("[ui] manual refresh")
        self._safe_refresh()

    def _dump_state(self):
        try:
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
            ap = self.game.active_player
            lines = [f"[dump] phase={getattr(self.game,'phase','?')} active={ap}"]
            for p in self.game.players:
                lines.append(f"P{p.player_id}:{p.name} life={p.life} hand={len(getattr(p,'hand',[]))} lib={len(getattr(p,'library',[]))}")
            if hasattr(self.game, 'stack') and getattr(self.game.stack,'items',None):
                lines.append(f"Stack size={len(self.game.stack.items)}")
            self._append_log("\n".join(lines))
        except Exception as ex:
            self._append_log(f"[dump][err] {ex}")
