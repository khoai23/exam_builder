import random

from typing import Optional, List, Tuple, Any, Union, Dict, Callable

from src.campaign.rules.base_campaign import BaseCampaign 
from src.campaign.event_flavor import GenericFlavorText

import logging
logger = logging.getLogger(__name__)

class PlayerCampaign(BaseCampaign):
    """Version of campaign map that support player actions instead of bots. The bot can still be used for suggestion and/or substitution.
    """
    def __init__(self, *args, players: List[int]=None, player_names: List[str]=None, flavor_text: GenericFlavorText=None, **kwargs):
        super(PlayerCampaign, self).__init__(*args, **kwargs)
        self._is_players = set(players)
        self._player_coef = None
        self._action_dict = {}
        self._current_phase = "deploy"
        # this will use a specific string for player if supplied; fallback to default [P?] if not available 
        if player_names:
            self._setting["player_names"] = player_names
        # this will create & maintain flavor text that occurs during event; providing that it even exist.
        self.flavor_text = flavor_text(self)
        self.last_action_logs = []
        if self.flavor_text:
            player_id = players[0] if len(players) else None 
            player_name, player_color = ("All", "black") if player_id is None else (self.plname(player_id), self.plcolor(player_id))
            self.flavor_text.on_event_triggered("introduction", {"player_name": player_name, "player_color": player_color})

    def plname(self, player_id):
        if "player_names" in self._setting:
            return self._setting["player_names"][player_id]
        else:
            return super(PlayerCampaign, self).plname(player_id)

    @property
    def current_phase(self):
        return self._current_phase 

    def set_player_coef(self, value: float):
        # this should be result of a randomly generated quiz; detailing the coef going to be used in the next offense/defense phase.
        # TODO set different values for different phase? 
        self._player_coef = value
        logger.info("PlayerCampaign: p-coef is set as {}".format(self._player_coef))

    def perform_action_attack(self, player_id: int, attacking: int, target_id: int, attack_modifier: float=1.0, defend_modifier: float=1.0, preserve_modifier: float=2.0):
        target = self._map[target_id][-1]
        if self._player_coef:
            if player_id in self._is_players:
                logger.info("Attack initiated by player with completed quiz; modifier: {}".format(self._player_coef))
                attack_modifier = self._player_coef
            if target["owner"] in self._is_players:
                logger.info("Defend done by player with completed quiz; modifier: {}".format(self._player_coef))
                defend_modifier = self._player_coef 
        target_player_id = target["owner"] # save it here before the action to allow flavor_text to pick up the original owner.
        full_result = result, target, casualty = super(PlayerCampaign, self).perform_action_attack(player_id, attacking, target_id, attack_modifier=attack_modifier, defend_modifier=defend_modifier, preserve_modifier=preserve_modifier)
        if self.flavor_text:
            event_text = self.flavor_text.on_event_triggered("attack", {"player_id": player_id, "player_name": self.plname(player_id), "player_color": self.plcolor(player_id), "result": result, "result_as_str": "succeeded" if result else "failed", "target_name": self.pname(target_id), "target_color": "black" if not isinstance(target_player_id, int) else self.plcolor(target_player_id), "casualty": casualty})
            if event_text:
                self.last_action_logs.append(event_text)
        return full_result

    def update_action(self, player_id: int, action_type: str, action_data: list) -> Tuple[bool, Optional[str]]:
        # save the supposed actions of the player; if anything gone wrong, throw back the issue
        if player_id not in self._is_players:
            # trying to do action of non-player, kick 
            return False, "Player {:d} is a bot; cannot update the actions.".format(player_id)
        if not isinstance(action_data, list) or any(len(a) != 3 for a in action_data): # both move & attack use same format for now
            return False, "Invalid submitted action data: {}".format(action_data)
        self._action_dict[(player_id, action_type)] = action_data
        return True, None

    def phase_perform_attack(self, player_id: int, override_action: Optional[list]=None):
        # override the action, if exist then use itself, if not use empty list to disable bot action 
        # If need to let bots take over, the dict value must be written with None
        if player_id in self._is_players:
            override_action = self._action_dict.get( (player_id, "attack"), None )
        return super(PlayerCampaign, self).phase_perform_attack(player_id, override_action=override_action)

    def phase_perform_movement(self, player_id: int, override_action: Optional[list]=None):
        # override the action, if exist then use itself, if not use empty list to disable bot action 
        # If need to let bots take over, the dict value must be written with None
        if player_id in self._is_players:
            override_action = self._action_dict.get( (player_id, "move"), None )
        return super(PlayerCampaign, self).phase_perform_movement(player_id, override_action=override_action)

    def retrieve_possible_attacks(self, player_id: int):
        # retrieve all possible attacks vector for the player.
        return self.all_attack_vectors(player_id) 

    def retrieve_all_movements(self, player_id: int, allowable_range: int=2):
        # retrieve all possible movements vector-bundle for the player.
        owned = self.all_owned_provinces(player_id)
        movable = []
        for ip in owned:
            source = self._map[ip][-1]
            if source["units"] <= 1:
                continue # not enough unit, dont try anything 
            # output 
            movable.append( (ip, source["units"]-1, [p for p in self.check_range(ip, allowable_range, owner=player_id)]) )
        return movable 

    # all phase functions also update the current phase to the next one
    def full_phase_deploy(self):
        # next phase is move
        self._current_phase = "move"
        return super(PlayerCampaign, self).full_phase_deploy()

    def full_phase_move(self):
        # next phase is attack 
        self._current_phase = "attack"
        return super(PlayerCampaign, self).full_phase_move()

    def full_phase_attack(self):
        # next phase is end; this should trigger the next button on the site
        self._current_phase = "end"
        result = super(PlayerCampaign, self).full_phase_attack()
        self._player_coef = None 
        return result

    def retrieve_all_deployment(self, player_id: int):
        # retrieve all possible deploy point for the player 
        return self.all_deployable_provinces(player_id)

    def end_turn(self):
        # also wipe the action dict 
        self._action_dict.clear() 
#        self._player_coef = None
        # next phase
        self._current_phase = "deploy"
        return super(PlayerCampaign, self).end_turn()


    def full_phase_attack(self, simultaneous_mode: bool=True):
        """Upgrade over 1st variant - instead of bots making up the attack sequentially, force them to be created first and launch them with respect to their current setting.
        Should be accompanied by IntentionRule to reward plays that resemble planning."""
        if not simultaneous_mode:
            # just use the old logic
            self._current_phase = "end"
            self._player_coef = None 
            return super(PlayerCampaign, self).full_phase_attack()
        # receive bot actions at current situation. 
        action_dict, direction_dict = dict(), dict()
        mutual_attacks = set()
        for pid in range(self._player_count):
            if pid in self._dead:
                continue # ignore dead ones.
            actions = self._player_bot[pid].calculate_attacks(self._map)
            if not actions:
                continue 
            target_ids = set(tid for sid, tid, rq in actions)
            if len(target_ids) > 1:
                # TODO allow multiple attacks if setting allows for it.
                print("Player {} submitted multiple attack targets {}({}), ignored.".format(pid, target_ids, actions))
                continue 
            action_dict[pid] = actions
            target_id = list(target_ids)[0]
            target_player = self._map[target_id][-1]["owner"]
            direction_dict[pid] = (target_id, target_player)
            if direction_dict.get(target_player, (None, ))[-1] == pid:
                # mutual attacks detected 
                mutual_attacks.add( (pid, target_player) )
        logger.info("@phase_perform_attack with simultaneous_mode=True: actions: {}, mutual_attacks: {}".format(action_dict, mutual_attacks))

        # resolving received actions:
        # if there are two who simultaneously attack each other, and both attacked province were mobilized for the attack, battle is fought without any terrain bonuses/penalties with the full section. This should reward the stronger player.
        # same case, but only one attacked province is mobilized - the mobilized province's terrain bonuses/penalties are removed, and their units are halved in both attacking & defending calculation. This should reward the player who planned correctly (think something like a riposte).
        # all other case, resolve as normal in order of initiative.
        for p1, p2 in mutual_attacks:
            actions1, actions2 = action_dict[p1], action_dict[p2]
            source_1 = set(sid for sid, tid, rq in actions1)
            source_2 = set(sid for sid, tid, rq in actions2)
            target_1, _ = direction_dict[p1]
            target_2, _ = direction_dict[p2]
            if target_1 in source_2 and target_2 in source_1:
                # direct fight trigger; draw all available & meet in open combat
                draw_1 = draw_2 = 0
                for sid, tid, rq in actions1:
                    source = self._map[sid][-1]
                    can_draw = min(rq, source["units"] - 1)
                    if can_draw:
                        draw_1 += can_draw 
                        source["units"] -= can_draw
                for sid, tid, rq in actions2:
                    source = self._map[sid][-1]
                    can_draw = min(rq, source["units"] - 1)
                    if can_draw:
                        draw_2 += can_draw 
                        source["units"] -= can_draw
                self.perform_action_mutual_attacks(p1, draw_1, target_1, p2, draw_2, target_2)
                # remove the resolved attacks
                action_dict.pop(p1); action_dict.pop(p2)
            elif target_1 in source_2 or target_2 in source_1:
                # riposte trigger - the mobilized region will lose half of the attacking values and its terrain defensive bonuses   
                if target_1 in source_2:
                    p_adv, p_dav = p1, p2 # adv is for "advantage", dav is for "disadvantage"
                    actions_adv, actions_dav, target_adv, target_dav = actions1, actions2, target_1, target_2
                else:
                    p_adv, p_dav = p2, p1
                    actions_adv, actions_dav, target_adv, target_dav = actions2, actions1, target_2, target_1
                # disadvantage side attack first with reduced values
                draw_dav = 0
                for sid, tid, rq in actions_dav:
                    source = self._map[sid][-1]
                    can_draw = min(rq, source["units"] - 1)
                    if can_draw:
                        if sid == target_adv:  # penalized region
                            draw_dav += (can_draw // 2 )
                        else:
                            draw_dav += can_draw 
                        source["units"] -= can_draw 
                print("[P{}] attacking --{}--> {} (P{}, disadvantage)".format(p_dav, draw_dav, self.pname(target_dav), p_adv))
                self.perform_action_attack(p_dav, draw_dav, target_dav)
                # advantage side then attack; TODO invalidate the terrain in here; for now just give a bonus base attack modifier 
                draw_adv = 0
                for sid, tid, rq in actions_adv:
                    source = self._map[sid][-1]
                    can_draw = min(rq, source["units"] - 1)
                    if can_draw:
                        draw_adv += can_draw 
                        source["units"] -= can_draw 
                print("[P{}] attacking --{}--> {} (P{}, advantage)".format(p_adv, draw_adv, self.pname(target_adv), p_dav))
                self.perform_action_attack(p_adv, draw_adv, target_adv, attack_modifier=1.5)
                # remove the resolved attacks
                action_dict.pop(p1); action_dict.pop(p2)
            else:
                continue # attacks land in different regions; resolve as normal.
        # perform the rest as normal
        for i in self._action_order:
            if i not in action_dict:
                continue # already resolved or not submitted; ignore 
            # automatically lower the units to available & discarding those no longer owned.
            correct_source_actions = ((sid, tid, min(rq, self._map[sid][-1]["units"]-1)) for sid, tid, rq in action_dict[i] if self._map[sid][-1]["owner"] == i)
            correct_amount_actions = [a for a in correct_source_actions if a[-1] > 0]
            self.phase_perform_attack(i, override_action=correct_amount_actions) 
        
        # after everything; reset the phase & coef
        self._current_phase = "end"
        self._player_coef = None 
        return

    def perform_action_mutual_attacks(self, player_1: int, force_1: int, target_1: int, player_2: int, force_2: int, target_2: int, player_1_modifier: float=1.0, player_2_modifier: float=1.0, winning_resolution="attack"):
        """Happens when two player simultaneously launches attack into each other. This should not be affected by any terrain-related mechanism. Yet.
        winning_resolution: depending on mode:
            `hold` will just deposit the winning side back to their matching province. Should not happen in normal circumstances. Heavily favor the loser if this is the case.
            `attack`/`continue` will launch an additional attack from the remaining force of the winnning side. TODO negate terrain bonus; for now, this will give the losing side a flat 0.5 defend_modifier.
            `overrun` will automatically give the winning side the target province. TODO deposit the remaining losing side units to somewhere. Heavily favor the winner if they has small advantage."""
        true_force_1 = force_1 * player_1_modifier
        true_force_2 = force_2 * player_2_modifier
        # compare  
        if true_force_1 == true_force_2:
            # really not supposed to happen with RandomFactorRule; but assuming it does..
            if self.flavor_text:
                event_text = self.flavor_text.on_event_triggered("mutual_attacks_draw", {
                    "player_1_id": player_1, "player_1_name": self.plname(player_1), "player_1_color": self.plcolor(player_1),
                    "player_2_id": player_2, "player_2_name": self.plname(player_2), "player_2_color": self.plcolor(player_2)
                    })
                if event_text:
                    self.last_action_logs.append(event_text)
            return
        if true_force_1 > true_force_2:
            winner, loser = player_1, player_2
        else:
            winner, loser = player_2, player_1
        remaining_units = max(int(abs(true_force_1 - true_force_2)), 1) # should have at least 1 unit remaining 
        # register unit casualties.
        self._context["casualties"][player_1] += max(force_1 if winner == player_2 else force_1 - remaining_units, 0)
        self._context["casualties"][player_2] += max(force_2 if winner == player_1 else force_2 - remaining_units, 0)
        if winning_resolution == "hold":
            return_province_id = target_2 if winner == player_1 else target_1 
            self._map[return_province_id][-1]["units"] += remaining_units 
            if self.flavor_text:
                event_text = self.flavor_text.on_event_triggered("mutual_attack_win_hold", {
                    "winner_id": winner, "winner_name": self.plname(winner), "winner_color": self.plcolor(winner),
                    "loser_id": loser, "loser_name": self.plname(loser), "loser_color": self.plcolor(loser),
                    "returning_units": remaining_units, "return_province_id": return_province_id, "return_province_name": self.pname(return_province_id)
                    })
                if event_text:
                    self.last_action_logs.append(event_text)
            return
        elif winning_resolution == "attack" or winning_resolution == "continue":
            winner_target = target_1 if winner == player_1 else target_2
            if self.flavor_text:
                event_text = self.flavor_text.on_event_triggered("mutual_attack_win_continue", {
                    "winner_id": winner, "winner_name": self.plname(winner), "winner_color": self.plcolor(winner),
                    "loser_id": loser, "loser_name": self.plname(loser), "loser_color": self.plcolor(loser),
                    "remaining_units": remaining_units
                    })
                if event_text:
                    self.last_action_logs.append(event_text)
            result = self.perform_action_attack(winner, remaining_units, winner_target, defend_modifier=0.5)
            return 
        elif winning_resolution == "overrun":
            winner_target = target_1 if winner == player_1 else target_2
            target = self._map[winner_target][-1]
            target["owner"] = winner 
            target["units"] = remaining_units + 1
            if self.flavor_text:
                event_text = self.flavor_text.on_event_triggered("mutual_attack_win_overrun", {
                    "winner_id": winner, "winner_name": self.plname(winner), "winner_color": self.plcolor(winner),
                    "loser_id": loser, "loser_name": self.plname(loser), "loser_color": self.plcolor(loser),
                    "occupy_units": remaining_units, "occupy_province_id": return_province_id, "occupy_province_name": self.pname(return_province_id)
                    })
                if event_text:
                    self.last_action_logs.append(event_text)
            return
        else:
            raise ValueError("@perform_action_mutual_attacks: winning_resolution must be hold|attack/continue|overrun; instead is {}".format(winning_resolution))

