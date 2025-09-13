# MTG Commander Game Engine - Rules Compliance Analysis

## Overview

This document provides a comprehensive analysis of the current MTG Commander Game Engine implementation against the official Magic: The Gathering Comprehensive Rules. The analysis identifies areas where the engine deviates from official rules and provides recommendations for achieving strict rules compliance.

## 🔍 Analysis Summary

### Current Implementation Strengths ✅

1. **Basic Phase Structure**: The engine recognizes the correct MTG turn phases
2. **Mana System**: Generally follows CR 106 for mana pools and payment
3. **Stack Structure**: Implements LIFO ordering correctly
4. **Commander Rules**: Basic commander tax and damage tracking implemented
5. **Card Type Handling**: Proper differentiation between permanent and non-permanent spells

### Critical Issues Identified ❌

## 1. Phase/Step Progression Issues (CR 500 - Turn Structure)

### Current Problems:
- **Inconsistent Phase Timing**: `phase_hooks.py` has hardcoded phase advancement logic that doesn't properly handle priority
- **Missing Steps**: Some phases are missing their constituent steps (e.g., combat has steps but they're not properly structured)
- **Auto-advancement**: Phases advance automatically without proper priority passing
- **State-based Actions**: Not properly checked at the right timing

### MTG Rules Requirements:
- CR 500.1: Each turn has exactly 5 phases, some with steps
- CR 116.3: Players must receive priority in each step/phase where priority is given
- CR 116.4: Priority passes in APNAP order (Active Player, Non-Active Player)
- CR 500.8: Steps and phases end when all players pass priority in succession with empty stack

### Evidence from Code:
```python
# phase_hooks.py line 298-311 - Auto-advancement without priority
QTimer.singleShot(100, auto_advance_to_main)
```

## 2. Priority System Violations (CR 116 - Timing and Priority)

### Current Problems:
- **Missing Priority System**: `priority.py` is essentially empty (only 14 lines)
- **No APNAP Order**: Priority doesn't follow Active Player, Non-Active Player ordering
- **No Priority Holding**: Players can't hold priority when casting spells
- **Automatic Passing**: Priority is never actually held by players

### MTG Rules Requirements:
- CR 116.3a: Active player receives priority at start of most steps/phases
- CR 116.3b: When priority is given, players can cast spells or activate abilities
- CR 116.4: Priority passes to next player in APNAP order
- CR 116.5: Player with priority may pass; if all players pass with empty stack, step/phase ends

### Evidence from Code:
```python
# priority.py - Completely inadequate implementation
class PriorityManager:
    def auto_pass_if_ai(self):
        pass  # No actual priority logic
```

## 3. Stack Resolution Issues (CR 608 - Resolving Spells and Abilities)

### Current Problems:
- **Immediate Resolution**: Some effects resolve immediately without using the stack
- **Missing Priority Between Resolutions**: Players should receive priority between each stack resolution
- **Incomplete State-Based Action Checks**: SBAs not checked after each resolution

### MTG Rules Requirements:
- CR 608.1: Each spell/ability resolves individually from the stack
- CR 608.2h: Priority passes after each resolution
- CR 608.2g: State-based actions are checked after each resolution

### Evidence from Code:
```python
# stack.py line 161-169 - Oversimplified priority passing
def pass_priority(self, player_id: int):
    if self.can_resolve():
        self.resolve_top()  # Immediate resolution without proper priority
```

## 4. Mana Pool Timing Issues (CR 106.4)

### Current Problems:
- **Manual Emptying**: Mana pools are not automatically emptied between steps/phases
- **Incorrect Timing**: Pool emptying logic exists but isn't consistently applied

### MTG Rules Requirements:
- CR 106.4: Mana pools empty at the end of each step and phase

### Evidence from Code:
```python
# game_state.py line 153-154 - Manual emptying only
def next_phase(self):
    self._empty_all_mana_pools()  # Only called during explicit phase changes
```

## 5. Spell Casting Timing Violations (CR 601)

### Current Problems:
- **Missing Timing Checks**: No verification of sorcery-speed restrictions
- **Incomplete Casting Process**: The full casting process (announce, pay costs, choose targets) is simplified
- **No Illegal Action Handling**: Invalid timing doesn't properly fail

### MTG Rules Requirements:
- CR 307.1: Sorceries can only be cast during main phase with empty stack and priority
- CR 601.2: Complete casting process must be followed
- CR 601.3: If any part fails, the spell is illegal and returned to hand

## 6. State-Based Actions Missing (CR 704)

### Current Problems:
- **No SBA Implementation**: No systematic state-based action checking
- **Incorrect Timing**: SBAs should be checked continuously, not just at specific times
- **Incomplete Coverage**: Many SBAs are missing (lethal damage, zero toughness, etc.)

### MTG Rules Requirements:
- CR 704.1: State-based actions are checked continuously
- CR 704.3: All applicable SBAs are performed simultaneously
- CR 704.4: If any SBAs were performed, they're checked again

## 📋 Detailed Fix Requirements

### 1. Priority System Overhaul

**Required Changes:**
```python
class PrioritySystem:
    def __init__(self, game):
        self.game = game
        self.active_player = game.active_player
        self.priority_player = game.active_player
        self.players_passed = set()
    
    def give_priority(self, player_id):
        """Give priority to specific player per CR 116"""
        self.priority_player = player_id
        self.players_passed.clear()
    
    def pass_priority(self, player_id):
        """Player passes priority in APNAP order"""
        if player_id != self.priority_player:
            return False  # Out of turn
        
        self.players_passed.add(player_id)
        self.priority_player = self._next_player_apnap()
        
        # Check if all players passed with empty stack
        if len(self.players_passed) == len(self.game.players) and not self.game.stack.items():
            self._end_step_or_phase()
    
    def _next_player_apnap(self):
        """Calculate next player in APNAP order"""
        # Implementation needed
```

### 2. Phase Structure Revision

**Required Changes:**
```python
class PhaseManager:
    def __init__(self, game):
        self.game = game
        self.current_phase = "beginning"
        self.current_step = "untap"
        self.priority_system = PrioritySystem(game)
    
    def advance_step(self):
        """Only advance when all players pass priority with empty stack"""
        if not self._can_advance():
            return False
        
        self._perform_step_actions()
        self._check_state_based_actions()
        self._give_priority_if_applicable()
    
    def _can_advance(self):
        """Check if step/phase can advance per CR 116.4"""
        return (len(self.priority_system.players_passed) == len(self.game.players) 
                and not self.game.stack.items())
```

### 3. State-Based Actions Implementation

**Required Changes:**
```python
class StateBasedActions:
    def check_and_perform(self, game):
        """Perform all applicable SBAs per CR 704"""
        actions_performed = False
        
        while True:
            current_actions = []
            
            # CR 704.5a: Zero or negative life
            for player in game.players:
                if player.life <= 0:
                    current_actions.append(('lose_game', player.player_id))
            
            # CR 704.5f: Zero toughness
            for player in game.players:
                for perm in player.battlefield[:]:  # Copy to avoid modification issues
                    if hasattr(perm, 'toughness') and perm.toughness <= 0:
                        current_actions.append(('destroy', perm))
            
            # CR 704.5g: Lethal damage
            # ... additional SBAs
            
            if not current_actions:
                break
                
            self._perform_actions(current_actions)
            actions_performed = True
            
        return actions_performed
```

## 🎯 Implementation Priority

### Phase 1: Core Priority System
1. Implement complete PrioritySystem class
2. Integrate priority with phase advancement
3. Add proper APNAP ordering

### Phase 2: Stack Integration
1. Ensure priority passes after each stack resolution
2. Add proper state-based action timing
3. Implement holding priority during spell casting

### Phase 3: Timing Restrictions
1. Add sorcery-speed validation
2. Implement complete casting process
3. Add proper illegal action handling

### Phase 4: State-Based Actions
1. Implement comprehensive SBA system
2. Add continuous checking at correct timing
3. Ensure all CR 704 rules are covered

## 🧪 Testing Strategy

### Compliance Test Suite Enhancement
The existing `test_rules_compliance.py` should be expanded to include:

1. **Priority System Tests**:
   - APNAP order verification
   - Priority holding during spell casting
   - Proper phase/step advancement timing

2. **Stack Resolution Tests**:
   - Priority between resolutions
   - State-based actions after resolution
   - Proper LIFO ordering

3. **Timing Restriction Tests**:
   - Sorcery speed enforcement
   - Instant timing validation
   - Special action timing

4. **State-Based Action Tests**:
   - Continuous checking
   - Simultaneous performance
   - Complete coverage of CR 704

## 📊 Compliance Score

**Current Estimated Rules Compliance: 45%**

- ✅ Basic game structure: 70%
- ❌ Priority system: 10%
- ✅ Stack mechanics: 60%
- ❌ State-based actions: 20%
- ✅ Mana system: 80%
- ❌ Timing restrictions: 30%

**Target After Fixes: 95%**

The remaining 5% would be edge cases and highly specialized rules that may not be relevant for the Commander format or can be implemented incrementally.

## 🚀 Next Steps

1. **Immediate**: Fix the critical priority system (biggest impact)
2. **Short-term**: Implement proper phase/step advancement
3. **Medium-term**: Add comprehensive state-based actions
4. **Long-term**: Achieve 95%+ rules compliance through iterative testing

This analysis provides the foundation for transforming the current implementation into a strictly rules-compliant MTG engine suitable for competitive play and rules education.
