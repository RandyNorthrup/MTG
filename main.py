import pygame, sys, os, json, re
from typing import List, Tuple, Optional
from config import *
from engine.game_state import GameState, PlayerState
from engine.card_engine import Card
from ai.basic_ai import BasicAI
from ui.ui_manager import UIManager

# --- NEW: legacy aliases so old deck ids resolve cleanly ---
BASIC_ALIASES = {
    "basic_forest": "Forest",
    "basic_island": "Island",
    "basic_mountain": "Mountain",
    "basic_plains": "Plains",
    "basic_swamp": "Swamp",
}
CUSTOM_ALIASES = {
    "lightning_bolt_plus": "Lightning Bolt",
    "divination": "Divination",
    "coiling_oracle": "Coiling Oracle",
    "tatyova_benthic_druid": "Tatyova, Benthic Druid",
    "aesi_tyrant_of_gyre_strait": "Aesi, Tyrant of Gyre Strait",
    "dragonspeaker_shaman": "Dragonspeaker Shaman",
    "thunderbreak_regent": "Thunderbreak Regent",
    "the_ur_dragon": "The Ur-Dragon",
}

def load_card_db() -> tuple[dict, dict, dict, str]:
    """
    Returns (by_id, by_name_lower, by_normalized_name, path_used).
    Prefers the Scryfall-derived full DB if present, else falls back to the small starter DB.
    """
    base = os.path.join('data','cards','card_db.json')
    full = os.path.join('data','cards','card_db_full.json')
    path = full if os.path.exists(full) else base
    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # raw may be a list (most common) or an id->card dict.
    cards = list(raw.values()) if isinstance(raw, dict) else list(raw)

    by_id = { c['id']: c for c in cards }

    # exact lowercase name map
    by_name_lower: dict[str, dict] = {}
    for c in cards:
        nm = c.get('name')
        if isinstance(nm, str):
            by_name_lower[nm.lower()] = c

    # normalized name map (strip punctuation, collapse spaces, lowercase)
    def norm(s: str) -> str:
        return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

    by_norm: dict[str, dict] = {}
    for c in cards:
        nm = c.get('name')
        if isinstance(nm, str):
            by_norm[norm(nm)] = c

    return by_id, by_name_lower, by_norm, path

def _resolve_entry(entry: str, by_id: dict, by_name_lower: dict, by_norm: dict, deck_path: str, db_path_used: str) -> dict:
    """
    Resolve a deck entry that could be an id, an exact name, or an underscore/simplified name.
    """
    # --- NEW: remap legacy aliases to canonical names first ---
    entry = BASIC_ALIASES.get(entry, entry)
    entry = CUSTOM_ALIASES.get(entry, entry)

    # 1) direct id match
    if entry in by_id:
        return by_id[entry]

    # 2) exact name (case-insensitive)
    c = by_name_lower.get(entry.lower())
    if c:
        return c

    # 3) normalized name (handles underscores, punctuation, etc.)
    def norm(s: str) -> str:
        return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
    c = by_norm.get(norm(entry))
    if c:
        return c

    # Not found → helpful error
    raise KeyError(
        f"Card '{entry}' not found in card DB.\n"
        f"Deck file: {deck_path}\n"
        f"Card DB used: {db_path_used}\n"
        f"Tip: Use exact Scryfall names or ids, or keep underscore ids like 'aesi_tyrant_of_gyre_strait' "
        f"(this loader now resolves those too)."
    )

def load_deck(path: str, by_id: dict, by_name_lower: dict, by_norm: dict, db_path_used: str, owner_id: int) -> Tuple[List[Card], Optional[Card]]:
    with open(path,'r',encoding='utf-8') as f:
        d = json.load(f)

    cards: List[Card] = []

    # Commander entry can be id OR name (or simplified underscore name)
    commander_entry = d.get('commander')
    commander_card: Optional[dict] = None
    if commander_entry:
        commander_card = _resolve_entry(commander_entry, by_id, by_name_lower, by_norm, path, db_path_used)

    # Cards can be id OR name (or simplified underscore name)
    for entry in d.get('cards', []):
        cdata = _resolve_entry(entry, by_id, by_name_lower, by_norm, path, db_path_used)
        # Skip adding the commander to the main 99; we'll build a separate Card object below
        if commander_card and cdata['id'] == commander_card['id']:
            continue
        cards.append(Card(
            id=cdata['id'], name=cdata['name'], types=cdata['types'], mana_cost=cdata['mana_cost'],
            power=cdata.get('power'), toughness=cdata.get('toughness'), text=cdata.get('text',''),
            is_commander=False, color_identity=cdata.get('color_identity',[]), owner_id=owner_id, controller_id=owner_id
        ))

    # Build commander object last (if present)
    commander_obj: Optional[Card] = None
    if commander_card:
        commander_obj = Card(
            id=commander_card['id'], name=commander_card['name'], types=commander_card['types'],
            mana_cost=commander_card['mana_cost'],
            power=commander_card.get('power'), toughness=commander_card.get('toughness'),
            text=commander_card.get('text',''), is_commander=False,
            color_identity=commander_card.get('color_identity',[]),
            owner_id=owner_id, controller_id=owner_id
        )

    return cards, commander_obj

def new_game():
    by_id, by_name_lower, by_norm, db_path_used = load_card_db()
    p_cards, p_commander = load_deck(os.path.join('data','decks','reap_the_tides.json'), by_id, by_name_lower, by_norm, db_path_used, 0)
    a_cards, a_commander = load_deck(os.path.join('data','decks','draconic_domination.json'), by_id, by_name_lower, by_norm, db_path_used, 1)
    p = PlayerState(player_id=0, name='You', life=STARTING_LIFE, library=p_cards, commander=p_commander)
    a = PlayerState(player_id=1, name='AI', life=STARTING_LIFE, library=a_cards, commander=a_commander)
    game = GameState(players=[p,a])
    game.setup()
    return game

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W,SCREEN_H))
    pygame.display.set_caption('MTG Commander – Phase 1')
    clock = pygame.time.Clock()
    game = new_game()
    ui = UIManager(game)
    ai = BasicAI(pid=1)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # --- NEW: let the UI handle tabs & active panel events first ---
            ui.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_SPACE:
                    if game.stack.can_resolve():
                        game.stack.resolve_top(game)
                    else:
                        game.next_phase()
                        if game.active_player == 1 and game.phase in ('MAIN1','COMBAT_DECLARE'):
                            ai.take_turn(game, ui)
                if event.key == pygame.K_a:
                    if game.active_player == 0 and game.phase == 'COMBAT_DECLARE':
                        game.declare_attackers(0)

            # Left click to play/cast from hand (Play tab only)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and ui.active_tab == 2:
                ps = game.players[0]
                if game.phase in ('MAIN1','MAIN2') and game.active_player == 0:
                    playable_ids = {c.id for c in ps.find_playable()}
                    rects = ui.inter.hand_card_rects(len(ps.hand))
                    idx = ui.inter.card_at_pos(rects, event.pos)
                    if idx is not None:
                        c = ps.hand[idx]
                        if c.id in playable_ids:
                            if 'Land' in c.types:
                                game.play_land(0, c)
                            else:
                                for perm in ps.battlefield:
                                    if 'Land' in perm.card.types and not perm.tapped:
                                        game.tap_for_mana(0, perm)
                                game.cast_spell(0, c)

        ui.draw(screen)
        if game.check_game_over():
            msg = 'You Win!' if game.players[1].life <= 0 else 'You Lose!'
            font = pygame.font.Font(FONT_NAME,36)
            surf = font.render(msg, True, (255,255,255))
            screen.blit(surf,(SCREEN_W//2 - surf.get_width()//2, SCREEN_H//2 - surf.get_height()//2))
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == '__main__':
    main()
