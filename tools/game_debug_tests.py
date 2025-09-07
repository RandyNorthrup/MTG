from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QMessageBox, QLineEdit, QTabWidget, QPlainTextEdit
from PySide6.QtCore import Qt, QTimer

class GameDebugWindow(QWidget):
    """
    Lightweight in-process debug utility.
    All operations are best-effort and wrapped with guards so failures
    do not crash the app.
    """
    def __init__(self, game, play_area, main_window):
        super().__init__()
        self.setWindowTitle("Game Debug")
        self.game = game
        self.play_area = play_area
        self.main_window = main_window
        self.controller = getattr(main_window, 'controller', None)

        root = QVBoxLayout(self)
        root.setContentsMargins(8,8,8,8)
        root.setSpacing(6)

        self.info_lbl = QLabel(self._build_info_text())
        self.info_lbl.setStyleSheet("font:10pt monospace;")
        self.info_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        root.addWidget(self.info_lbl)

        # Row 1 – flow
        row1 = QHBoxLayout()
        row1.addWidget(self._mk_btn("Advance Phase", self._advance_phase))
        row1.addWidget(self._mk_btn("AI Step", self._ai_step))
        row1.addWidget(self._mk_btn("Resolve Stack", self._resolve_stack))
        row1.addWidget(self._mk_btn("Force Log Phase", self._log_phase))
        root.addLayout(row1)

        # Row 2 – player actions
        row2 = QHBoxLayout()
        row2.addWidget(self._mk_btn("+5 Life (AP)", self._add_life))
        row2.addWidget(self._mk_btn("Draw Card (AP)", self._draw_card))
        row2.addWidget(self._mk_btn("Add Debug Mana", self._add_mana))
        row2.addWidget(self._mk_btn("Refresh Board", self._refresh_board))
        root.addLayout(row2)

        # Row 3 – misc
        row3 = QHBoxLayout()
        row3.addWidget(self._mk_btn("Dump State", self._dump_state))
        row3.addWidget(self._mk_btn("Close", self.close))
        row3.addStretch(1)
        root.addLayout(row3)

        # --- NEW: window size display row ---
        size_row = QHBoxLayout()
        self.main_size_box = QLineEdit(); self.main_size_box.setReadOnly(True)
        self.game_size_box = QLineEdit(); self.game_size_box.setReadOnly(True)
        for w, lab in [(self.main_size_box, "Main"), (self.game_size_box, "Game")]:
            w.setFixedWidth(150)
            size_row.addWidget(QLabel(lab+":"), 0)
            size_row.addWidget(w, 0)
        size_row.addStretch(1)
        root.addLayout(size_row)

        # --- NEW: tabs for Log / Verbose ---
        self._tabs = QTabWidget()
        # Preserve existing log box: assume self.log_box already created above; if not, adapt below.
        # If log_box not yet created at this point in original file, move this block after its creation.
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

        # Control row for verbose refresh
        verb_row = QHBoxLayout()
        self.btn_refresh_verbose = QPushButton("Refresh Verbose")
        self.btn_refresh_verbose.clicked.connect(self._refresh_verbose)
        verb_row.addWidget(self.btn_refresh_verbose)
        verb_row.addStretch(1)
        root.addLayout(verb_row)
        # Initial fill
        self._refresh_verbose()

        # Periodic info refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_info)
        self._refresh_timer.start(1200)

        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)  # ADDED keep on top
        self._update_window_sizes()  # ADDED initial size fill

    # --- UI helpers ---
    def _mk_btn(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _append_log(self, msg):
        self.log_box.append(msg)

    def _update_info(self):
        self.info_lbl.setText(self._build_info_text())
        self._update_window_sizes()
        self._refresh_verbose(auto=True)

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
            if hasattr(self.game, 'stack') and hasattr(self.game.stack, 'items'):
                stack_size = len(self.game.stack.items)
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
        self._update_info()

    # --- NEW ---
    def _update_window_sizes(self):
        try:
            mw = self.main_window
            gw = getattr(getattr(mw, 'api', None), '_game_window', None)
            if mw:
                self.main_size_box.setText(f"{mw.width()}x{mw.height()}")
            if gw:
                self.game_size_box.setText(f"{gw.width()}x{gw.height()}")
            else:
                self.game_size_box.setText("(closed)")
        except Exception:
            pass

    # --- NEW safe helpers (placed near other helpers / before _build_verbose_dump) ---
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

    # --- NEW: Verbose dump helpers ---
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
                # Commander
                try:
                    cmdr = getattr(p, 'commander', None)
                    if cmdr:
                        lines.append(f"     Commander: {getattr(cmdr,'name','(unnamed)')}")
                except Exception:
                    pass
                # Battlefield detail (limit)
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
            # Potential attackers (active player)
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

    def _refresh_verbose(self, auto=False):
        # If user switched away and auto refresh, skip heavy repaint
        if auto and self._tabs.currentWidget() is not self.verbose_box:
            return
        self.verbose_box.setPlainText(self._build_verbose_dump())

    # --- Button actions ---
    def _advance_phase(self):
        try:
            if self.controller:
                self.controller.advance_phase()
            elif hasattr(self.game, 'next_phase'):
                self.game.next_phase()
            self._append_log("[phase] advanced")
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
