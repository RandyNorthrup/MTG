import pygame
from config import CARD_W, CARD_H, ZOOM_W, ZOOM_H, FONT_NAME

class CardRenderer:
    def __init__(self):
        self.font_small = pygame.font.Font(FONT_NAME, 14)
        self.font_big = pygame.font.Font(FONT_NAME, 18)

    def draw_card(self, surface, rect, card, highlight=False):
        pygame.draw.rect(surface, (240, 240, 240), rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2, border_radius=8)
        if highlight:
            pygame.draw.rect(surface, (0, 200, 0), rect, 3, border_radius=8)

        name_surf = self.font_big.render(card.name, True, (10, 10, 10))
        surface.blit(name_surf, (rect.x + 6, rect.y + 6))

        tline = "/".join(card.types)
        type_surf = self.font_small.render(tline, True, (60, 60, 60))
        surface.blit(type_surf, (rect.x + 6, rect.y + 30))

        if "Creature" in card.types and card.power is not None:
            pt = f"{card.power}/{card.toughness}"
            pt_surf = self.font_big.render(pt, True, (10, 10, 10))
            surface.blit(pt_surf, (rect.right - pt_surf.get_width() - 8, rect.bottom - pt_surf.get_height() - 6))

    def draw_zoom(self, surface, center, card):
        rect = pygame.Rect(0, 0, ZOOM_W, ZOOM_H)
        rect.center = center
        pygame.draw.rect(surface, (250, 250, 250), rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2, border_radius=8)
        name = self.font_big.render(card.name, True, (10, 10, 10))
        surface.blit(name, (rect.x + 10, rect.y + 10))
        tline = "/".join(card.types)
        tl = self.font_small.render(tline, True, (50, 50, 50))
        surface.blit(tl, (rect.x + 10, rect.y + 40))
