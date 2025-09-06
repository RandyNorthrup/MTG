import pygame
from config import CARD_W, CARD_H, HAND_HEIGHT, SCREEN_W, SCREEN_H, PADDING

class Interaction:
    def __init__(self):
        self.hover_card = None
        self.selected_card = None

    def hand_card_rects(self, hand_len):
        rects = []
        if hand_len == 0:
            return rects
        spacing = min(20, max(6, (SCREEN_W - 2*PADDING - CARD_W) // max(1, hand_len)))
        x = PADDING
        y = SCREEN_H - HAND_HEIGHT + 12
        for i in range(hand_len):
            rects.append(pygame.Rect(x, y, CARD_W, CARD_H))
            x += spacing
        return rects

    def card_at_pos(self, rects, pos):
        for i, r in enumerate(rects):
            if r.collidepoint(pos):
                return i
        return None
