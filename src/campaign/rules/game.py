"""Game-wide rules, mainly affecting players."""
import random

from src.campaign.rules.base_campaign import Rule 

from typing import Optional, List, Tuple, Any, Union, Dict 

class RandomFactorRule(Rule):
    """Introduce a generic +-10% deviation to attack-related coefficients - attack, defend, preserve.
    Movement/deployment should be affected in other way.
    Should be put at the end of rule to not get overriden by fixed values e.g Terrain, Weather"""
    def __init__(self, campaign, deviation: float=0.1):
        self.deviation = deviation

    @staticmethod
    def _create_variable(deviation: float):
        return (1 + (random.random() * 2 - 1) * deviation)

    def affect_attack(self, attack_modifier: float, defend_modifier: float, preserve_modifier: float, attack_strength: int, defend_strength: int, attacker_id: int, defender_id: int, target_province_id: int): 
        new_attack_modifier = attack_modifier * RandomFactorRule._create_variable(self.deviation)
        new_defend_modifier = defend_modifier * RandomFactorRule._create_variable(self.deviation)
        new_preserve_modifier = preserve_modifier * RandomFactorRule._create_variable(self.deviation)
        return new_attack_modifier, new_defend_modifier, new_preserve_modifier 

class RevanchismRule(Rule):
    """Allow each player a chance for comeback.
    Player can be granted a "revanchism" status for 5 turns when (1) is smallest player in the game, (2) is under 2 provinces & 10 units, and (3) only has 20% of the total power of the largest player.
    Only one player can be granted the status. Each player can only be granted once.
    When in this status, player attack/defense is increased by 30%, deployment is doubled."""
    def __init__(self, campaign, status_duration: int=5, status_combat_coef: float=0.3, status_deploy_coef: float=2.0):
        super(RevanchismRule, self).__init__(campaign)
        self.status_duration = status_duration 
        self.status_combat_coef = status_combat_coef
        self.status_deploy_coef = status_deploy_coef
        # if a player is in revanchism, the id & the turn when this trigger is recorded.
        self.current_affected_player = self.affected_turn = None 
        # if a player had spent their chance, they are barred from triggering it again 
        self.spent = set() 
    
    def _trigger_condition(self, player_id: int): 
        if self.current_affected_player is not None:
            return False 
        if player_id in self.spent:
            return False 
        context = self.campaign._context 
        player_province_count, player_army_size, biggest_army_size = context["total_owned"][player_id], context["army_size"][player_id], max(context["army_size"].values())
        trigger = (player_id == context["smallest_player"]) \
                  and (player_province_count <= 2 and player_army_size <= 10) \
                  and (player_army_size <= biggest_army_size * 0.2)
        return trigger 

    def end_phase(self):
        if self.current_affected_player is None:
            # attempting logic for revanchism if none is in effect
            for player_id in range(self.campaign._player_count):
                if self._trigger_condition(player_id):
                    print("RevanchismRule triggered for [P{:d}]!".format(player_id))
                    self.current_affected_player = player_id
                    self.affected_turn = self.campaign._context["turn"]
                    self.spent.add(player_id)
                    break # only occur for one
        else:
            # if during revanchism, check for expiration and if does, delete the property 
            if self.affected_turn + self.status_duration <= self.campaign._context["turn"]:
                print("RevanchismRule expired for [P{:d}]".format(self.current_affected_player))
                self.current_affected_player = self.affected_turn = None 


    def affect_attack(self, attack_modifier: float, defend_modifier: float, preserve_modifier: float, attack_strength: int, defend_strength: int, attacker_id: int, defender_id: int, target_province_id: int): 
        if self.current_affected_player is not None: 
            if attacker_id == self.current_affected_player:
                # attack initiated by designated player
                new_attack_modifier = attack_modifier * (1.0 + self.status_combat_coef)
                return new_attack_modifier, defend_modifier, preserve_modifier
            elif defender_id == self.current_affected_player:
                # defense targetting designated player
                new_defend_modifier = defend_modifier * (1.0 + self.status_combat_coef)
                return attack_modifier, new_defend_modifier, preserve_modifier 
        return attack_modifier, defend_modifier, preserve_modifier 

    def affect_deployment(self, deploy_strength: int, deploy_distance_from_front: int, deployer_id: int, target_province_id: int):
        if self.current_affected_player is not None and self.current_affected_player == deployer_id:
            new_deploy_strength = int(deploy_strength * self.status_deploy_coef)
            new_deploy_distance_from_front = deploy_distance_from_front + 1 
            return new_deploy_strength, new_deploy_distance_from_front
        return deploy_strength, deploy_distance_from_front 

CORE_ICON_UNICODE_VALUE = ord("\u2780")
class CoreRule(Rule):
    """If used, each province will has a "core" property indicating population loyalty. Core is declared by 1st occupier from unowned ground. Core can be allowed to drift after an amount of turns if specified to allow so.
    When fighting on non-core region against rightful owner, player will suffer small penalty to combat effectiveness, and a moderate penalty for occupation.
    NOTE: this must go after TerrainRule if any; due to it affecting preserve_modifier
    """
    def __init__(self, campaign, core_drift_duration: Optional[int]=None, core_combat_coef: float=0.1, noncore_preserve_penalty: float=0.5):
        super(CoreRule, self).__init__(campaign)
        # save the properties
        self.core_drift_duration = core_drift_duration
        self.core_combat_coef = core_combat_coef
        self.noncore_preserve_penalty = noncore_preserve_penalty  
        # set the core mechanism
        for *_, p in self.campaign._map:
            p["core"] = p["owner"]
            if self.core_drift_duration:
                p["core_drift"] = 0

    def affect_attack(self, attack_modifier: float, defend_modifier: float, preserve_modifier: float, attack_strength: int, defend_strength: int, attacker_id: int, defender_id: int, target_province_id: int): 
        target = self.campaign._map[target_province_id][-1]
        if target["core"] is not None:
            right_owner_id = target["core"]
            if attacker_id == right_owner_id: # decrease enemy defense
                new_defend_modifier = defend_modifier * (1.0 - self.core_combat_coef)
                return attack_modifier, new_defend_modifier, preserve_modifier
            elif defender_id == right_owner_id: # decrease enemy attack & increase penalty to 
                new_attack_modifier = attack_modifier * (1.0 - self.core_combat_coef)
                new_preserve_modifier = preserve_modifier + self.noncore_preserve_penalty 
                return new_attack_modifier, defend_modifier, new_preserve_modifier
        return attack_modifier, defend_modifier, preserve_modifier 

    def after_attack(self, player_id: int, full_result):
        result, province, casualty = full_result  
        if not result:
            return
        if province["core"] is None:
            # first occupation; granting core for the attacker 
            province["core"] = player_id 
        if self.core_drift_duration:
            p["core_drift"] = 0 

    def end_phase(self):
        if self.core_drift_duration is None:
            # core drift mechanism disabled 
            return  
        for *_, p in self.campaign._map:
            if p["core"] != p["owner"]:
                p["core_drift"] += 1
                if p["core_drift"] >= self.core_drift_duration:
                    p["core"] = p["owner"] 
                    p["core_drift"] = 0
                    print("@CoreRule: province {} had became core of [P{:d}]".format(p["province_name"], p["core"]))

    def modify_draw_map(self, draw_map):
        for *_, p in draw_map:
            if p["core"] is not None:
                # symbol is 1-10, so by plusing index0 it will just match what we need
                p["symbol"] = p.get("symbol", "") + chr(CORE_ICON_UNICODE_VALUE+p["core"])
