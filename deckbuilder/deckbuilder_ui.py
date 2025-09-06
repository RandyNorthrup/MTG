import pygame, sys, json, os
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_BACKSPACE, K_RETURN, MOUSEBUTTONDOWN
from deckbuilder.deckbuilder_logic import validate_deck_from_ids


FONT_NAME = None

SCREEN_W, SCREEN_H = 1280, 720
PADDING = 12

class DeckBuilder:
    def __init__(self, card_db_path, banlist_path):
        with open(card_db_path, 'r', encoding='utf-8') as f:
            self.db = json.load(f)
        self.by_name = { c['name']: c for c in self.db }
        self.banned = set()
        with open(banlist_path, 'r', encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if line and not line.startswith('#'):
                    self.banned.add(line)

        self.deck = { 'name': 'Custom Commander Deck', 'commander': None, 'cards': [] }
        self.query = ''
        self.results = self.db
        self.font = None
        self.font_small = None

    def filter_results(self):
        q = self.query.lower().strip()
        if not q:
            self.results = self.db[:200]
            return
        out = []
        for c in self.db:
            if q in c['name'].lower():
                out.append(c)
            elif q in '/'.join(c.get('types',[])).lower():
                out.append(c)
        self.results = out[:300]

    def run(self):
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption('Deck Builder – Phase 2 (Starter)')
        self.font = pygame.font.Font(FONT_NAME, 18)
        self.font_small = pygame.font.Font(FONT_NAME, 14)

        input_active = False

        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        pygame.quit(); sys.exit()
                    if input_active:
                        if event.key == K_BACKSPACE:
                            self.query = self.query[:-1]
                            self.filter_results()
                        elif event.key == K_RETURN:
                            self.filter_results()
                        else:
                            self.query += event.unicode
                            self.filter_results()
                elif event.type == MOUSEBUTTONDOWN:
                    x,y = event.pos
                    if 20 <= x <= SCREEN_W-20 and 20 <= y <= 50:
                        input_active = True
                    else:
                        input_active = False
                    if 20 <= x <= SCREEN_W//2 - 10 and 100 <= y <= SCREEN_H-20:
                        idx = (y-100)//24
                        if 0 <= idx < len(self.results):
                            c = self.results[idx]
                            name = c['name']
                            if name in self.banned:
                                print(f'[BAN] {name} is banned in Commander')
                            else:
                                if pygame.mouse.get_pressed()[2]:
                                    self.deck['commander'] = c['id']
                                else:
                                    if name.lower().startswith(('plains','island','swamp','mountain','forest')) or self.deck['cards'].count(c['id']) == 0:
                                        self.deck['cards'].append(c['id'])
                                    else:
                                        print(f'[Singleton] Already added {name}')
                    if SCREEN_W//2 + 20 <= x <= SCREEN_W - 20 and SCREEN_H - 50 <= y <= SCREEN_H - 20:
                        out = os.path.join('data','decks','custom_deck.json')
                        os.makedirs(os.path.dirname(out), exist_ok=True)
                        with open(out, 'w', encoding='utf-8') as f:
                            json.dump(self.deck, f, ensure_ascii=False, indent=2)
                        print(f'[Saved] {out}')

            screen.fill((245,245,245))

            pygame.draw.rect(screen, (220,220,220), (20,20, SCREEN_W-40, 30), border_radius=6)
            screen.blit(self.font.render(f'Search: {self.query}', True, (20,20,20)), (28,24))

            x1, y1 = 20, 100
            screen.blit(self.font.render('Results (click to add, right-click to set Commander)', True, (0,0,0)), (x1, y1-30))
            for i, c in enumerate(self.results[: int((SCREEN_H-140)/24) ]):
                line = c['name']
                if c['name'] in self.banned:
                    line += '  [BANNED]'
                screen.blit(self.font_small.render(line, True, (0,0,0)), (x1, y1 + i*24))

            x2, y2 = SCREEN_W//2 + 20, 100
            screen.blit(self.font.render('Deck (Commander + 99)', True, (0,0,0)), (x2, y2-30))
            cmdr = next((c for c in self.db if c['id']==self.deck['commander']), None)
            cmdr_name = cmdr['name'] if cmdr else '— (Right-click a card to set as Commander)'
            screen.blit(self.font.render(f'Commander: {cmdr_name}', True, (10,10,10)), (x2, y2))
            y2 += 30
            for i, cid in enumerate(self.deck['cards'][: int((SCREEN_H-200)/20) ]):
                nm = next((c['name'] for c in self.db if c['id']==cid), cid)
                screen.blit(self.font_small.render(f'- {nm}', True, (0,0,0)), (x2, y2 + i*20))

            pygame.draw.rect(screen, (200,200,200), (SCREEN_W//2 + 20, SCREEN_H - 50, SCREEN_W - (SCREEN_W//2 + 40), 30), border_radius=6)
            screen.blit(self.font.render('Save as data/decks/custom_deck.json', True, (20,20,20)), (SCREEN_W//2 + 28, SCREEN_H - 46))

            pygame.display.flip()

if __name__ == '__main__':
    card_db_path = os.path.join('data','cards','card_db_full.json')
    banlist_path = os.path.join('data','commander_banlist.txt')
    if not os.path.exists(card_db_path):
        print('[INFO] card_db_full.json not found. Use tools/scryfall_filter.py to generate it from Scryfall bulk.')
        sys.exit(0)
    DeckBuilder(card_db_path, banlist_path).run()
