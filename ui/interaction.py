from dataclasses import dataclass
from typing import List, Optional, Tuple
import pygame
from config import CARD_W, CARD_H, HAND_HEIGHT, SCREEN_W, SCREEN_H, PADDING

@dataclass
class Rect:
    x: int; y: int; w: int; h: int
    def contains(self, px: int, py: int) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

class Interaction:
    def __init__(self):
        self.hover_card = None
        self.selected_card = None

    def hand_card_rects(self, hand_len: int) -> List[Rect]:
        if hand_len <= 0:
            return []
        spacing = min(20, max(6, (SCREEN_W - 2*PADDING - CARD_W) // max(1, hand_len)))
        x = PADDING
        y = SCREEN_H - HAND_HEIGHT + 12
        rects = []
        for _ in range(hand_len):
            rects.append(Rect(x,y,CARD_W,CARD_H))
            x += spacing
        return rects

    def card_at_pos(self, rects: List[Rect], pos: Tuple[int,int]) -> Optional[int]:
        mx,my = pos
        for i,r in enumerate(rects):
            if r.contains(mx,my):
                return i
        return None
