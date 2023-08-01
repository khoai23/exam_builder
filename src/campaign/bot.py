"""Bot to control actions in the campaign map.
Will calculate the targetting for moving & attacking, and where to deploy for best effect. 
Should have multiple criteria / selectable coefficient to prioritize different things."""
import random

from typing import Optional, List, Tuple, Any, Union, Dict 

class Bot:
    """Default interface for a bot."""
    def calculate_attacks(self, campaign_map: List[Tuple[Any, Dict]], expected_attack_coef: float=1.0) -> Optional[Tuple[int, int, int]]:
        """This should return None or (source, target, attack_amount); will be re-verified by the campaign"""
        raise NotImplementedError

    def calculate_movement(self, campaign_map: List[Tuple[Any, Dict]], allowable_range: int=2) -> Optional[Tuple[int, int, int]]:
        """This should return None or (source, target, movement_amount); will be re-verified by the campaign"""
        raise NotImplementedError

    def calculate_deployment(self, campaign_map: List[Tuple[Any, Dict]], deployable: int) -> Optional[int]:
        """This should return None or deploy_region; will be re-verified by the campaign"""
        raise NotImplementedError 


def RandomBot(Bot):
    # Do everything randomly for now 
    def __init__(self, player_id: int, campaign: Any):
        self.player_id = player_id
        self._campaign = campaign

    def calculate_attacks(self, campaign_map, expected_attack_coef=1.0) -> Optional[Tuple[int, int, int]]:
        attack_vectors = self._campaign.all_attack_vectors(self.player_id)
        return random.choice(attack_vectors)

    def calculate_movement(self, campaign_map, allowable_range=2) -> Optional[Tuple[int, int, int]]:
        owned_provinces = self._campaign.all_owned_provinces(self.player_id)
        possible_source = [ip for ip in owned_provinces if campaign_map[ip][-1]["units"] > 0]
        if len(possible_source) == 0:
            return None
        source = random.choice(possible_source)
        possible_target = self._campaign.check_range(source, expected_range=allowable_range, owner=self.player_id) - {source}
        target = random.choice(possible_target)
        amount = max(int(random.random() * campaign_map[ip]), 1) # move at least 1 unit 
        return (source, target, amount)

    def calculate_deployment(self, campaign_map, deployable: int) -> Optional[int]:
        if deployable <= 0:
            return None 
        deployable_provinces = self._campaign.all_deployable_provinces(self.player_id)
        return random.choice(deployable_provinces)

