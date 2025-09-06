# ui/tabs.py
import pygame
from typing import List, Tuple, Optional, Callable

TAB_HEIGHT = 40
PAD = 12

class TabBar:
    def __init__(self, tabs: List[str], on_change: Callable[[int], None]):
        self.tabs = tabs
        self.active = 0
        self.on_change = on_change
        self.font = pygame.font.SysFont(None, 22)
        self.rects: List[pygame.Rect] = []

    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            pos = e.pos
            for i, r in enumerate(self.rects):
                if r.collidepoint(pos) and i != self.active:
                    self.active = i
                    self.on_change(i)
                    break

    def draw(self, surf: pygame.Surface, width: int):
        self.rects.clear()
        x = 0
        for i, name in enumerate(self.tabs):
            label = self.font.render(name, True, (255,255,255) if i==self.active else (200,200,200))
            w = label.get_width() + PAD*2
            r = pygame.Rect(x, 0, w, TAB_HEIGHT)
            pygame.draw.rect(surf, (45,45,60) if i==self.active else (30,30,40), r)
            surf.blit(label, (r.x + PAD, r.y + (TAB_HEIGHT - label.get_height())//2))
            self.rects.append(r)
            x += w
        # baseline
        pygame.draw.line(surf, (80,80,100), (0, TAB_HEIGHT), (width, TAB_HEIGHT), 2)
