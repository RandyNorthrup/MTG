from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QMouseEvent, QPaintEvent, QPen, QColor
from PySide6.QtCore import Qt, QTimer, QRect
from config import CARD_W, CARD_H, HAND_HEIGHT, BATTLEFIELD_HEIGHT, SCREEN_W, SCREEN_H, PADDING, ZOOM_W, ZOOM_H
# The engine game object is passed in from main
# This file used to host the pygame UIManager; now only PlayArea is required.

class PlayArea(QWidget):
    """
    Central play surface:
      - Renders both battlefields, player hand, commanders.
      - Left-click playable card in hand to play/cast (auto-taps lands for generic cost).
      - Hover shows zoom panel (top-left).
      - Scoreboard toggled via 'S' (handled in MainWindow).
    """
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.setMouseTracking(True)
        self.hover_card = None
        self.playable_ids = set()
        self.scoreboard_visible = False
        self.zoom_enabled = True
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_playables)
        self._refresh_timer.start(400)
        self._update_playables()

    # -------- Internal helpers --------
    def _update_playables(self):
        try:
            ps = self.game.players[0]
            self.playable_ids = {c.id for c in ps.find_playable()}
        except Exception:
            self.playable_ids = set()
        self.update()

    def _hand_rects(self):
        ps = self.game.players[0]
        n = len(ps.hand)
        if n == 0:
            return []
        spacing = min(20, max(6, (self.width() - 2*PADDING - CARD_W) // max(1, n)))
        x = PADDING
        y = self.height() - HAND_HEIGHT + 12
        rects = []
        for _ in range(n):
            rects.append(QRect(x, y, CARD_W, CARD_H))
            x += spacing
        return rects

    def _card_index_at(self, rects, pos):
        for i, r in enumerate(rects):
            if r.contains(pos):
                return i
        return None

    def _autotap_and_cast(self, card):
        ps = self.game.players[0]
        need = card.mana_cost if isinstance(card.mana_cost, int) else 0
        for perm in list(ps.battlefield):
            if need <= 0:
                break
            if 'Land' in perm.card.types and not perm.tapped:
                self.game.tap_for_mana(0, perm)
                need -= 1
        self.game.cast_spell(0, card)

    # -------- Qt Events --------
    def mouseMoveEvent(self, e: QMouseEvent):
        ps = self.game.players[0]
        rects = self._hand_rects()
        idx = self._card_index_at(rects, e.position().toPoint())
        self.hover_card = ps.hand[idx] if idx is not None else None
        self.update()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() != Qt.LeftButton:
            return
        # Only allow actions in main phases as active player 0
        if self.game.active_player != 0 or self.game.phase not in ('MAIN1', 'MAIN2'):
            return
        ps = self.game.players[0]
        rects = self._hand_rects()
        idx = self._card_index_at(rects, e.position().toPoint())
        if idx is None:
            return
        card = ps.hand[idx]
        if card.id not in self.playable_ids:
            return
        if 'Land' in card.types:
            self.game.play_land(0, card)
        else:
            self._autotap_and_cast(card)
        self._update_playables()

    def paintEvent(self, e: QPaintEvent):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(18,18,25))

        # Opponent battlefield (top)
        self._draw_battlefield(p, self.game.players[1].battlefield, PADDING + 40)
        # Player battlefield (bottom area above hand)
        bf_y = self.height() - HAND_HEIGHT - BATTLEFIELD_HEIGHT
        self._draw_battlefield(p, self.game.players[0].battlefield, bf_y)
        # Hand
        self._draw_hand(p)
        # Commanders
        self._draw_commanders(p)
        # Scoreboard
        if self.scoreboard_visible:
            self._draw_scoreboard(p)
        # Hover zoom
        if self.hover_card and self.zoom_enabled:
            self._draw_zoom(p, self.hover_card)

    # -------- Drawing helpers --------
    def _draw_battlefield(self, p: QPainter, battlefield, y: int):
        x = PADDING
        for perm in battlefield:
            r = QRect(x, y, CARD_W, CARD_H)
            self._draw_card(p, r, perm.card, highlight=False)
            if perm.tapped:
                pen = QPen(QColor(200,50,50), 3)
                p.setPen(pen)
                p.drawLine(r.topLeft(), r.bottomRight())
            x += CARD_W + 12

    def _draw_hand(self, p: QPainter):
        ps = self.game.players[0]
        rects = self._hand_rects()
        for i, r in enumerate(rects):
            card = ps.hand[i]
            self._draw_card(p, r, card, highlight=(card.id in self.playable_ids))

    def _draw_commanders(self, p: QPainter):
        p0 = self.game.players[0]
        p1 = self.game.players[1]
        if p0.commander:
            r0 = QRect(PADDING, self.height() - HAND_HEIGHT - CARD_H - 10, CARD_W, CARD_H)
            self._draw_card(p, r0, p0.commander, p0.commander in p0.command)
        if p1.commander:
            r1 = QRect(self.width() - CARD_W - PADDING, 10, CARD_W, CARD_H)
            self._draw_card(p, r1, p1.commander, p1.commander in p1.command)

    def _draw_scoreboard(self, p: QPainter):
        p.save()
        p.setPen(QColor(230,230,230))
        bg = QRect(8,8,260, 22*len(self.game.players)+12)
        p.fillRect(bg, QColor(0,0,0,140))
        y = 26
        for pl in self.game.players:
            line = f"{pl.name}  L:{pl.life}  Lib:{len(pl.library)}  BF:{len(pl.battlefield)}"
            p.drawText(16, y, line)
            y += 22
        p.restore()

    def _draw_zoom(self, p: QPainter, card):
        rect = QRect(0,0,ZOOM_W,ZOOM_H)
        rect.moveTopLeft(QRect(0,0,ZOOM_W,ZOOM_H).topLeft() + p.viewport().topLeft())
        rect.translate(20, 20)
        p.save()
        p.setBrush(QColor(255,255,255))
        p.setPen(QPen(Qt.black,2))
        p.drawRoundedRect(rect, 8,8)
        p.setPen(Qt.black)
        p.drawText(rect.adjusted(10,10,-10,-10), Qt.TextWordWrap, f"{card.name}\n{' / '.join(card.types)}")
        p.restore()

    def _draw_card(self, p: QPainter, rect: QRect, card, highlight=False):
        p.save()
        p.setBrush(QColor(245,245,245))
        p.setPen(QPen(Qt.black, 2))
        p.drawRoundedRect(rect, 6,6)
        if highlight:
            p.setPen(QPen(QColor(0,180,0),3))
            p.drawRoundedRect(rect, 6,6)
        p.setPen(Qt.black)
        p.drawText(rect.adjusted(4,4,-4,-4), 0, card.name[:18])
        type_line = "/".join(card.types)[:18]
        p.setPen(QColor(70,70,70))
        p.drawText(rect.adjusted(4,22,-4,-4), 0, type_line)
        if "Creature" in card.types and card.power is not None:
            p.setPen(Qt.black)
            p.drawText(rect.adjusted(0,0,-6,-4), Qt.AlignRight | Qt.AlignBottom, f"{card.power}/{card.toughness}")
        p.restore()
