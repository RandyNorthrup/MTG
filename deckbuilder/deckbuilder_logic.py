# deckbuilder/deckbuilder_logic.py
from typing import Dict, List, Tuple
from rules.commander_validator import validate_commander_deck, DeckReport

def validate_deck_from_ids(main_ids: List[str], commander_ids: List[str], card_db_by_id: Dict[str, dict]) -> DeckReport:
    main_cards = [card_db_by_id[i] for i in main_ids if i in card_db_by_id]
    commander_cards = [card_db_by_id[i] for i in commander_ids if i in card_db_by_id]
    return validate_commander_deck(main_cards, commander_cards)
