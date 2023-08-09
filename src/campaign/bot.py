"""Bot to control actions in the campaign map.
Will calculate the targetting for moving & attacking, and where to deploy for best effect. 
Should have multiple criteria / selectable coefficient to prioritize different things."""
import random 
from collections import defaultdict

from typing import Optional, List, Tuple, Any, Union, Dict, Set

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
    def __init__(self, *args, merge=False, certainty_coef: float=1.0, return_coef: float=0.0, unowned_coef: float=10.0, limit_attack_force: bool=False):
        # by default, do a landgrab with no afterthought of defense or gain 
        # always vastly prefer an unowned province
        # probably very retarded
        if not merge:
            super(LandGrabBot, self).__init__(*args)
        self.certainty_coef = certainty_coef
        self.return_coef = return_coef 
        self.unowned_coef = unowned_coef 
        self.limit_attack_force = limit_attack_force

    def _sorting_coef(self, campaign_map, source_id: int, target_id: int, available: Optional[int]=None) -> float:
        # calculate the score & validity of an action 
        # return the expected score of an attack
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
        if self.limit_attack_force:
            # if this flag is enabled; only attack with the minimum force needed along with the attack coefficient 
            source_id, target_id, max_attack = best 
            true_attack = int(campaign_map[target_id][-1]["units"] / expected_attack_coef) + 1
            return (source_id, target_id, true_attack)
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

class FrontlineBot(Bot):
    """A bot that prioritize taking regions that are defensible, and distribute deployed units to the front even-ish"""
    def __init__(self, *args, merge=False, defensiveness_coef: float=-1.0, distance_coef: float=-0.25, reinforcement_coef: float=10.0):
        # by default, prioritize grabbing provinces that are defensible (least vectors of attacks) and close to the capital 
        # if grabbing this province allow reinforcement to immediately deploy to defend it, also give it a bonus
        if not merge:
            super(FrontlineBot, self).__init__(*args)
            self.defensiveness_coef = defensiveness_coef
            self.distance_coef = distance_coef
            self.reinforcement_coef = reinforcement_coef

    def _sorting_coef(self, campaign_map, source_id: int, target_id: int, available: Optional[int]=None, merge: bool=False) -> float:
        # count the number of hostile province bordering it
        target_connections = campaign_map[target_id][-1]["connection"]
        hostile_connections = set(bp for bp in target_connections if campaign_map[bp][-1]["owner"] != self.player_id and campaign_map[bp][-1]["owner"] is not None)
        # count direct distance to current capital 
        capital = self._campaign.capital(self.player_id)
        distance_to_capital = self._campaign.check_distance(capital, target_id) if capital is not None else 0
        # count possible "plug" - if another tile became possible to reinforce from occupying this tile, this will count as a yes 
        all_owned = self._campaign.all_owned_provinces(self.player_id)
        reinforcement_blocker = ({np for np in self._campaign.check_range(ip, 2) if campaign_map[np][-1]["owner"] != self.player_id} for ip in all_owned) # np for neighbor_province 
        capturing_will_unblock = any((len(blks) == 1 and target_id in blks for blks in reinforcement_blocker))
        # calculate 
        # with a bit extra for availability
        score = self.defensiveness_coef * len(hostile_connections) + self.distance_coef * distance_to_capital + self.reinforcement_coef * int(capturing_will_unblock)
        if not merge:
            # add extra for availability & possible load 
            score += 0.1 * available 
            score += 0 if available > campaign_map[target_id][-1]["units"] else -99
        return score

    def calculate_attacks(self, campaign_map, expected_attack_coef=1.0, always_attack: bool=False) -> List[Tuple[int, int, int]]:
        attack_vectors = self._campaign.all_attack_vectors(self.player_id)
        if len(attack_vectors) == 0:
            return None 
        # condense the possible attack vectors to maximum achievable
        total_vectors = defaultdict(int)
        for s, i, a in attack_vectors:
            total_vectors[i] += a
        best = max(total_vectors.items(), key=lambda v: self._sorting_coef(campaign_map, None, v[0], available=v[1]))
        # only attack with enough force to occupy with expected_attack_coef. 
        target_id, max_attack = best 
        true_attack = int(campaign_map[target_id][-1]["units"] / expected_attack_coef) + 1
        if true_attack > max_attack:
            # not enough force; if not always_attack, return None
            if not always_attack:
                return None 
            # if do, set the true_attack down to max_attack again
            true_attack = max_attack
        highest_to_lowest = sorted([s for s in attack_vectors if s[1] == target_id], key=lambda v: v[-1], reverse=True)
        # distribute accordingly between all valid attack vectors, highest first
        attacks = []
        for s, t, a in highest_to_lowest:
            if a >= true_attack:
                attacks.append((s, t, true_attack))
                return attacks # finished iteration, all attacks needed had been created
            else:
                attacks.append((s, t, a))
                true_attack -= a # need more attack, deduce and go to next iter 
        # should not reach here 
        raise NotImplementedError
        return (source_id, target_id, true_attack)

    def province_distance_to_frontline(self, province_id: int, frontline: Set[int]):
        # check the distance from a province_id to a frontline. Use cached distance to reduce complexity 
        if province_id in frontline:
            return 0 
        return min((self._campaign.check_distance(province_id, i) for i in frontline))

    def calculate_movement(self, campaign_map, allowable_range=2) -> List[Tuple[int, int, int]]:
        # distribute all moveable units across frontline, tile with more outward connections first.
        all_owned = self._campaign.all_owned_provinces(self.player_id)
        # all frontline tile, weighted by number of hostile connections
        frontline = {ip for ip in all_owned if any((campaign_map[np][-1]["owner"] != self.player_id for np in campaign_map[ip][-1]["connection"]))}
        weighted = {i: len({np for np in campaign_map[i][-1]["connection"] if campaign_map[np][-1]["owner"] != self.player_id}) for i in frontline}
        # all moveable tile 
        tiles = {i: campaign_map[i][-1]["units"] - 1 for i in all_owned}
        movable_units = {i:u for i, u in tiles.items() if u > 0}
        # perform distribution. First, calculate the full number, and allot to each weighted tile accordingly
        all_movable = sum(movable_units.values())
        all_tile_weight = sum(weighted.values())
        distribute = { i: int(all_movable * w / all_tile_weight) for i, w in weighted.items() }
        if sum(distribute.values()) < all_movable:
            # still have leftover
            # assuming that remainder of distribution will have < 1 unit per all possible tiles. 
            # TODO if not, need a different equation 
            remaining = all_movable - sum(distribute.values())
            for i, w in sorted(weighted.items(), key=lambda it: it[0], reverse=True):
                if remaining <= 0:
                    break # no more remaining
                # from high to low, distribute the remaining points 
                distribute[i] += 1
                remaining -= 1
            # if still has remainder, spawn a warning 
            if remaining > 0:
                print("Frontline distribution still have {} units remaining.".format(remaining))
        print("Expected distribution: ", distribute)
        # Second, find set of all appropriate movements to best put all units to necessary positions 
        # TODO minimize the amount of movements needed 
        movements = dict() 
        while len(distribute) > 0:
            # attempt to move point-by-point from distribution toward movement, least possible first 
            scored_target = {ip: sum((movable_units[sp] for sp in self._campaign.check_range(ip, allowable_range, owner=self.player_id) if sp in movable_units)) for ip in distribute} # sp is source province
            # get the least connective tile as target 
            target, _ = min(scored_target.items(), key=lambda it: it[1])
            # from this tile, get the corresponding least connective source 
            scored_source = {ip: sum((distribute[tp] for tp in self._campaign.check_range(ip, allowable_range, owner=self.player_id) if tp in distribute))
                    for ip in self._campaign.check_range(target, allowable_range, owner=self.player_id) if ip in movable_units}
            if len(scored_source) == 0:
                print("Cannot find valid reinforcement tile; reinforcing {} failed.".format(target))
                distribute.pop(target)
                continue
            source, _ = min(scored_source.items(), key=lambda it: it[1])
            # check appropriate transfer amount between source -> target 
            source_available = movable_units[source]
            target_required = distribute[target]
            if source_available > target_required:
                amount = target_required
                distribute.pop(target)
                movable_units[source] -= amount 
            elif target_required > source_available:
                amount = source_available
                distribute[target] -= amount 
                movable_units.pop(source)
            else:
                amount = source_available # either is fine 
                distribute.pop(target)
                movable_units.pop(source)
            # put into possible movements 
            if source == target:
                # somehow attempt to move to self, dont have to perform 
                pass
            else:
                print("[Debug] moving request {} -> {} ({})".format(source, target, amount))
                assert (source, target) not in movements, "Algorithm should not have duplicate attempt; but has {} - ({}, {})".format(movements, source, target)
                movements[(source, target)] = amount  
        # if there is still movable units; check if there is a "better" tile to move to; better here being closest to the frontline 
        for source, amount in movable_units.items():
            possible = [tp for tp in self._campaign.check_range(source, allowable_range, owner=self.player_id) if tp in all_owned]
            best_target = min(possible, key=lambda i: self.province_distance_to_frontline(i, frontline) * 100 + len(campaign_map[i][-1]["connection"])) # between same distance, use the one with the most connection 
            if source != best_target:
                # move if they are different 
                print("[Debug] additional moving request {} -> {} ({})".format(source, best_target, amount))
                movements[(source, best_target)] = amount
        # after everything ran, convert back to a default movement format 
        true_movements = [(s, t, a) for (s, t), a in movements.items()]
        return true_movements
    
    def calculate_deployment(self, campaign_map, deployable: int) -> Optional[int]:
        if deployable <= 0:
            return None 
        deployable_provinces = self._campaign.all_deployable_provinces(self.player_id)
        # deploy on the most connective positions. TODO deploy in anticipation of the reinforcement phase
        best = max(deployable_provinces, key=lambda dp: len(self._campaign.check_range(dp, 2, owner=self.player_id)))
        return best
