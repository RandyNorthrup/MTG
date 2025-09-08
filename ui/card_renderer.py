from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import QRect

# Card dimension constants (local to card_renderer)
CARD_W = 98
CARD_H = 140
ZOOM_W = 320
ZOOM_H = 440
PADDING = 16

class CardRenderer:
    def __init__(self):
        self.font_small = QFont("SansSerif", 8)
        self.font_big = QFont("SansSerif", 10, QFont.Bold)

    def draw_card(self, p: QPainter, rect: QRect, card, highlight=False):
        p.save()
        p.setBrush(QColor(245,245,245))
        p.setPen(QPen(QColor(0,0,0), 2))
        p.drawRoundedRect(rect, 6, 6)
        if highlight:
            p.setPen(QPen(QColor(0,180,0), 3))
            p.drawRoundedRect(rect, 6, 6)
        p.setFont(self.font_big)
        p.setPen(QColor(10,10,10))
        p.drawText(rect.adjusted(6,4,-6,-4), 0, card.name)
        p.setFont(self.font_small)
        p.setPen(QColor(60,60,60))
        p.drawText(rect.adjusted(6,20,-6,-6), 0, "/".join(card.types))
        if "Creature" in card.types and card.power is not None:
            pt = f"{card.power}/{card.toughness}"
            p.setFont(self.font_big)
            p.drawText(rect.adjusted(0,0,-6,-4), 0x0002 | 0x0080, pt)  # Align right|bottom
        p.restore()

    def draw_zoom(self, p: QPainter, center_x: int, center_y: int, card):
        rect = QRect(0,0,ZOOM_W,ZOOM_H)
        rect.moveCenter(QRect(center_x, center_y, 1,1).center())
        p.save()
        p.setBrush(QColor(255,255,255))
        p.setPen(QPen(QColor(0,0,0),2))
        p.drawRoundedRect(rect, 8,8)
        p.setFont(self.font_big)
        p.setPen(QColor(10,10,10))
        p.drawText(rect.adjusted(10,10,-10,-10), 0, card.name)
        p.setFont(self.font_small)
        p.setPen(QColor(40,40,40))
        p.drawText(rect.adjusted(10,30,-10,-10), 0, "/".join(card.types))
        p.restore()
