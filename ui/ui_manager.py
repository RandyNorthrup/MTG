import os
from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtGui import (QPainter, QMouseEvent, QPaintEvent, QPen, QColor,
                           QPixmap)
from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from config import CARD_W, CARD_H, HAND_HEIGHT, PADDING, ZOOM_W, ZOOM_H
from image_cache import ensure_card_image
from engine.mana import ManaPool, parse_mana_cost, GENERIC_KEY  # NEW
from engine.combat import attach_combat  # NEW

# Layout / style constants
SIDEBAR_W = 130
PHASE_BAR_H = 34
TOP_BG = QColor(125,129,134)
BOT_BG = QColor(48,51,55)

# Card back (opponent hand) image
CARD_BACK_FILE = os.path.join('data', 'images', 'card_back.png')
_CARD_BACK_CACHE: QPixmap | None = None

# Hover zoom options
SHOW_CARD_ID = False  # hide card id in preview pane

def _load_card_back():
    global _CARD_BACK_CACHE
    if _CARD_BACK_CACHE is not None:
        return _CARD_BACK_CACHE
    if os.path.exists(CARD_BACK_FILE):
        pm = QPixmap(CARD_BACK_FILE)
        if not pm.isNull():
            _CARD_BACK_CACHE = pm
            return _CARD_BACK_CACHE
    _CARD_BACK_CACHE = None
    return None


class PlayArea(QWidget):
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.setMouseTracking(True)

        self.hover_card = None
        self.playable_ids = set()

        # Hover zoom / preview
        self.zoom_enabled = True
        self.zoom_pos = QPoint(20, 20)
        self._zoom_drag = False
        self._zoom_drag_offset = QPoint(0, 0)

        # Slot registry for accurate hover mapping (player cards only)
        self._render_slots: list[tuple[QRect, object]] = []

        # Periodic playable update
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_playables)
        self._refresh_timer.start(400)
        self._update_playables()

    # ---------- Phases ----------
    def _phase_sequence(self):
        return ["UNTAP", "UPKEEP", "DRAW", "MAIN1", "COMBAT", "MAIN2", "END"]

    # ---------- Layout ----------
    def _layout(self):
        """
        Layout with phase bar relocated just above the hand:
          [Opponent Battlefield/Lands]
          [Player Battlefield/Lands]
          [Phase Bar]
          [Player Hand]
        """
        w = self.width()
        h = self.height()
        phase_h = PHASE_BAR_H
        hand_rect = QRect(SIDEBAR_W, h - HAND_HEIGHT, w - SIDEBAR_W, HAND_HEIGHT)

        # Space above hand & phase bar
        usable = h - HAND_HEIGHT - phase_h
        top_h = usable // 2
        bottom_h = usable - top_h

        top_area = QRect(SIDEBAR_W, 0, w - SIDEBAR_W, top_h)
        bottom_area = QRect(SIDEBAR_W, top_area.bottom(), w - SIDEBAR_W, bottom_h)
        phase_bar = QRect(SIDEBAR_W, bottom_area.bottom(), w - SIDEBAR_W, phase_h)

        def zone_slices(area: QRect):
            pad = 8
            bf = area.adjusted(pad, pad, -pad, -pad)
            split = int(bf.height() * 0.68)
            battlefield = QRect(bf.left(), bf.top(), bf.width(), split)
            lands = QRect(bf.left(), battlefield.bottom() + 6, bf.width(),
                          max(0, bf.bottom() - (battlefield.bottom() + 6)))
            return {"battlefield": battlefield, "lands": lands}

        return {
            "sidebar": QRect(0, 0, SIDEBAR_W, h),
            "top": top_area,
            "bottom": bottom_area,
            "phase": phase_bar,
            "hand": hand_rect,
            "top_zones": zone_slices(top_area),
            "bottom_zones": zone_slices(bottom_area)
        }

    # ---------- Commander damage / counters ----------
    def _commander_damage_received(self, player):
        tracker = getattr(player, 'commander_tracker', None)
        if not tracker or not hasattr(tracker, 'damage'):
            return 0
        total = 0
        for (atk, dfd), val in tracker.damage.items():
            if dfd == player.player_id:
                total += val
        return total

    def _player_counters_text(self, player):
        counters = getattr(player, 'counters', None)
        if not counters:
            return ""
        out = []
        for k, v in counters.items():
            out.append(f"{k}:{v}")
            if len(out) >= 4:
                break
        return " ".join(out)

    # ---------- Paint ----------
    def paintEvent(self, e: QPaintEvent):
        p = QPainter(self)
        try:
            self._render_slots = []
            layout = self._layout()
            p.fillRect(self.rect(), QColor(20, 20, 22))
            p.fillRect(layout["top"], TOP_BG)
            p.fillRect(layout["bottom"], BOT_BG)
            self._draw_sidebars(p, layout["sidebar"])
            self._draw_battle_zones(p, self.game.players[1], layout["top_zones"], is_opponent=True)
            self._draw_battle_zones(p, self.game.players[0], layout["bottom_zones"], is_opponent=False)
            self._draw_phase_bar(p, layout["phase"])
            self._draw_hand(p, layout["hand"])
            if self.hover_card and self.zoom_enabled:
                self._draw_zoom(p, self.hover_card)
        finally:
            p.end()

        if hasattr(self.game, 'combat'):
            self._draw_combat_overlays()

    # ---------- Sidebars ----------
    def _draw_sidebars(self, p: QPainter, rect: QRect):
        mid = rect.height() // 2
        top_panel = QRect(rect.left(), rect.top(), rect.width(), mid)
        bot_panel = QRect(rect.left(), mid, rect.width(), rect.height() - mid)
        self._draw_player_panel(p, self.game.players[1], top_panel, True)
        self._draw_player_panel(p, self.game.players[0], bot_panel, False)

    def _draw_player_panel(self, p: QPainter, player, r: QRect, is_top: bool):
        p.save()
        p.fillRect(r, QColor(32, 32, 36) if is_top else QColor(38, 38, 42))
        p.setPen(QPen(QColor(70, 70, 80), 1))
        p.drawRect(r.adjusted(0, 0, -1, -1))

        pad = 6
        avatar = QRect(r.left() + pad, r.top() + pad, r.width() - 2 * pad, 80)
        p.fillRect(avatar, QColor(55, 55, 65))
        p.setPen(QColor(235, 235, 240))
        p.drawRect(avatar.adjusted(0, 0, -1, -1))
        p.drawText(avatar, Qt.AlignCenter, (player.name[:2] or "?").upper())

        y = avatar.bottom() + 6
        line_h = 16
        p.setPen(QColor(220, 220, 230))
        life_line = f"Life:{player.life}"
        cmd = self._commander_damage_received(player)
        if cmd:
            life_line += f" Cmd:{cmd}"
        p.drawText(r.left() + pad, y + line_h - 3, life_line)
        y += line_h
        p.drawText(r.left() + pad, y + line_h - 3, f"Lib:{len(player.library)} GY:{len(player.graveyard)}")
        y += line_h
        p.drawText(r.left() + pad, y + line_h - 3, f"Hand:{len(player.hand)}")
        y += line_h
        counters = self._player_counters_text(player)
        if counters:
            p.drawText(r.left() + pad, y + line_h - 3, counters)

        if player.commander:
            cmdbox = QRect(r.left() + pad, r.bottom() - 54 - pad, r.width() - 2 * pad, 54)
            p.fillRect(cmdbox, QColor(50, 50, 62))
            p.setPen(QPen(QColor(95, 95, 110), 1))
            p.drawRect(cmdbox.adjusted(0, 0, -1, -1))
            p.setPen(QColor(230, 230, 240))
            p.drawText(cmdbox.adjusted(4, 4, -4, -4), Qt.TextWordWrap, player.commander.name[:28])
        p.restore()

    # ---------- Battlefield / Lands ----------
    def _draw_battle_zones(self, p: QPainter, player, zones, is_opponent: bool):
        p.save()
        p.setPen(QPen(QColor(60, 60, 70), 1))
        p.drawRect(zones["battlefield"])
        p.drawRect(zones["lands"])
        lands, others = [], []
        for perm in player.battlefield:
            (lands if 'Land' in perm.card.types else others).append(perm)
        self._draw_perm_grid(p, others, zones["battlefield"], register=not is_opponent)
        self._draw_perm_grid(p, lands, zones["lands"], register=not is_opponent)
        if is_opponent:
            self._draw_opponent_hand(p, player, zones["battlefield"])
        p.restore()

    def _draw_perm_grid(self, p: QPainter, perms, rect: QRect, register: bool):
        if not perms:
            return
        cols = max(1, rect.width() // (CARD_W + 8))
        x0 = rect.left() + 6
        y0 = rect.top() + 6
        for i, perm in enumerate(perms):
            r = QRect(x0 + (i % cols) * (CARD_W + 8),
                      y0 + (i // cols) * (CARD_H + 8),
                      CARD_W, CARD_H)
            hover = (self.hover_card is perm.card)
            playable = (perm.card.id in self.playable_ids)
            self._draw_card(p, r, perm.card, hover=hover, playable=playable)
            if register:
                self._register_card(r, perm.card)
            if perm.tapped:
                p.setPen(QPen(QColor(200, 50, 50), 3))
                p.drawLine(r.topLeft(), r.bottomRight())

    def _draw_opponent_hand(self, p: QPainter, player, battlefield_rect: QRect):
        size = len(player.hand)
        if size == 0:
            return
        y = battlefield_rect.top() - CARD_H - 6
        if y < 4:
            y = 4
        max_show = min(size, 10)
        total_w = max_show * CARD_W + (max_show - 1) * 6
        start_x = battlefield_rect.left() + (battlefield_rect.width() - total_w) // 2
        back_pix = _load_card_back()
        if back_pix:
            scaled = back_pix.scaled(CARD_W, CARD_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        else:
            scaled = None
        pen = QPen(QColor(15, 15, 18), 2)
        for i in range(max_show):
            r = QRect(start_x + i * (CARD_W + 6), y, CARD_W, CARD_H)
            if scaled:
                p.save()
                p.setClipRect(r)
                p.drawPixmap(r, scaled)
                p.restore()
                p.setPen(pen)
                p.drawRoundedRect(r, 6, 6)
            else:
                p.setPen(QPen(QColor(110, 110, 140), 2))
                p.setBrush(QColor(40, 40, 55))
                p.drawRoundedRect(r, 6, 6)
                p.setPen(QColor(170, 180, 205))
                p.drawText(r.adjusted(4, 4, -4, -4), Qt.AlignCenter, "📘")
        if size > max_show:
            p.setPen(QColor(230, 230, 235))
            p.drawText(battlefield_rect.left() + 6, y + CARD_H + 14, f"+{size - max_show}")

    # ---------- Phase Bar ----------
    def _draw_phase_bar(self, p: QPainter, rect: QRect):
        phases = self._phase_sequence()
        current = self.game.phase.upper()
        if current.startswith("COMBAT"):
            current = "COMBAT"
        seg_w = rect.width() // len(phases)
        p.save()
        p.fillRect(rect, QColor(25, 25, 28))
        font = p.font()
        font.setPointSize(10)
        p.setFont(font)
        for i, ph in enumerate(phases):
            seg = QRect(rect.left() + i * seg_w, rect.top(), seg_w, rect.height())
            active = (ph == current)
            p.setPen(QPen(QColor(55, 55, 65), 1))
            p.fillRect(seg.adjusted(2, 4, -2, -4), QColor(120, 90, 40) if active else QColor(50, 50, 55))
            p.setPen(QColor(255, 255, 255) if active else QColor(200, 200, 205))
            p.drawText(seg, Qt.AlignCenter, ph)
        p.restore()

    def _phase_hit_test(self, pt: QPoint):
        layout = self._layout()
        bar = layout["phase"]
        if not bar.contains(pt):
            return None
        phases = self._phase_sequence()
        seg_w = bar.width() // len(phases)
        idx = (pt.x() - bar.left()) // seg_w
        return phases[idx] if 0 <= idx < len(phases) else None

    # ---------- Hand ----------
    def _draw_hand(self, p: QPainter, rect: QRect):
        ps = self.game.players[0]
        n = len(ps.hand)
        if n == 0:
            return
        spacing = min(28, max(10, (rect.width() - 2 * PADDING - CARD_W) // max(1, n)))
        x = rect.left() + PADDING
        y = rect.top() + 8
        for card in ps.hand:
            r = QRect(x, y, CARD_W, CARD_H)
            hover = (card is self.hover_card)
            playable = (card.id in self.playable_ids)
            self._draw_card(p, r, card, hover=hover, playable=playable)
            self._register_card(r, card)
            x += spacing
        if self.hover_card and all(c is not self.hover_card for _, c in self._render_slots):
            self.hover_card = None

    # ---------- Hover mapping ----------
    def _register_card(self, rect: QRect, card):
        self._render_slots.append((QRect(rect), card))

    def _hit_test_card(self, pt: QPoint):
        for r, c in reversed(self._render_slots):
            if r.contains(pt):
                return c
        return None

    # ---------- Mouse ----------
    def mouseMoveEvent(self, e: QMouseEvent):
        pt = e.position().toPoint()
        if self._zoom_drag:
            new_pos = pt - self._zoom_drag_offset
            new_pos.setX(max(0, min(self.width() - ZOOM_W, new_pos.x())))
            new_pos.setY(max(0, min(self.height() - ZOOM_H, new_pos.y())))
            if new_pos != self.zoom_pos:
                self.zoom_pos = new_pos
                self.update()
            return
        card = self._hit_test_card(pt)
        if card is not self.hover_card:
            self.hover_card = card
            self.update()

    def mousePressEvent(self, e: QMouseEvent):
        pt = e.position().toPoint()
        phase = self.game.phase.upper()
        # Ensure combat manager attached
        attach_combat(self.game)

        # Declare attackers (active player = 0)
        if phase == 'COMBAT_DECLARE' and e.button() == Qt.LeftButton and self.game.active_player == 0:
            card = self._hit_test_card(pt)
            if card:
                # find permanent object
                perm = _find_perm(self.game, card.id)
                if perm:
                    self.game.combat.toggle_attacker(0, perm)
                    self.update()
                    return

        # Commit attackers with right-click anywhere (simplified)
        if phase == 'COMBAT_DECLARE' and e.button() == Qt.RightButton and self.game.active_player == 0:
            if self.game.combat.state.attackers:
                self.game.combat.attackers_committed()
                # advance to blocking phase (reuse existing phase sequence if available)
                self.game.phase = 'COMBAT_BLOCK'
                self.update()
                return

        # Blocking assignment (defender assumed player 1)
        if phase == 'COMBAT_BLOCK' and e.button() == Qt.LeftButton:
            card = self._hit_test_card(pt)
            if not card:
                return
            perm = _find_perm(self.game, card.id)
            if not perm:
                return
            # Sequence: first click selects blocker (owned by defending player), second click attacker.
            sel = getattr(self, '_pending_blocker', None)
            if sel is None:
                # select blocker if belongs to defending player
                if perm.card.controller_id == 1:
                    self._pending_blocker = perm
            else:
                # attempt to pair with attacker
                if perm in self.game.combat.state.attackers:
                    self.game.combat.toggle_blocker(1, self._pending_blocker, perm)
                    self._pending_blocker = None
                else:
                    # replaced blocker selection
                    if perm.card.controller_id == 1:
                        self._pending_blocker = perm
            self.update()
            return

        # Commit blockers (right-click) -> move to damage
        if phase == 'COMBAT_BLOCK' and e.button() == Qt.RightButton:
            self.game.phase = 'COMBAT_DAMAGE'
            # Resolve damage immediately
            self.game.combat.assign_and_deal_damage()
            # Advance to MAIN2 (simplified)
            self.game.phase = 'MAIN2'
            self.update()
            return

        # Fallback to existing interaction
        # Phase bar click
        if e.button() == Qt.LeftButton:
            # Drag preview?
            if self.hover_card and self._zoom_rect().contains(pt):
                self._zoom_drag = True
                self._zoom_drag_offset = pt - self.zoom_pos
                return
            ph = self._phase_hit_test(pt)
            if ph:
                seq = self._phase_sequence()
                cur = self.game.phase.upper()
                if cur.startswith("COMBAT"):
                    cur = "COMBAT"
                if ph in seq:
                    cur_i = seq.index(cur)
                    tgt_i = seq.index(ph)
                    if tgt_i > cur_i:
                        for _ in range(tgt_i - cur_i):
                            if self.game.stack.can_resolve():
                                break
                            self.game.next_phase()
                        self.update()
                        return
        # Hand interaction (play card)
        if e.button() != Qt.LeftButton:
            return
        layout = self._layout()
        hand_rect = layout["hand"]
        if not hand_rect.contains(pt):
            return
        if self.game.active_player != 0 or self.game.phase not in ('MAIN1', 'MAIN2'):
            return
        card = self._hit_test_card(pt)
        if not card or card not in self.game.players[0].hand:
            return
        if card.id not in self.playable_ids:
            return
        if 'Land' in card.types:
            self.game.play_land(0, card)
        else:
            self._autotap_and_cast(card)
        self._update_playables()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton and self._zoom_drag:
            self._zoom_drag = False

    # ---------- Helpers ----------
    def _autotap_and_cast(self, card):
        ps = self.game.players[0]
        # Ensure mana pool on player
        if not hasattr(ps, 'mana_pool'):
            ps.mana_pool = ManaPool()
        pool: ManaPool = ps.mana_pool

        # Parse colored cost (fallback: numeric generic)
        cost_dict = parse_mana_cost(getattr(card, 'mana_cost_str', None))
        if not cost_dict:
            # fallback to existing integer generic cost
            generic_need = card.mana_cost if isinstance(card.mana_cost, int) else 0
            if generic_need:
                cost_dict = {GENERIC_KEY: generic_need}

        # STEP 1: Identify unmet colored needs
        colored_needs = {c: n for c, n in cost_dict.items() if c in ('W','U','B','R','G') and n > 0}

        # STEP 2: Tap lands to satisfy colored needs first
        def land_produces(perm):
            name = perm.card.name.lower()
            if 'forest' in name: return 'G'
            if 'island' in name: return 'U'
            if 'swamp' in name: return 'B'
            if 'mountain' in name: return 'R'
            if 'plains' in name: return 'W'
            return GENERIC_KEY

        # Only untapped lands
        untapped_lands = [perm for perm in ps.battlefield if 'Land' in perm.card.types and not perm.tapped]

        # Colored pass
        for color, need in list(colored_needs.items()):
            while need > 0:
                found = next((l for l in untapped_lands if land_produces(l) == color), None)
                if not found:
                    break
                self.game.tap_for_mana(0, found)
                pool.add(color, 1)
                untapped_lands.remove(found)
                need -= 1
            colored_needs[color] = need  # remaining (if any)

        # STEP 3: Generic requirements (including leftover colored shortfall)
        remaining_generic = cost_dict.get(GENERIC_KEY, 0)
        # Any unmet colored becomes extra generic requirement (very rough fallback)
        for c, rem in colored_needs.items():
            if rem > 0:
                remaining_generic += rem
                cost_dict[c] -= rem  # colored portion we couldn't satisfy

        if remaining_generic > 0:
            # Tap any remaining lands for generic
            for land in list(untapped_lands):
                if remaining_generic <= 0:
                    break
                sym = land_produces(land)
                self.game.tap_for_mana(0, land)
                pool.add(sym, 1 if sym != GENERIC_KEY else 1)
                remaining_generic -= 1
                untapped_lands.remove(land)
            # Update cost dict generic to reflect actual need
            cost_dict[GENERIC_KEY] = cost_dict.get(GENERIC_KEY,0)

        # STEP 4: Attempt payment
        if not pool.can_pay(cost_dict):
            # Casting fails (insufficient mana) -> no rollback for prototype
            return
        pool.pay(cost_dict)

        # STEP 5: Cast
        self.game.cast_spell(0, card)

    def _update_playables(self):
        try:
            ps = self.game.players[0]
            self.playable_ids = {c.id for c in ps.find_playable()}
        except Exception:
            self.playable_ids = set()
        self.update()

    # ---------- Card & Zoom Rendering ----------
    def _draw_card(self, p: QPainter, rect: QRect, card, *, hover: bool=False, playable: bool=False):
        """
        Draw card with distinct border states:
          - hover only: cyan border
          - playable only: green border
          - hover + playable: cyan outer, green inner
        """
        img_path = ensure_card_image(card.id)
        drew_image = False
        if img_path and os.path.exists(img_path):
            pm = QPixmap(img_path)
            if not pm.isNull():
                scaled = pm.scaled(rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                p.save()
                p.setClipRect(rect)
                p.drawPixmap(rect, scaled)
                p.restore()
                drew_image = True

        if not drew_image:
            # Fallback vector
            p.save()
            p.setBrush(QColor(245, 245, 245))
            p.setPen(QPen(Qt.black, 2))
            p.drawRoundedRect(rect, 6, 6)
            p.setPen(Qt.black)
            p.drawText(rect.adjusted(4, 4, -4, -4), Qt.AlignLeft | Qt.AlignTop, card.name[:18])
            p.setPen(QColor(70, 70, 70))
            p.drawText(rect.adjusted(4, 22, -4, -4), Qt.AlignLeft | Qt.AlignTop, "/".join(card.types)[:18])
            if "Creature" in card.types and card.power is not None:
                p.setPen(Qt.black)
                p.drawText(rect.adjusted(0, 0, -6, -4),
                           Qt.AlignRight | Qt.AlignBottom,
                           f"{card.power}/{card.toughness}")
            p.restore()

        # Borders
        if hover and playable:
            # Dual border: outer cyan, inner green
            p.save()
            p.setPen(QPen(QColor(0, 220, 255), 4))
            p.drawRoundedRect(rect.adjusted(0,0,0,0), 6, 6)
            p.setPen(QPen(QColor(0, 200, 70), 2))
            p.drawRoundedRect(rect.adjusted(3,3,-3,-3), 5, 5)
            p.restore()
        elif hover:
            p.save()
            p.setPen(QPen(QColor(0, 220, 255), 3))
            p.drawRoundedRect(rect, 6, 6)
            p.restore()
        elif playable:
            p.save()
            p.setPen(QPen(QColor(0, 180, 0), 3))
            p.drawRoundedRect(rect, 6, 6)
            p.restore()

        # Creature PT overlay (only once, show effective if present)
        if "Creature" in card.types and card.power is not None:
            base_p = card.power
            base_t = card.toughness
            eff_p = getattr(card, 'eff_power', base_p)
            eff_t = getattr(card, 'eff_toughness', base_t)
            text = f"{eff_p}/{eff_t}"
            changed = (eff_p != base_p) or (eff_t != base_t)
            pt_box = QRect(rect.right() - 42, rect.bottom() - 28, 40, 24)
            p.save()
            p.fillRect(pt_box, QColor(0, 0, 0, 160))
            p.setPen(QColor(120,255,120) if changed else QColor(255,255,255))
            p.drawText(pt_box, Qt.AlignCenter, text)
            p.restore()

    def _zoom_rect(self):
        return QRect(self.zoom_pos.x(), self.zoom_pos.y(), ZOOM_W, ZOOM_H)

    def _draw_zoom(self, p: QPainter, card):
        rect = self._zoom_rect()
        p.save()
        p.setPen(QPen(QColor(40, 40, 45), 2))
        p.setBrush(QColor(12, 12, 14, 230))
        p.drawRoundedRect(rect, 10, 10)
        img_path = ensure_card_image(card.id)
        if img_path and os.path.exists(img_path):
            pm = QPixmap(img_path)
            if not pm.isNull():
                inner = rect.adjusted(8, 8, -8, -90)  # reserve more space for text footer
                scaled = pm.scaled(inner.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                dest = QRect(
                    inner.left() + (inner.width() - scaled.width()) // 2,
                    inner.top() + (inner.height() - scaled.height()) // 2,
                    scaled.width(),
                    scaled.height()
                )
                p.drawPixmap(dest, scaled)

        # Footer with name, types (id removed)
        card_text = (getattr(card, 'text', '') or '').strip()
        footer_min = 74
        extra = 0
        if card_text:
            # rough height estimation (wrap later): ~14 px per line, assume 4 lines max for now
            est_lines = max(1, min(8, sum(1 for _ in card_text.splitlines()) or 1))
            extra = 14 * est_lines + 8
        footer_h = min(footer_min + extra, rect.height() // 2)
        footer = QRect(rect.left() + 6, rect.bottom() - footer_h - 6, rect.width() - 12, footer_h)
        p.fillRect(footer, QColor(0, 0, 0, 170))

        # Name
        name_rect = QRect(footer.left() + 4, footer.top() + 2, footer.width() - 8, 20)
        p.setPen(QColor(235, 235, 240))
        p.drawText(name_rect, Qt.TextSingleLine | Qt.AlignLeft | Qt.AlignVCenter, card.name)

        # Types line (no id appended now)
        types_rect = QRect(footer.left() + 4, name_rect.bottom() + 2, footer.width() - 8, 18)
        p.setPen(QColor(180, 180, 190))
        type_line = "/".join(card.types)
        p.drawText(types_rect, Qt.AlignLeft | Qt.AlignVCenter, type_line)

        # Rules text (wrapped) below
        if card_text:
            rules_rect = QRect(footer.left() + 4, types_rect.bottom() + 4,
                               footer.width() - 8, footer.bottom() - (types_rect.bottom() + 8))
            p.setPen(QColor(210, 210, 215))
            p.drawText(rules_rect, Qt.TextWordWrap | Qt.AlignTop | Qt.AlignLeft, card_text)

        p.restore()

    # ---------- Target Overlay ----------
    def _target_matches_hint(self, card, hint: str | None):
        if not hint:
            return True
        if hint == 'creature':
            return 'Creature' in card.types
        if hint == 'player':
            return False  # (no player card object here)
        return True

    def _draw_target_overlay(self):
        p = QPainter(self)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0,200,255,60))
        for r, card in self._render_slots:
            if self._target_matches_hint(card, self.game.rules_engine.pending_activation[2].target_hint):
                p.drawRoundedRect(r,6,6)
        p.end()

    def _draw_combat_overlays(self):
        combat = self.game.combat
        p = QPainter(self)
        # Attacker highlight (red)
        p.setBrush(Qt.NoBrush)
        for r, card in self._render_slots:
            # find perm
            if any(getattr(perm.card, 'id', None) == card.id for perm in combat.state.attackers):
                p.setPen(QPen(QColor(220,40,40), 4))
                p.drawRoundedRect(r.adjusted(1,1,-1,-1), 6,6)
        # Blocker highlight (blue) + link line to first blocker
        p.setPen(QPen(QColor(60,140,240), 4))
        for atk_id, blist in combat.state.blockers.items():
            for perm in blist:
                for r, card in self._render_slots:
                    if card.id == perm.card.id:
                        p.drawRoundedRect(r.adjusted(1,1,-1,-1),6,6)
        p.end()

# --- helper outside class ---
def _find_perm(game, card_id):
    for p in game.players:
        for perm in p.battlefield:
            if getattr(perm.card, 'id', None) == card_id:
                return perm
    return None
def _find_perm(game, card_id):
    for p in game.players:
        for perm in p.battlefield:
            if getattr(perm.card, 'id', None) == card_id:
                return perm
    return None
