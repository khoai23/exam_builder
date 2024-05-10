import random

from typing import Optional, List, Tuple, Any, Union, Dict, Callable

from src.campaign.rules.base_campaign import BaseCampaign 

import logging
logger = logging.getLogger(__name__)

class PlayerCampaign(BaseCampaign):
    """Version of campaign map that support player actions instead of bots. The bot can still be used for suggestion and/or substitution.
    """
    def __init__(self, *args, players: List[int]=None, **kwargs):
        super(PlayerCampaign, self).__init__(*args, **kwargs)
        self._is_players = set(players)
        self._player_coef = None
        self._action_dict = {}
        self._current_phase = "deploy"

    @property
    def current_phase(self):
        return self._current_phase 

    def set_player_coef(self, value: float):
        # this should be result of a randomly generated quiz; detailing the coef going to be used in the next offense/defense phase.
        # TODO set different values for different phase? 
        self._player_coef = value
        logger.info("PlayerCampaign: p-coef is set as {}".format(self._player_coef))

    def perform_action_attack(self, player_id: int, attacking: int, target_id: int, attack_modifier: float=1.0, defend_modifier: float=1.0, preserve_modifier: float=2.0):
        if self._player_coef:
            if player_id in self._is_players:
                logger.info("Attack initiated by player with completed quiz; modifier: {}".format(self._player_coef))
                attack_modifier = self._player_coef
            target = self._map[target_id][-1]
            if target["owner"] in self._is_players:
                logger.info("Defend done by player with completed quiz; modifier: {}".format(self._player_coef))
                defend_modifier = self._player_coef
        return super(PlayerCampaign, self).perform_action_attack(player_id, attacking, target_id, attack_modifier=attack_modifier, defend_modifier=defend_modifier, preserve_modifier=preserve_modifier)


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
