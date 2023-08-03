"""Bot to control actions in the campaign map.
Will calculate the targetting for moving & attacking, and where to deploy for best effect. 
Should have multiple criteria / selectable coefficient to prioritize different things."""
import random

from typing import Optional, List, Tuple, Any, Union, Dict 

class Bot:
    """Default interface for a bot."""
    def __init__(self, player_id: int, campaign: Any):
        self.player_id = player_id
        self._campaign = campaign 

    def calculate_attacks(self, campaign_map: List[Tuple[Any, Dict]], expected_attack_coef: float=1.0) -> Optional[Tuple[int, int, int]]:
        """This should return None or (source, target, attack_amount); will be re-verified by the campaign"""
        raise NotImplementedError

    def calculate_movement(self, campaign_map: List[Tuple[Any, Dict]], allowable_range: int=2) -> Optional[Tuple[int, int, int]]:
        """This should return None or (source, target, movement_amount); will be re-verified by the campaign"""
        raise NotImplementedError

    def calculate_deployment(self, campaign_map: List[Tuple[Any, Dict]], deployable: int) -> Optional[int]:
        """This should return None or deploy_region; will be re-verified by the campaign"""
        raise NotImplementedError 


class RandomBot(Bot):
    # Do everything randomly for now 
    def calculate_attacks(self, campaign_map, expected_attack_coef=1.0) -> Optional[Tuple[int, int, int]]:
        attack_vectors = self._campaign.all_attack_vectors(self.player_id)
        if len(attack_vectors) == 0:
            return None
        return random.choice(attack_vectors)

    def calculate_movement(self, campaign_map, allowable_range=2) -> Optional[Tuple[int, int, int]]:
        owned_provinces = self._campaign.all_owned_provinces(self.player_id)
        possible_source = [ip for ip in owned_provinces if campaign_map[ip][-1]["units"] > 0]
        if len(possible_source) == 0:
            return None
        source = random.choice(possible_source)
        possible_target = self._campaign.check_range(source, expected_range=allowable_range, owner=self.player_id) - {source}
        if len(possible_target) == 0:
            return None
        target = random.choice(list(possible_target))
        max_movable = campaign_map[source][-1]["units"] - 1
        amount = max(int(random.random() * max_movable), 1) # move at least 1 unit 
        return (source, target, amount)

    def calculate_deployment(self, campaign_map, deployable: int) -> Optional[int]:
        if deployable <= 0:
            return None 
        deployable_provinces = self._campaign.all_deployable_provinces(self.player_id)
        return random.choice(list(deployable_provinces))

class LandGrabBot(Bot):
    """Bot with coefficients for largest/fastest landgrab.
    First coefficient is certainty, the sorting coefficient for safety in grabbing the province; this can be a flat number, or a function
    Second coefficient is return, the sorting coefficient for gain of grabbing the province; the higher score of the province, the better number you got. 
    Third coefficient to prevent deadlock if two bot started competing over a weak province; the higher the score, the more likely that the bot will try to take unowned provinces first
    Grabbing the biggest province is dangerous because a counterattack may just get it back (as the deadlock demonstrated), hence the need for the 2nd and/or 3rd
    """
    def __init__(self, *args, merge=False, certainty_coef: float=1.0, return_coef: float=0.0, unowned_coef: float=10.0):
        # by default, do a landgrab with no afterthought of defense or gain 
        # always vastly prefer an unowned province
        # probably very retarded
        if not merge:
            super(LandGrabBot, self).__init__(*args)
        self.certainty_coef = certainty_coef
        self.return_coef = return_coef 
        self.unowned_coef = unowned_coef

    def _sorting_coef(self, campaign_map, source_id: int, target_id: int, available: Optional[int]=None) -> float:
        # calculate the score & validity of an action 
        # return the expected score of an attack and the actual value for attacking
        if available is None: # maybe throw this away?
            available = campaign_map[source_id][-1]["units"] - 1
        defense = campaign_map[target_id][-1]["units"]
        gain = campaign_map[target_id][-1]["score"]
        unowned = int(campaign_map[target_id][-1]["owner"] is None)
        # allow conditional
        if callable(self.certainty_coef):
            score = self.certainty_coef(available, defense)
        else:
            score = (available - defense) * self.certainty_coef 
        score += gain * self.return_coef + unowned * self.unowned_coef
        return score

    def calculate_attacks(self, campaign_map, expected_attack_coef=1.0) -> Optional[Tuple[int, int, int]]:
        attack_vectors = self._campaign.all_attack_vectors(self.player_id)
        if len(attack_vectors) == 0:
            return None 
        best = max(attack_vectors, key=lambda v: self._sorting_coef(campaign_map, v[0], v[1], available=v[2]))
        return best 

    def calculate_movement(self, campaign_map, allowable_range=2) -> Optional[Tuple[int, int, int]]:
        # list all possible vectors, even the zero ones
        attack_vectors = self._campaign.all_attack_vectors(self.player_id, show_zero_attack=True)
        # for each source province in the attack_vectors, check the highest reinforcement from anywhere available 
        all_sources = {s for s, t, a in attack_vectors}
        owned = self._campaign.all_owned_provinces(self.player_id)
        max_reinforce = dict()
        for sid in all_sources:
             available_reinforce = self._campaign.check_range(sid, expected_range=allowable_range, owner=self.player_id) - {sid}
             highest = max(((rp, campaign_map[rp][-1]["units"] - 1) for rp in available_reinforce), key=lambda x: x[1], default=(None, 0)) # rp is reinforce_province
             if highest[1] > 0: # has reinforcement available:
                 max_reinforce[sid] = highest 
        # calculate the best score AFTER the reinforcement 
#        print("[Debug] Max reinforcement in a province-basis: {}".format(max_reinforce))
        best_source, _, _ = max(attack_vectors, key=lambda v: self._sorting_coef(campaign_map, v[0], v[1], available=v[2]+max_reinforce.get(v[0], (None, 0))[1]), default=(None, None, None))
        if best_source in max_reinforce:
            # has to reinforce this province with that maximum amount
            reinforce_province, reinforce_amount = max_reinforce[best_source]
            return (reinforce_province, best_source, reinforce_amount)
        else:
            # best source can't reinforce from anywhere anyway
            # TODO sort for second-best?
            return None 

    def calculate_deployment(self, campaign_map, deployable: int) -> Optional[int]:
        # just deploy randomly for now
        return RandomBot.calculate_deployment(self, campaign_map, deployable)
