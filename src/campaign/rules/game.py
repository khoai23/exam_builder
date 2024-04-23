"""Game-wide rules, mainly affecting players."""
import random

from src.campaign.rules.base_campaign import Rule 

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
