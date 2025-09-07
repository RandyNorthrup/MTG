import random
from engine.mana import parse_mana_cost

def enhance_ai_controllers(game, ai_controllers):
    def card_total_cost(card):
        cost_dict = parse_mana_cost(getattr(card, 'mana_cost_str', ''))
        if not cost_dict:
            if isinstance(card.mana_cost, int):
                return card.mana_cost
            try:
                return int(card.mana_cost)
            except Exception:
                return 0
        return sum(cost_dict.values())

    def available_untapped_lands(player):
        lands = []
        for perm in getattr(player, 'battlefield', []):
            c = getattr(perm, 'card', perm)
            if 'Land' in c.types and not getattr(perm, 'tapped', False):
                lands.append(perm)
        return lands

    def tap_for_generic(game_ref, pid, needed):
        tapped = 0
        for perm in list(available_untapped_lands(game_ref.players[pid])):
            if tapped >= needed:
                break
            try:
                if hasattr(game_ref, 'tap_for_mana'):
                    game_ref.tap_for_mana(pid, perm)
                else:
                    perm.tapped = True
            except Exception:
                perm.tapped = True
            tapped += 1
        return tapped >= needed

    def safe_advance(game_ref):
        try:
            if hasattr(game_ref, 'turn_manager') and hasattr(game_ref.turn_manager, 'advance_phase'):
                game_ref.turn_manager.advance_phase()
            else:
                game_ref.next_phase()
        except Exception:
            pass

    def play_land_if_possible(ctrl, player):
        if getattr(ctrl, '_land_played_this_turn', False):
            return
        for card in list(player.hand):
            if 'Land' in card.types:
                try:
                    game.play_land(player.player_id, card)
                    ctrl._land_played_this_turn = True
                    return
                except Exception:
                    pass
                try:
                    player.hand.remove(card)
                    if hasattr(game, 'enter_battlefield'):
                        game.enter_battlefield(player.player_id, card)
                    else:
                        player.battlefield.append(type("Perm", (), {"card": card, "tapped": False})())
                    ctrl._land_played_this_turn = True
                    return
                except Exception:
                    continue

    def cast_spells(ctrl, player):
        attempts = 0
        progress = True
        while progress and attempts < 20:
            attempts += 1
            pool = [c for c in list(player.hand)
                    if 'Land' not in c.types and any(t in c.types for t in ('Creature','Enchantment','Artifact'))]
            if not pool: break
            pool.sort(key=card_total_cost)
            for card in pool:
                cost = card_total_cost(card)
                if cost == 0:
                    try:
                        game.cast_spell(player.player_id, card)
                        progress = True
                        break
                    except Exception:
                        continue
                lands = available_untapped_lands(player)
                if len(lands) >= cost and tap_for_generic(game, player.player_id, cost):
                    try:
                        game.cast_spell(player.player_id, card)
                        progress = True
                        break
                    except Exception:
                        pass

    def declare_attackers(ctrl, player):
        if not hasattr(game, 'combat'):
            return
        for perm in list(player.battlefield):
            card = getattr(perm, 'card', perm)
            if 'Creature' in card.types and not getattr(perm, 'tapped', False):
                try:
                    game.combat.toggle_attacker(player.player_id, perm)
                except Exception:
                    pass
        try:
            game.combat.attackers_committed()
        except Exception:
            pass
        if getattr(game, 'phase','').upper() == 'COMBAT_DECLARE':
            safe_advance(game)

    def assign_blockers(ctrl, player):
        if not hasattr(game,'combat'): return
        atk = game.combat.state.attackers
        if not atk: return
        used = set()
        for perm in list(player.battlefield):
            if len(used) >= len(atk): break
            card = getattr(perm,'card',perm)
            if 'Creature' in card.types and not getattr(perm,'tapped',False):
                attacker = atk[len(used)]
                try:
                    game.combat.toggle_blocker(player.player_id, perm, attacker)
                    used.add(perm)
                except Exception:
                    continue
        if getattr(game,'phase','').upper() == 'COMBAT_BLOCK':
            safe_advance(game)
            try:
                game.combat.assign_and_deal_damage()
            except Exception:
                pass
            for _ in range(3):
                if getattr(game,'phase','').upper() == 'MAIN2':
                    break
                safe_advance(game)

    def end_main_if_idle(ctrl, player):
        if getattr(game.stack,'can_resolve',lambda:False)():
            return
        safe_advance(game)

    for pid, ctrl in ai_controllers.items():
        def take_turn_bound(game_ref, pid=pid, controller=ctrl):
            phase = getattr(game_ref,'phase','').upper()
            player = game_ref.players[pid]
            if phase == 'UNTAP':
                controller._land_played_this_turn = False
                controller._phase_done = set()
            done = getattr(controller,'_phase_done', set())
            if phase == 'MAIN1' and phase not in done:
                play_land_if_possible(controller, player)
                cast_spells(controller, player)
                done.add(phase)
                end_main_if_idle(controller, player)
            elif phase == 'COMBAT_DECLARE' and game_ref.active_player == pid and phase not in done:
                declare_attackers(controller, player)
                done.add(phase)
            elif phase == 'COMBAT_BLOCK' and game_ref.active_player != pid and phase not in done:
                assign_blockers(controller, player)
                done.add(phase)
            elif phase == 'MAIN2' and phase not in done:
                cast_spells(controller, player)
                done.add(phase)
                end_main_if_idle(controller, player)
            controller._phase_done = done
        ctrl.take_turn = take_turn_bound
