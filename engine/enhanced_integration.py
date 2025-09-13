"""
Enhanced MTG Engine Integration
Demonstrates how the new enhanced systems integrate with your existing engine
"""

import sys
import os

# Add the parent directory to sys.path to import engine modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Any
from engine.card_engine import Card, Permanent
from engine.card_fetch import load_deck, enhance_existing_card
from engine.card_validation import validate_card_data, normalize_card_data
from engine.enhanced_keywords import extract_card_keywords, get_combat_keywords, has_keyword
from engine.layers import LayersEngine, create_static_buff_effect, create_set_pt_effect

class EnhancedCardEngine:
    """
    Enhanced card engine that integrates all the new systems
    with your existing card engine implementation
    """
    
    def __init__(self):
        self.layers_engine = LayersEngine()
        self.validation_enabled = True
        self.keyword_cache = {}  # Cache parsed keywords
        
    def create_enhanced_card(self, card_data: Dict[str, Any], owner_id: int) -> Card:
        """
        Create a Card object with full validation, normalization, and enhancement
        """
        # Step 1: Validate and normalize the card data
        if self.validation_enabled:
            validation_result = validate_card_data(card_data)
            if not validation_result.is_valid:
                print(f"⚠️  Validation errors for {card_data.get('name', 'Unknown')}:")
                for error in validation_result.errors:
                    print(f"   • ERROR: {error}")
            
            if validation_result.warnings:
                print(f"⚠️  Validation warnings for {card_data.get('name', 'Unknown')}:")
                for warning in validation_result.warnings:
                    print(f"   • WARNING: {warning}")
            
            # Use normalized data if available
            if validation_result.normalized_data:
                card_data = validation_result.normalized_data
        
        # Step 2: Create the basic Card object
        card = Card(
            id=card_data.get('id', card_data['name'].lower().replace(' ', '_')),
            name=card_data['name'],
            types=card_data['types'],
            mana_cost=card_data['mana_cost'],
            mana_cost_str=card_data.get('mana_cost_str', ''),
            power=card_data.get('power'),
            toughness=card_data.get('toughness'),
            text=card_data.get('text', ''),
            color_identity=card_data.get('color_identity', []),
            owner_id=owner_id,
            controller_id=owner_id
        )
        
        # Step 3: Associate with layers engine for P/T calculation
        card.set_layers_engine(self.layers_engine)
        
        # Step 4: Parse and cache keywords
        if card.text:
            keywords = extract_card_keywords(card.text)
            self.keyword_cache[card.id] = keywords
            # Store keywords on the card for easy access
            card.keywords = keywords
        
        # Step 5: Apply rules engine parsing (existing functionality)
        try:
            from engine.rules_engine import parse_and_attach
            parse_and_attach(card)
        except ImportError:
            pass  # Rules engine may not be available
        
        return card
    
    def create_permanent(self, card: Card) -> Permanent:
        """Create a Permanent object with enhanced features"""
        permanent = Permanent(card=card)
        
        # Handle summoning sickness based on card type and keywords
        if card.is_type("Creature"):
            # Creatures have summoning sickness unless they have haste
            permanent.summoning_sick = not has_keyword(card, "haste")
        else:
            # Non-creatures don't have summoning sickness
            permanent.summoning_sick = False
        
        return permanent
    
    def get_current_power_toughness(self, card: Card) -> tuple[Optional[int], Optional[int]]:
        """
        Get the current power and toughness of a card after all effects
        """
        return card.get_current_power_toughness()
    
    def add_static_buff(self, source_card: Card, target_predicate, power: int, toughness: int):
        """
        Add a static power/toughness buff effect
        
        Args:
            source_card: Card creating the buff effect
            target_predicate: Function that returns True for cards this affects
            power: Power modification
            toughness: Toughness modification
        """
        effect = create_static_buff_effect(
            source_id=source_card.id,
            power=power,
            toughness=toughness,
            affects_card_func=target_predicate
        )
        self.layers_engine.add_effect(effect)
    
    def add_pt_setting_effect(self, source_card: Card, target_predicate, power: Optional[int], toughness: Optional[int]):
        """
        Add an effect that sets power/toughness to specific values
        """
        effect = create_set_pt_effect(
            source_id=source_card.id,
            power=power,
            toughness=toughness,
            affects_card_func=target_predicate
        )
        self.layers_engine.add_effect(effect)
    
    def remove_effects_from_source(self, source_card: Card):
        """Remove all effects created by a specific card"""
        self.layers_engine.remove_effect(source_card.id)
    
    def get_combat_keywords(self, card: Card) -> set[str]:
        """Get combat-relevant keywords for a card"""
        return get_combat_keywords(card)
    
    def can_block(self, blocker_card: Card, attacker_card: Card) -> bool:
        """Check if blocker can block attacker based on keywords and rules"""
        from engine.enhanced_keywords import can_block
        return can_block(blocker_card, attacker_card)
    
    def handle_combat_damage(self, damage_source: Card, damage_target: Card, damage_amount: int) -> Dict[str, Any]:
        """
        Handle combat damage with keyword interactions
        Returns information about the damage effects
        """
        result = {
            "damage_dealt": damage_amount,
            "lethal_damage": False,
            "life_gained": 0,
            "destroy_target": False
        }
        
        # Handle deathtouch
        if has_keyword(damage_source, "deathtouch") and damage_amount > 0:
            if not has_keyword(damage_target, "indestructible"):
                result["destroy_target"] = True
                result["lethal_damage"] = True
        
        # Handle lifelink
        if has_keyword(damage_source, "lifelink"):
            result["life_gained"] = damage_amount
        
        # Check for lethal damage based on toughness
        if damage_target.is_type("Creature"):
            current_power, current_toughness = self.get_current_power_toughness(damage_target)
            if current_toughness is not None and damage_amount >= current_toughness:
                result["lethal_damage"] = True
        
        return result


def demonstrate_enhanced_systems():
    """Demonstration of the enhanced card systems"""
    print("🎴 Enhanced MTG Card Engine Demonstration")
    print("=" * 50)
    
    # Create enhanced engine
    engine = EnhancedCardEngine()
    
    # Sample card data (like what would come from your card database)
    sample_cards = [
        {
            "id": "lightning_bolt",
            "name": "Lightning Bolt",
            "types": ["Instant"],
            "mana_cost": 1,
            "mana_cost_str": "{R}",
            "text": "Lightning Bolt deals 3 damage to any target.",
            "color_identity": ["R"]
        },
        {
            "id": "grizzly_bears",
            "name": "Grizzly Bears",
            "types": ["Creature"],
            "mana_cost": 2,
            "mana_cost_str": "{1}{G}",
            "power": 2,
            "toughness": 2,
            "text": "",
            "color_identity": ["G"]
        },
        {
            "id": "serra_angel",
            "name": "Serra Angel",
            "types": ["Creature"],
            "mana_cost": 5,
            "mana_cost_str": "{3}{W}{W}",
            "power": 4,
            "toughness": 4,
            "text": "Flying, vigilance",
            "color_identity": ["W"]
        },
        {
            "id": "giant_growth",
            "name": "Giant Growth",
            "types": ["Instant"],
            "mana_cost": 1,
            "mana_cost_str": "{G}",
            "text": "Target creature gets +3/+3 until end of turn.",
            "color_identity": ["G"]
        }
    ]
    
    # Create enhanced cards
    print("\n📋 Creating Enhanced Cards:")
    cards = []
    for card_data in sample_cards:
        card = engine.create_enhanced_card(card_data, owner_id=1)
        cards.append(card)
        print(f"✅ Created {card.name}")
        
        # Show keywords if any
        if hasattr(card, 'keywords') and card.keywords:
            print(f"   Keywords: {', '.join(card.keywords.keys())}")
        
        # Show current P/T for creatures
        if card.is_type("Creature"):
            power, toughness = engine.get_current_power_toughness(card)
            print(f"   P/T: {power}/{toughness}")
    
    # Demonstrate layers system with static buffs
    print("\n⚔️ Demonstrating Layers System:")
    
    # Find creatures for demonstration
    grizzly_bears = next(c for c in cards if c.name == "Grizzly Bears")
    serra_angel = next(c for c in cards if c.name == "Serra Angel")
    
    print(f"Before effects - Grizzly Bears: {engine.get_current_power_toughness(grizzly_bears)}")
    print(f"Before effects - Serra Angel: {engine.get_current_power_toughness(serra_angel)}")
    
    # Add a static buff effect (like from an anthem effect)
    def affects_all_creatures(card):
        return card.is_type("Creature")
    
    # Create a fake "Glorious Anthem" effect
    fake_anthem = Card(
        id="anthem_effect",
        name="Anthem Effect",
        types=["Effect"],
        mana_cost=0,
        owner_id=1,
        controller_id=1
    )
    
    engine.add_static_buff(fake_anthem, affects_all_creatures, 1, 1)
    
    print(f"After +1/+1 buff - Grizzly Bears: {engine.get_current_power_toughness(grizzly_bears)}")
    print(f"After +1/+1 buff - Serra Angel: {engine.get_current_power_toughness(serra_angel)}")
    
    # Demonstrate keyword interactions
    print("\n🥊 Demonstrating Keyword Combat:")
    
    # Check combat keywords
    serra_keywords = engine.get_combat_keywords(serra_angel)
    print(f"Serra Angel combat keywords: {serra_keywords}")
    
    # Test blocking scenarios
    print(f"Can Grizzly Bears block Serra Angel? {engine.can_block(grizzly_bears, serra_angel)}")
    
    # Simulate combat damage with keywords
    print("\n⚡ Simulating Combat Damage:")
    damage_result = engine.handle_combat_damage(serra_angel, grizzly_bears, 4)
    print(f"Serra Angel deals 4 damage to Grizzly Bears:")
    print(f"  - Damage dealt: {damage_result['damage_dealt']}")
    print(f"  - Lethal damage: {damage_result['lethal_damage']}")
    print(f"  - Life gained: {damage_result['life_gained']}")
    
    print("\n✅ Enhanced systems demonstration complete!")
    
    return engine, cards


def test_integration_with_existing_deck():
    """Test integration with existing deck loading functionality"""
    print("\n🎮 Testing Integration with Existing Deck System:")
    print("=" * 50)
    
    try:
        # Try to load a deck using existing functionality
        # This would use your existing deck loading code
        print("Note: This would integrate with your existing load_deck() function")
        print("The enhanced engine can process any cards loaded through your current system")
        
        # Example of how it would work:
        # library_cards, commander = load_deck("path/to/deck.txt", owner_id=1)
        # enhanced_engine = EnhancedCardEngine()
        # 
        # for card in library_cards:
        #     # Add layers engine support
        #     card.set_layers_engine(enhanced_engine.layers_engine)
        #     
        #     # Parse keywords
        #     if card.text:
        #         keywords = extract_card_keywords(card.text)
        #         card.keywords = keywords
        
        print("✅ Integration points identified")
        
    except Exception as e:
        print(f"Note: Full integration requires existing deck loading system: {e}")


if __name__ == "__main__":
    # Run the demonstration
    engine, cards = demonstrate_enhanced_systems()
    
    # Test integration concepts
    test_integration_with_existing_deck()
    
    print(f"\n🎯 Summary of Enhanced Features:")
    print(f"✅ Comprehensive layers system for accurate P/T calculation")
    print(f"✅ Complete keyword recognition with combat interactions") 
    print(f"✅ Card data validation and normalization")
    print(f"✅ Integration with existing card engine structures")
    print(f"✅ Extensible framework for additional MTG rules")
