"""Base campaign that allows specific behaviors on "Rule". This should allow customizable option so I can try out all the new ideas"""
from abc import ABC, abstractmethod

from src.campaign.default import PlayerCampaignMap as DefaultCampaignMap

from typing import Optional, List, Tuple, Any, Union, Dict 

class Rule(ABC):
    """Generic base for rule. Either phase-based (allow specific modifier to happen before/after specific phase) or action-based (allow specific modifier to affect the outcome of action)""" 
    def __init__(self, campaign):
        self.campaign = campaign

    # phase-based function
    def deployment_phase(self, player_id: int, reinforcement_coef: float, disbanding_coef: float):
        return reinforcement_coef, disbanding_coef

    def movement_phase(self, player_id: int):
        pass 

    def attack_phase(self, player_id: int):
        pass  

    def end_phase(self):
        pass # this one is unique in that it only run once per whole turn; instead of one per player for the above 3.

    # action-based function 
    def affect_attack(self, attack_modifier: float, defend_modifier: float, preserve_modifier: float, # affected modifiers
            attack_strength: int, defend_strength: int, attacker_id: int, defender_id: int, target_province_id: int): # additional info
        return attack_modifier, defend_modifier, preserve_modifier

    def affect_deployment(self, deploy_strength: int, deploy_distance_from_front: int, # affected result
            deployer_id: int, target_province_id: int): # additional info
        return deploy_strength, deploy_distance_from_front

    def affect_movement(self, move_strength: int, move_distance: int, 
            mover_id: int, source_province_id: int, target_province_id: int):
        return move_strength, move_distance

    def after_attack(self, player_id: int, result: Tuple[Any]):
        pass 

    def after_deployment(self, player_id: int, result: Tuple[Any]):
        pass 

    def after_movement(self, player_id: int, result: Tuple[Any]):
        pass 

    # visual representation 
    def modify_draw_map(self, draw_map: List[Any]):
        return draw_map

class BaseCampaign(DefaultCampaignMap):
    """Same as DefaultCampaignMap; except will allow rules to modify specifics of campaign."""
    def __init__(self, *args, rules: List[Rule]=[], **kwargs): 
        super(BaseCampaign, self).__init__(*args, **kwargs) 
        self.rules = [rule_cls(self) for rule_cls in rules]

    # phase-based injection 
    def phase_deploy_reinforcement(self, player_id: int, player_province: set, reinforcement_coef: float=0.5, disbanding_coef: float=0.25):
        """TODO make these coef affect in perform_action_deploy instead."""
        for r in self.rules:
            reinforcement_coef, disbanding_coef = r.deployment_phase(player_id, reinforcement_coef, disbanding_coef)
        return super(BaseCampaign, self).phase_deploy_reinforcement(player_id, player_province, reinforcement_coef=reinforcement_coef, disbanding_coef=disbanding_coef)

    def phase_perform_movement(self, player_id: int, override_action: Optional[list]=None):
        for r in self.rules:
            r.movement_phase(player_id)
        return super(BaseCampaign, self).phase_perform_movement(player_id, override_action=override_action)

    def phase_perform_attack(self, player_id: int, override_action: Optional[list]=None):
        for r in self.rules:
            r.attack_phase(player_id)
        return super(BaseCampaign, self).phase_perform_attack(player_id, override_action=override_action)

    # action-based injection
    def perform_action_attack(self, player_id: int, attacking: int, target_id: int, attack_modifier: float=1.0, defend_modifier: float=1.0, preserve_modifier: float=2.0):
        """Inject and allow rules to affect the attacking procedure.
        Should be affecting the tuple of modifiers and end up with proper outcome of battles."""
        target = self._map[target_id][-1]
        attack_strength, defend_strength, attacker_id, defender_id, target_province_id = attacking, target["units"], player_id, target["owner"], target_id
        for r in self.rules:
            attack_modifier, defend_modifier, preserve_modifier = r.affect_attack(attack_modifier, defend_modifier, preserve_modifier, attack_strength, defend_strength, attacker_id, defender_id, target_province_id)
        # after all changes, values are then fed into the real function 
        full_result = super(BaseCampaign, self).perform_action_attack(player_id, attacking, target_id, attack_modifier=attack_modifier, defend_modifier=defend_modifier, preserve_modifier=preserve_modifier)
        for r in self.rules:
            r.after_attack(attacker_id, full_result)
        return full_result

    def perform_action_movement(self, move: int, source_id: int, target_id: int, allowable_range: int=2) -> Tuple[bool, str]:
        """Inject and allow rules to affect the movement procedure.
        Should be affecting how many & how far the movement can be accomplished."""
        source = self._map[source_id][-1]
        move_strength, move_distance, mover_id, source_province_id, target_province_id = move, allowable_range, source["owner"], source_id, target_id
        for r in self.rules:
            move_strength, move_distance = r.affect_movement(move_strength, move_distance, mover_id, source_province_id, target_province_id)
        result = super(BaseCampaign, self).perform_action_movement(move_strength, source_id, target_id, allowable_range=move_distance)
        for r in self.rules:
            r.after_movement(mover_id, result)
        return result

    def perform_action_deploy(self, deploy: int, target_id: int, distance_from_front: int=2, recheck: bool=True):
        """Inject and allow rules to affect the deploying procedure.
        Should affect amount of deployed units & how close it could be deployed from the front"""
        target = self._map[target_id][-1]
        deploy_strength, deploy_distance_from_front, deployer_id, target_province_id = deploy, distance_from_front, target["owner"], target_id
        for r in self.rules:
            deploy_strength, deploy_distance_from_front = r.affect_deployment(deploy_strength, deploy_distance_from_front, deployer_id, target_province_id)
        full_result = super(BaseCampaign, self).perform_action_deploy(deploy_strength, target_id, distance_from_front=deploy_distance_from_front, recheck=recheck)
        for r in self.rules:
            r.after_deployment(deployer_id, full_result)
        return full_result

    def end_turn(self, *args, **kwargs):
        result = super(BaseCampaign, self).end_turn(*args, **kwargs)
        for r in self.rules:
            r.end_phase()
        return result

    def retrieve_draw_map(self, colorscheme: List[str]=None, default="white"):
        result = super(BaseCampaign, self).retrieve_draw_map(colorscheme=colorscheme, default=default)
        for r in self.rules:
            r.modify_draw_map(result)
        return result
