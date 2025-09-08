import os
from PySide6.QtWidgets import (QWidget, QMenu, QVBoxLayout, QDialog, QLabel, QPushButton,
                               QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox)
from PySide6.QtGui import (QPainter, QPen, QColor, QPixmap, QMouseEvent, QPaintEvent)
from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from image_cache import ensure_card_image
from engine.mana import ManaPool, parse_mana_cost
from ui.card_renderer import CARD_W, CARD_H, ZOOM_W, ZOOM_H, PADDING  # ADDED

try:
    from shiboken6 import isValid as _q_is_valid
except Exception:
    def _q_is_valid(o):
        if o is None:
            return False
        try:
            o.objectName()
            return True
        except Exception:
            return False

# Layout / style constants
SIDEBAR_W = 130
TOP_BG = QColor(125,129,134)
BOT_BG = QColor(48,51,55)  # ensure defined (used by painter sections)

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
            return pm
    _CARD_BACK_CACHE = None
    return None

class _ManaSelectDialog(QDialog):
    """Simple dialog: user taps lands to pay remaining cost (colored/generic)."""
    def __init__(self, parent, player, cost_dict, produce_cb):
        super().__init__(parent)
        self.setWindowTitle("Select Mana Sources")
        self.player = player
        self.cost_remaining = dict(cost_dict)
        self.produce_cb = produce_cb
        lay = QVBoxLayout(self)
        self.info_lbl = QLabel(self._fmt()); lay.addWidget(self.info_lbl)
        self.listw = QListWidget()
        for perm in player.battlefield:
            if 'Land' in perm.card.types and not perm.tapped:
                it = QListWidgetItem(perm.card.name); it.setData(Qt.UserRole, perm)
                self.listw.addItem(it)
        lay.addWidget(self.listw)
        row = QHBoxLayout()
        self.tap_btn = QPushButton("Tap Selected"); self.tap_btn.clicked.connect(self._tap_one)
        self.done_btn = QPushButton("Done"); self.done_btn.clicked.connect(self.accept)
        row.addWidget(self.tap_btn); row.addWidget(self.done_btn); lay.addLayout(row)
    def _fmt(self):
        return "Remaining cost: " + " ".join(f"{k}:{v}" for k,v in self.cost_remaining.items() if v>0 or not self.cost_remaining) or "None"
    def _tap_one(self):
        it = self.listw.currentItem()
        if not it: return
        perm = it.data(Qt.UserRole)
        if perm.tapped: return
        nm = perm.card.name.lower()
        sym = 'G'
        for t,s in [('plains','W'),('island','U'),('swamp','B'),('mountain','R'),('forest','G')]:
            if t in nm: sym = s; break
        self.produce_cb(perm, sym)
        if sym in self.cost_remaining and self.cost_remaining[sym]>0:
            self.cost_remaining[sym]-=1
        else:
            # reduce generic fallback if tracked under 'G'
            if self.cost_remaining.get('G',0)>0:
                self.cost_remaining['G']-=1
        it.setText(it.text()+" (tapped)")
        self.info_lbl.setText(self._fmt())
    def remaining(self):
        return sum(v for v in self.cost_remaining.values() if v>0)

class PlayArea(QWidget):
    def __init__(self, game, api=None, parent=None):
        super().__init__(parent)
        self.game = game
        self.api = api  # ADDED: reference to GameAppAPI or controller
        self.setMouseTracking(True)
        self.hover_card = None
        self.playable_ids = set()
        self.zoom_enabled = True
        self.zoom_pos = QPoint(20,20)
        self._zoom_drag = False
        self._zoom_drag_offset = QPoint()
        self._render_slots: list[tuple[QRect,object]] = []
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_playables)
        self._refresh_timer.start(400)
        self._update_playables()

    def set_game(self, game):
        self.game = game
        self._update_playables()
        self.update()

    def set_api(self, api):
        self.api = api

    def refresh_board(self):
        self.update()

    def enable_drag_and_drop(self):
        pass

    # ---------- Layout helpers ----------
    def _layout(self):
        """
          [Opponent Battlefield/Lands]
          [Player Battlefield/Lands]
          [Player Hand]
        """
        w = self.width()
        h = self.height()
        sidebar_w = SIDEBAR_W
        top = QRect(sidebar_w, 0, w - sidebar_w, int(h * 0.38))
        bottom = QRect(sidebar_w, top.bottom(), w - sidebar_w, int(h * 0.38))
        hand_rect = QRect(sidebar_w, bottom.bottom(), w - sidebar_w, h - bottom.bottom())
        def zone(area: QRect):
            pad = 8
            inner = area.adjusted(pad, pad, -pad, -pad)
            split = int(inner.height() * 0.68)
            bf = QRect(inner.left(), inner.top(), inner.width(), split)
            lands = QRect(inner.left(), bf.bottom() + 6, inner.width(), max(0, inner.bottom() - (bf.bottom() + 6)))
            return {"battlefield": bf, "lands": lands}
        return {
            "sidebar": QRect(0, 0, SIDEBAR_W, h),
            "top": top,
            "bottom": bottom,
            "hand": hand_rect,
            "top_zones": zone(top),
            "bottom_zones": zone(bottom)
        }

    # ---------- Commander damage / counters ----------
    def _commander_damage_received(self, player):
        tracker = getattr(player,'commander_tracker',None)
        if not tracker or not hasattr(tracker,'damage'): return 0
        total=0
        for (atk,dfd),val in tracker.damage.items():
            if dfd == player.player_id:
                total += val
        return total

    def _player_counters_text(self, player):
        counters = getattr(player,'counters',None)
        if not counters: return ""
        out=[]
        for k,v in counters.items():
            out.append(f"{k}:{v}")
            if len(out)>=4: break
        return " ".join(out)

    # ---------- Paint ----------
    def paintEvent(self, e: QPaintEvent):
        p = QPainter(self)
        layout = self._layout()
        p.fillRect(self.rect(), QColor(20,20,22))
        p.fillRect(layout["top"], TOP_BG)
        p.fillRect(layout["bottom"], BOT_BG)
        self._render_slots = []
        self._draw_sidebars(p, layout["sidebar"])
        if len(self.game.players) > 1:
            self._draw_battle_zones(p, self.game.players[1], layout["top_zones"], True)
        self._draw_battle_zones(p, self.game.players[0], layout["bottom_zones"], False)
        self._draw_hand(p, layout["hand"])
        if self.hover_card and self.zoom_enabled:
            self._draw_zoom(p, self.hover_card)
        p.end()
        if hasattr(self.game, 'combat'):
            self._draw_combat_overlays()

    # ---------- Sidebars ----------
    def _draw_sidebars(self, p: QPainter, rect: QRect):
        mid = rect.height()//2
        top = QRect(rect.left(), rect.top(), rect.width(), mid)
        bottom = QRect(rect.left(), mid, rect.width(), rect.height()-mid)
        if len(self.game.players)>1:
            self._draw_player_panel(p, self.game.players[1], top, True)
        else:
            p.save()
            p.fillRect(top, QColor(32,32,36))
            p.setPen(QPen(QColor(70,70,80),1))
            p.drawRect(top.adjusted(0,0,-1,-1))
            p.setPen(QColor(210,210,215))
            p.drawText(top.adjusted(6,6,-6,-6), Qt.AlignCenter,
                       "Waiting for opponent...\n(Host Start will add AI if none)")
            p.restore()
        if self.game.players:
            self._draw_player_panel(p, self.game.players[0], bottom, False)

    def _draw_player_panel(self, p: QPainter, player, r: QRect, is_top: bool):
        p.save()
        p.fillRect(r, QColor(32,32,36) if is_top else QColor(38,38,42))
        p.setPen(QPen(QColor(70,70,80),1)); p.drawRect(r.adjusted(0,0,-1,-1))
        pad=6
        avatar = QRect(r.left()+pad, r.top()+pad, r.width()-2*pad, 78)
        p.fillRect(avatar, QColor(55,55,65))
        p.setPen(QColor(235,235,240)); p.drawRect(avatar.adjusted(0,0,-1,-1))
        p.drawText(avatar, Qt.AlignCenter, (player.name[:2] or "?").upper())
        y = avatar.bottom()+6
        lh = 16
        p.setPen(QColor(220,220,230))
        line = f"Life:{player.life}"
        cmd = self._commander_damage_received(player)
        if cmd: line += f" Cmd:{cmd}"
        p.drawText(r.left()+pad, y+lh-3, line); y+=lh
        p.drawText(r.left()+pad, y+lh-3, f"Lib:{len(player.library)} GY:{len(player.graveyard)}"); y+=lh
        p.drawText(r.left()+pad, y+lh-3, f"Hand:{len(player.hand)}"); y+=lh
        ctr = self._player_counters_text(player)
        if ctr: p.drawText(r.left()+pad, y+lh-3, ctr)
        if player.commander:
            cmdbox = QRect(r.left()+pad, r.bottom()-54-pad, r.width()-2*pad, 54)
            p.fillRect(cmdbox, QColor(50,50,62))
            p.setPen(QPen(QColor(95,95,110),1)); p.drawRect(cmdbox.adjusted(0,0,-1,-1))
            p.setPen(QColor(230,230,240))
            p.drawText(cmdbox.adjusted(4,4,-4,-4), Qt.TextWordWrap, player.commander.name[:30])
        p.restore()

    # ---------- Battlefield / Lands ----------
    def _draw_battle_zones(self, p: QPainter, player, zones, is_opponent: bool):
        p.save()
        p.setPen(QPen(QColor(60,60,70),1))
        p.drawRect(zones["battlefield"]); p.drawRect(zones["lands"])
        lands, others = [], []
        for perm in player.battlefield:
            (lands if 'Land' in perm.card.types else others).append(perm)
        self._draw_perm_grid(p, others, zones["battlefield"], register=not is_opponent)
        self._draw_perm_grid(p, lands, zones["lands"], register=not is_opponent)
        if is_opponent:
            self._draw_opponent_hand(p, player, zones["battlefield"])
        p.restore()

    def _draw_perm_grid(self, p: QPainter, perms, rect: QRect, register: bool):
        if not perms: return
        cols = max(1, rect.width()//(CARD_W+8))
        x0 = rect.left()+6; y0 = rect.top()+6
        for i, perm in enumerate(perms):
            r = QRect(x0+(i%cols)*(CARD_W+8), y0+(i//cols)*(CARD_H+8), CARD_W, CARD_H)
            hover = (self.hover_card is perm.card)
            playable = (perm.card.id in self.playable_ids)
            self._draw_card(p, r, perm.card, hover=hover, playable=playable)
            if register: self._register_card(r, perm.card)
            if getattr(perm,'tapped',False):
                p.setPen(QPen(QColor(200,50,50),3)); p.drawLine(r.topLeft(), r.bottomRight())

    def _draw_opponent_hand(self, p: QPainter, player, battlefield_rect: QRect):
        size = len(player.hand)
        if size==0: return
        y = battlefield_rect.top() - CARD_H - 6
        if y<4: y=4
        max_show = min(size,10)
        total_w = max_show*CARD_W + (max_show-1)*6
        start_x = battlefield_rect.left() + (battlefield_rect.width()-total_w)//2
        back = _load_card_back()
        scaled = back.scaled(CARD_W,CARD_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation) if back else None
        for i in range(max_show):
            r = QRect(start_x + i*(CARD_W+6), y, CARD_W, CARD_H)
            if scaled:
                p.save(); p.setClipRect(r); p.drawPixmap(r, scaled); p.restore()
                p.setPen(QPen(QColor(15,15,18),2)); p.drawRoundedRect(r,6,6)
            else:
                p.setPen(QColor(110,110,140),2); p.setBrush(QColor(40,40,55))
                p.drawRoundedRect(r,6,6)
        if size>max_show:
            p.setPen(QColor(230,230,235))
            p.drawText(battlefield_rect.left()+6, y+CARD_H+14, f"+{size-max_show}")

    # ---------- Hand ----------
    def _draw_hand(self, p: QPainter, rect: QRect):
        ps = self.game.players[0]
        n = len(ps.hand)
        if n==0: return
        spacing = min(28, max(10, (rect.width()-2*PADDING-CARD_W)//max(1,n)))
        x = rect.left()+PADDING
        y = rect.top()+8
        for card in ps.hand:
            r = QRect(x,y,CARD_W,CARD_H)
            hover = (card is self.hover_card)
            playable = (card.id in self.playable_ids)
            self._draw_card(p, r, card, hover=hover, playable=playable)
            self._register_card(r, card)
            x += spacing
        if self.hover_card and all(c is not self.hover_card for _,c in self._render_slots):
            self.hover_card=None

    # ---------- Hover mapping ----------
    def _register_card(self, rect: QRect, card):
        self._render_slots.append((QRect(rect), card))
    def _hit_test_card(self, pt: QPoint):
        for r,c in reversed(self._render_slots):
            if r.contains(pt): return c
        return None

    # ---------- Mouse ----------
    def mouseMoveEvent(self, e: QMouseEvent):
        pt = e.position().toPoint()
        if self._zoom_drag:
            new_pos = pt - self._zoom_drag_offset
            new_pos.setX(max(0, min(self.width()-ZOOM_W, new_pos.x())))
            new_pos.setY(max(0, min(self.height()-ZOOM_H, new_pos.y())))
            if new_pos != self.zoom_pos:
                self.zoom_pos = new_pos; self.update()
            return
        card = self._hit_test_card(pt)
        if card is not self.hover_card:
            self.hover_card = card
            self.update()

    def mousePressEvent(self, e: QMouseEvent):
        pt = e.position().toPoint()
        # All gameplay logic below is now delegated to api/controller
        if not self.api:
            return

        # Example: Declare attackers
        if self._is_combat_declare_phase() and e.button() == Qt.LeftButton and self.game.active_player == 0:
            card = self._hit_test_card(pt)
            if card:
                self.api.toggle_attacker(card)
                self.update()
                return

        # Example: Commit attackers
        if self._is_combat_declare_phase() and e.button() == Qt.RightButton and self.game.active_player == 0:
            if self.api.has_attackers():
                self.api.commit_attackers()
                self.update()
                return

        # Example: Blocking
        if self._is_combat_block_phase() and e.button() == Qt.LeftButton:
            card = self._hit_test_card(pt)
            if not card:
                return
            self.api.handle_blocker_click(card)
            self.update()
            return

        if self._is_combat_block_phase() and e.button() == Qt.RightButton:
            self.api.commit_blockers()
            self.update()
            return

        # Phase bar click / zoom drag
        if e.button() == Qt.LeftButton:
            if self.hover_card and self._zoom_rect().contains(pt):
                self._zoom_drag = True
                self._zoom_drag_offset = pt - self.zoom_pos
                return
            ph = self._phase_hit_test(pt)
            if ph:
                self.api.advance_to_phase(ph)
                self.update()
                return

        # Hand play
        if e.button() != Qt.LeftButton:
            return
        hand_rect = self._layout()["hand"]
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
            self.api.play_land(card)
        else:
            self.api.cast_spell(card)
        self._update_playables()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button()==Qt.LeftButton and self._zoom_drag:
            self._zoom_drag = False

    # ---------- Helpers ----------
    def _autotap_and_cast(self, card):
        ps = self.game.players[0]
        if not hasattr(ps,'mana_pool'):
            ps.mana_pool = ManaPool()
        pool: ManaPool = ps.mana_pool
        cost_dict = parse_mana_cost(getattr(card,'mana_cost_str',None))
        if not cost_dict:
            generic_need = card.mana_cost if isinstance(card.mana_cost,int) else 0
            if generic_need:
                cost_dict = {'G': generic_need}
        colored_needs = {c:n for c,n in cost_dict.items() if c in ('W','U','B','R','G') and n>0}
        def land_color(perm):
            n = perm.card.name.lower()
            for t,c in [('plains','W'),('island','U'),('swamp','B'),('mountain','R'),('forest','G')]:
                if t in n: return c
            return 'G'
        untapped = [perm for perm in ps.battlefield if 'Land' in perm.card.types and not perm.tapped]
        for color, need in list(colored_needs.items()):
            while need>0:
                found = next((l for l in untapped if land_color(l)==color), None)
                if not found: break
                self.game.tap_for_mana(0, found)
                pool.add(color,1)
                untapped.remove(found); need-=1
            colored_needs[color]=need
        remaining = cost_dict.get('G',0) + sum(rem for rem in colored_needs.values() if rem>0)
        for land in list(untapped):
            if remaining<=0: break
            sym = land_color(land)
            self.game.tap_for_mana(0, land)
            pool.add(sym,1)
            remaining -=1
        if not pool.can_pay(cost_dict):
            return
        pool.pay(cost_dict)
        self.game.cast_spell(0, card)

    def _update_playables(self):
        try:
            ps = self.game.players[0]
            self.playable_ids = {c.id for c in ps.find_playable()}
        except Exception:
            self.playable_ids = set()
        self.update()

    # ---------- Card rendering ----------
    def _draw_card(self, p: QPainter, rect: QRect, card, *, hover=False, playable=False):
        img = ensure_card_image(card.id)
        drew = False
        if img and os.path.exists(img):
            pm = QPixmap(img)
            if not pm.isNull():
                scaled = pm.scaled(rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                p.save(); p.setClipRect(rect); p.drawPixmap(rect, scaled); p.restore(); drew=True
        if not drew:
            p.save()
            p.setBrush(QColor(245,245,245)); p.setPen(QPen(Qt.black,2))
            p.drawRoundedRect(rect,6,6)
            p.setPen(Qt.black); p.drawText(rect.adjusted(4,4,-4,-4), Qt.AlignLeft|Qt.AlignTop, card.name[:18])
            p.setPen(QColor(70,70,70)); p.drawText(rect.adjusted(4,22,-4,-4), Qt.AlignLeft|Qt.AlignTop, "/".join(card.types)[:18])
            if "Creature" in card.types and card.power is not None:
                p.setPen(Qt.black)
                p.drawText(rect.adjusted(0,0,-6,-4), Qt.AlignRight|Qt.AlignBottom, f"{card.power}/{card.toughness}")
            p.restore()
        if hover or playable:
            p.save()
            if hover and playable:
                p.setPen(QPen(QColor(0,220,255),4)); p.drawRoundedRect(rect,6,6)
                p.setPen(QPen(QColor(0,200,70),2)); p.drawRoundedRect(rect.adjusted(3,3,-3,-3),5,5)
            elif hover:
                p.setPen(QPen(QColor(0,220,255),3)); p.drawRoundedRect(rect,6,6)
            else:
                p.setPen(QPen(QColor(0,180,0),3)); p.drawRoundedRect(rect,6,6)
            p.restore()
        if "Creature" in card.types and card.power is not None:
            base_p, base_t = card.power, card.toughness
            eff_p = getattr(card,'eff_power', base_p)
            eff_t = getattr(card,'eff_toughness', base_t)
            changed = (eff_p!=base_p) or (eff_t!=base_t)
            box = QRect(rect.right()-42, rect.bottom()-28, 40,24)
            p.save(); p.fillRect(box, QColor(0,0,0,160))
            p.setPen(QColor(120,255,120) if changed else QColor(255,255,255))
            p.drawText(box, Qt.AlignCenter, f"{eff_p}/{eff_t}")
            p.restore()

    # Zoom
    def _zoom_rect(self):
        return QRect(self.zoom_pos.x(), self.zoom_pos.y(), ZOOM_W, ZOOM_H)

    def _draw_zoom(self, p: QPainter, card):
        rect = self._zoom_rect()
        p.save()
        p.setPen(QPen(QColor(40,40,45),2)); p.setBrush(QColor(12,12,14,230))
        p.drawRoundedRect(rect,10,10)
        img = ensure_card_image(card.id)
        if img and os.path.exists(img):
            pm = QPixmap(img)
            if not pm.isNull():
                inner = rect.adjusted(8,8,-8,-90)
                scaled = pm.scaled(inner.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                dest = QRect(inner.left()+(inner.width()-scaled.width())//2,
                             inner.top()+(inner.height()-scaled.height())//2,
                             scaled.width(), scaled.height())
                p.drawPixmap(dest, scaled)
        text = (getattr(card,'text','') or '').strip()
        footer_min = 74
        lines = max(1, min(8, len(text.splitlines()) or 1))
        extra = 14*lines + (8 if text else 0)
        footer_h = min(footer_min+extra, rect.height()//2)
        footer = QRect(rect.left()+6, rect.bottom()-footer_h-6, rect.width()-12, footer_h)
        p.fillRect(footer, QColor(0,0,0,170))
        name_r = QRect(footer.left()+4, footer.top()+2, footer.width()-8, 20)
        p.setPen(QColor(235,235,240)); p.drawText(name_r, Qt.AlignLeft|Qt.AlignVCenter, card.name)
        types_r = QRect(footer.left()+4, name_r.bottom()+2, footer.width()-8, 18)
        p.setPen(QColor(180,180,190)); p.drawText(types_r, Qt.AlignLeft|Qt.AlignVCenter, "/".join(card.types))
        if text:
            rules_r = QRect(footer.left()+4, types_r.bottom()+4, footer.width()-8, footer.bottom()-(types_r.bottom()+8))
            p.setPen(QColor(210,210,215))
            p.drawText(rules_r, Qt.TextWordWrap|Qt.AlignTop|Qt.AlignLeft, text)
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
        p = QPainter(self); p.setBrush(Qt.NoBrush)
        # attackers
        for r, card in self._render_slots:
            if any(getattr(perm.card,'id',None)==card.id for perm in combat.state.attackers):
                p.setPen(QPen(QColor(220,40,40),4))
                p.drawRoundedRect(r.adjusted(1,1,-1,-1),6,6)
        p.setPen(QPen(QColor(60,140,240),4))
        for _, blist in combat.state.blockers.items():
            for perm in blist:
                for r, card in self._render_slots:
                    if card.id == perm.card.id:
                        p.drawRoundedRect(r.adjusted(1,1,-1,-1),6,6)
        p.end()

    # --- Helper methods for phase/turn checks (now just UI helpers) ---
    def _is_combat_declare_phase(self):
        return self.game.phase.upper() == 'COMBAT_DECLARE'

    def _is_combat_block_phase(self):
        return self.game.phase.upper() == 'COMBAT_BLOCK'


def _find_perm(game, card_id):
    for p in game.players:
        for perm in p.battlefield:
            if getattr(perm.card,'id',None)==card_id:
                return perm
    return None

def get_default_window_size():
    """Return (width, height) for the main window."""
    return (1280, 900)  # or whatever default you want
    for perm in p.battlefield:
            if getattr(perm.card,'id',None)==card_id:
                return perm
    return None

def get_default_window_size():
    """Return (width, height) for the main window."""
    return (1280, 900)  # or whatever default you want
