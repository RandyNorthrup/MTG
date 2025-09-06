import pygame
from typing import List
from config import *
from .card_renderer import CardRenderer
from .interaction import Interaction
from ui.tabs import TabBar, TAB_HEIGHT

class UIManager:
    def __init__(self, game):
        self.game = game

        # Tabs: 0=Home, 1=Decks, 2=Play
        self.active_tab = 0
        self.tabbar = TabBar(["Home", "Decks", "Play"], on_change=self._switch_tab)

        self.card_r = CardRenderer()
        self.inter = Interaction()

        # Optional panels (attach outside if you have them)
        self.deckbuilder = getattr(self, "deckbuilder", None)
        self.playfield   = getattr(self, "playfield", None)

        self.font = pygame.font.Font(FONT_NAME, 18)
        self.font_large = pygame.font.Font(FONT_NAME, 28)
        self.small = pygame.font.Font(FONT_NAME, 14)

        self.inter.hover_card = None

    def _switch_tab(self, idx: int):
        self.active_tab = idx

    # ----- Events -----

    def handle_event(self, event: pygame.event.Event):
        self.tabbar.handle_event(event)

        if self.active_tab == 1 and self.deckbuilder and hasattr(self.deckbuilder, "handle_event"):
            self.deckbuilder.handle_event(event)
        elif self.active_tab == 2 and self.playfield and hasattr(self.playfield, "handle_event"):
            self.playfield.handle_event(event)

        if self.active_tab == 2 and event.type == pygame.MOUSEMOTION:
            self._update_hand_hover()

    # ----- Draw -----

    def draw(self, screen: pygame.Surface):
        screen.fill((20, 20, 30))
        self.tabbar.draw(screen, screen.get_width())
        content = pygame.Rect(0, TAB_HEIGHT, screen.get_width(), screen.get_height() - TAB_HEIGHT)

        if self.active_tab == 0:
            self.draw_home(screen, content)
        elif self.active_tab == 1:
            self.draw_decks(screen, content)
        else:
            self.draw_play(screen, content)

        if self.inter.hover_card is not None:
            mx, my = pygame.mouse.get_pos()
            self.card_r.draw_zoom(screen, (mx + 140, my), self.inter.hover_card)

    def draw_home(self, screen: pygame.Surface, rect: pygame.Rect):
        f = self.font_large
        lines = [
            "Welcome to MTG Commander.",
            "• Use Decks to build/validate decks (Commander rules enforced).",
            "• Go to Play to start a match against the AI.",
        ]
        y = rect.y + 20
        for t in lines:
            surf = f.render(t, True, (230, 230, 240))
            screen.blit(surf, (rect.x + 20, y))
            y += 34

        hint = self.small.render("Commander: 40 life, 21 commander combat damage loses.", True, (190, 190, 210))
        screen.blit(hint, (rect.x + 20, y + 8))

    def draw_decks(self, screen: pygame.Surface, rect: pygame.Rect):
        if self.deckbuilder and hasattr(self.deckbuilder, "draw"):
            self.deckbuilder.draw(screen, rect)
        else:
            msg = self.font.render("Deckbuilder not initialized.", True, (230, 150, 150))
            screen.blit(msg, (rect.x + 20, rect.y + 20))

    def draw_play(self, screen: pygame.Surface, rect: pygame.Rect):
        # Opponent battlefield (top)
        y_bf_ai = rect.y + PADDING + 40
        self._draw_battlefield(screen, self.game.players[1].battlefield, y_bf_ai)

        # Your battlefield (bottom)
        y_bf_player = rect.bottom - HAND_HEIGHT - BATTLEFIELD_HEIGHT - PADDING
        self._draw_battlefield(screen, self.game.players[0].battlefield, y_bf_player)

        # Your hand (bottom strip)
        self._draw_hand(screen)

        # Commanders
        self._draw_commanders(screen)

        if self.playfield and hasattr(self.playfield, "draw"):
            self.playfield.draw(screen, rect)

    # ----- Helpers -----

    def _draw_battlefield(self, screen: pygame.Surface, battlefield, y: int):
        x = PADDING
        for perm in battlefield:
            r = pygame.Rect(x, y, CARD_W, CARD_H)
            self.card_r.draw_card(screen, r, perm.card, highlight=False)
            if perm.tapped:
                pygame.draw.line(screen, (200, 50, 50), (r.left, r.top), (r.right, r.bottom), 4)
            x += CARD_W + 12

    def _hand_rects(self) -> List[pygame.Rect]:
        ps = self.game.players[0]
        return self.inter.hand_card_rects(len(ps.hand))

    def _update_hand_hover(self):
        ps = self.game.players[0]
        rects = self._hand_rects()
        mx, my = pygame.mouse.get_pos()
        idx = self.inter.card_at_pos(rects, (mx, my))
        self.inter.hover_card = ps.hand[idx] if idx is not None else None

    def _draw_hand(self, screen: pygame.Surface):
        ps = self.game.players[0]
        rects = self._hand_rects()
        playable_ids = {c.id for c in ps.find_playable()}  # hash-safe
        for i, r in enumerate(rects):
            c = ps.hand[i]
            self.card_r.draw_card(screen, r, c, highlight=(c.id in playable_ids))
        self._update_hand_hover()

    def _draw_commanders(self, screen: pygame.Surface):
        p = self.game.players[0]
        a = self.game.players[1]
        rect_p = pygame.Rect(PADDING, SCREEN_H - HAND_HEIGHT - CARD_H - 10, CARD_W, CARD_H)
        rect_a = pygame.Rect(SCREEN_W - CARD_W - PADDING, PADDING + 40, CARD_W, CARD_H)

        if p.commander:
            in_command = (p.commander in p.command)
            self.card_r.draw_card(screen, rect_p, p.commander, highlight=in_command)
            casts = p.commander_tracker.cast_counts.get(p.commander.id, 0)
            tax = 2 * casts
            screen.blit(self.small.render(f"Cast x{casts} (Tax +{tax})", True, (230,230,230)), (rect_p.x, rect_p.bottom + 2))
            dealt = p.commander_tracker.damage.get((a.player_id, p.player_id), 0)
            screen.blit(self.small.render(f"Dealt to Opp: {dealt}/21", True, (210,210,240)), (rect_p.x, rect_p.bottom + 18))

        if a.commander:
            in_command = (a.commander in a.command)
            self.card_r.draw_card(screen, rect_a, a.commander, highlight=in_command)
            casts = a.commander_tracker.cast_counts.get(a.commander.id, 0)
            tax = 2 * casts
            screen.blit(self.small.render(f"Cast x{casts} (Tax +{tax})", True, (230,230,230)), (rect_a.x - 30, rect_a.bottom + 2))
            dealt = a.commander_tracker.damage.get((p.player_id, a.player_id), 0)
            screen.blit(self.small.render(f"Dealt to You: {dealt}/21", True, (210,210,240)), (rect_a.x - 30, rect_a.bottom + 18))
