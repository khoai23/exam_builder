"""Appropriate form of the campaign game.
Each player have an amount of units to be distributed on all its controlled tiles. It also have a "capital", which is either its first starting tile, or the highest value tile the player still control
Each tile have a score, the sum of this score decide the amount of units each player has. If the number exceeded this sum, units are disbanded randomly. If the number is less, new units will spawn in any tile -3 away from nearest hostile tile.
For every turn, each player get to move a number of adjacent units against one external tile. If that exceeds the units presently on the tile, the tile is captured by half of the remaining attacking unit. If not, substract upto -1 of attacker units on both side.
Winning condition is achieved by having 75% of total tile points."""
import random

from src.campaign.bot import Bot, RandomBot, LandGrabBot
from src.campaign.name import NameGenerator, RussianNameGenerator
from src.map import generate_map_by_region, generate_map_by_subregion, format_arrow

from typing import Optional, List, Tuple, Any, Union, Dict 

class CampaignMap:
    """The map on which the game is played."""
    def __init__(self, player_count: int=4, region_count: int=9, subregion_count: int=6, capital_point: int=10, region_point=30, 
            bot_class: Bot=RandomBot, name_generator: Optional[NameGenerator]=None):
        self._player_count = player_count 
        # create random bot that handle the actions done by player
        self._player_bot = [bot_class(i, self) for i in range(player_count)]
        # generate by region; this should help causing hubbed map 
        # TODO make varied subregions
        distribution = [dict(category=str(rg), tag=str(i)) for rg in range(region_count) for i in range(subregion_count)]
        regions = generate_map_by_subregion(distribution, bundled_by_category=True, do_recenter=True, do_shrink=0.98, return_connections=True)
        # with the map created, assign appropriate player capital & ensure each region have relatively same score 
        player_starter = random.sample(list(range(region_count)), player_count)
        self._original_capital = {}
        for i, tiles in enumerate(regions.values()):
            distribution = region_point
            if i in player_starter:
                # apply the capital in a random province 
                self._original_capital[player_starter.index(i)] = capital_id = random.choice(list(range(len(tiles))))
                capital = tiles[capital_id][-1]
                capital["score"] = capital_point
                capital["owner"] = player_starter.index(i)
                capital["units"] = capital_point 
                capital["is_capital"] = True
                distribution -= capital_point
                tiles = [t for t in tiles if t[-1] != capital]
                # print("Player {:d} has capital setting {}".format(capital["owner"], capital))
            # for all applicable tiles, distribute point-by-point, favor higher. TODO better distribution
            points = [1] * len(tiles)
            ids = list(range(len(tiles)))
            while sum(points) < distribution:
                # TODO prevent lopsided point distribution; capital should be the highest one
                next_id = random.choices(ids, weights=[p if p < 10 else 0 for p in points], k=1)[0]
                if points[next_id] >= 10:
                    # point should not be higher than 10 rn. TODO codify as a variable
                    continue
                points[next_id] += 1
            # once fully distributed; set the tiles values & ownership
            for p, (*_, t) in zip(points, tiles):
                t["score"] = p
                t["owner"] = None
                t["units"] = p
                t["is_capital"] = False
        # once all regions accounted for, flatten
        self._map = [subregion for region in regions.values() for subregion in region]
        # if NameGenerator is specified; use it to generate specific name for the region 
        if name_generator:
            # TODO allow extra kwargs for deeper control
            province_names = name_generator.batch_generate_name(len(self._map), name_generator.generate_province_name)
            for n, (*_, m) in zip(province_names, self._map):
                m["province_name"] = n
        # build cached distance for quick usage 
        self.build_cached_distance()
        print("Created map with {} subregion".format(len(self._map)))
    
    def build_cached_distance(self):
        # generate cached distance between all provinces.
        self._cached_distance = dict()
        # direct neighbors (distance = 1)
        for i, (*_, p) in enumerate(self._map):
            connections = p["connection"]
            for j in connections:
                key = (i, j) if i < j else (j, i)
                if key not in self._cached_distance:
                    self._cached_distance[key] = 1
        # while not reaching the alloted key (n*(n-1)/2); keep updating the distance 
        expected_size = len(self._map) * (len(self._map) - 1) // 2
        current_distance = 2
        while len(self._cached_distance) < expected_size:
            # keep an old size for log 
            old_size = len(self._cached_distance)
            # plus all possible distance together 
            # have to do list instead of generator due to update
            distance_1 = [d1 for d1, k1 in self._cached_distance.items() if k1 == 1]
            distance_other = [do for do, ko in self._cached_distance.items() if ko == (current_distance - 1)]
            for d1_1, d1_2 in distance_1:
                for do_1, do_2 in distance_other:
                    # check if they bind together 
                    if d1_1 == do_1:
                        # same lower, need to check
                        if d1_2 != do_2:
                            # can bind together 
                            key = (d1_2, do_2) if d1_2 < do_2 else (do_2, d1_2)
                            if key not in self._cached_distance:
                                # is indeed the smallest values; put in 
                                self._cached_distance[key] = current_distance 
                    elif d1_2 == do_1:
                        # key will always be d1_1, do_2 since they are ordered 
                        if (d1_1, do_2) not in self._cached_distance:
                            self._cached_distance[(d1_1, do_2)] = current_distance
                    elif d1_1 == do_2:
                        # key will always be do_1, d1_2 since they are ordered 
                        if (do_1, d1_2) not in self._cached_distance:
                            self._cached_distance[(do_1, d1_2)] = current_distance
                    elif d1_2 == do_2:
                        # same upper, need to check order, not equality
                        key = (d1_1, do_1) if d1_1 < do_1 else (do_1, d1_1)
                        if key not in self._cached_distance:
                            # is indeed the smallest values; put in 
                            self._cached_distance[key] = current_distance 
            # print update to debug
            print("_cached_distance updated: {} -> {} for {}".format(old_size, len(self._cached_distance), current_distance))

            # after everything, increasing the next calculation
            current_distance += 1
        print("Cached distance created")

    def retrieve_draw_map(self, colorscheme=["yellowgreen", "salmon", "powderblue", "moccasin"], default="transparent"):
        # just use the current map for now 
        # appropriate fg/bg; TODO set bg in accordance with the amount of available units, or maybe transparency?
        for i, srg in enumerate(self._map):
            attr = srg[-1]
            attr["fg"] = colorscheme[attr["owner"]] if attr["owner"] is not None else default
            attr["bg"] = "black"
            attr["name"] = attr.get("province_name", str(i)) + (" \u272A" if attr["is_capital"] else "")
            attr["text"] = "{:d} ({:d}\u2605)".format(attr["units"], attr["score"]) # display only score for now
        return self._map
     
    def check_distance(self, source_id: int, target_id: int):
        # check flat distance between two provinces. Value is cached.
        key = (source_id, target_id) if source_id < target_id else (target_id, source_id)
        return self._cached_distance[key]

    def check_range(self, base: int, expected_range: int, owner: Optional[int]=None) -> set:
        # put all provinces of less than {expected_range} distance from {base} into a set 
        result = set()
        border = [base] # current unit at range, base is range 0
        for _ in range(expected_range):
            next_border = []
            for b in border:
                # check; in mode with owner, only allow province with specific owners to count
                if b not in result and (owner is None or self._map[b][-1]["owner"] == owner):
                    # for each valid border province, add the neighbors to the next border 
                    next_border.extend(self._map[b][-1]["connection"])
                    # also add into result 
                    result.add(b)
            # after everything is done, next iteration will use next_border as border 
            border = next_border
        return result

    def perform_action_attack(self, player_id: int, attacking: int, target_id: int, critical_modifier: float=1.0, preserve_modifier: float=2.0):
        # perform an attack from a player, with up to {attacking} units, to target province
        # allow a "crit" modifier for later upgrade, and a "preserve" ratio which affect the amount of units kept after winning
        # all attacking units should have been consumed
        target = self._map[target_id][-1]
        assert target["owner"] is None or player_id != target["owner"], "Cannot attack same player province {}({})".format(target_id, player_id)
        true_attack = attacking * critical_modifier # multiply by modifier, round 
        if target["units"] > true_attack:
            # less than acceptable; simply subtract from defender, round down
            target["units"] -= int(true_attack)
            return False, target, int(true_attack)
        else:
            # more than acceptable; change ownership and put the remainder on the target 
            defender = target["units"]
            surplus = true_attack - defender
            new_occupant_units = min(max(int(surplus / preserve_modifier), 1), attacking) # minimum 1 occupant, maximum the original attacking force 
            losses = attacking - new_occupant_units
            target["owner"] = player_id
            target["units"] = new_occupant_units 
            # if capital, also delete its own flag. TODO allow a new capital setup/re-enable the flag when recaptured
            target["is_capital"] = False
            # TODO add log 
            return True, target, losses 
     
    def perform_action_movement(self, move: int, source_id: int, target_id: int, allowable_range: int=2) -> Tuple[bool, str]:
        # attempt to move from one province to another. Return the success of the movement & error type if any
        source = self._map[source_id][-1]
        target = self._map[target_id][-1]
        # check 
        if source["owner"] != target["owner"]:
            return False, "can only move in friendly provinces"
        if source["units"] < move + 1:
            return False, "not enough units to move"
        if target_id not in self.check_range(source_id, allowable_range, owner=source["owner"]):
            return False, "{} not in {} range of {}".format(target_id, allowable_range, source_id)
        # everything is ok, performing movement 
        # TODO put into queue, allow multiple movement submission for a phase
        source["units"] -= move 
        target["units"] += move 
        return True, None

    def check_deployable(self, target_id: int, distance_from_front: int=2):
        target = self._map[target_id][-1]
        if target["is_capital"]:
            # complete bypass 
            return True 
        else:
            owner = target["owner"]
            border = self.check_range(target_id, distance_from_front)
            if all((self._map[bp][-1]["owner"] == owner for bp in border)):
                # deep enough, can deploy 
                return True 
            else:
                # not deep enough, ignore 
                return False

    def perform_action_deploy(self, deploy: int, target_id: int, distance_from_front: int=2, recheck: bool=True):
        # attempt to perform a deployment; province is allowed to deploy if it is more than {distance_from_front} away from nearest hostile border, or is the capital of the player.
        # if recheck set to false, no need to check the deployable status
        if not recheck or check_deployable(target_id, distance_from_front=distance_from_front):
            target = self._map[target_id][-1]
            target["units"] += deploy 
            return True 
        else:
            return False

    #=====================
    # Bot-compatible functions.
    def all_owned_provinces(self, player_id: int) -> set:
        return set(ip for ip, p in enumerate(self._map) if p[-1]["owner"] == player_id)

    def all_attack_vectors(self, player_id: int, singular: bool=True, show_zero_attack: bool=False) -> list:
        # see Bot. if singular; only show attacks on province-to-province basis, if not, show all possible strength when attacking 
        # if show_zero_attack, will also list attacks that are zeroes. This is to help calculating reinforcement movement
        player_province = self.all_owned_provinces(player_id) # in id format
        all_bordered = set((bp for ip in player_province for bp in self._map[ip][-1]["connection"]))
        bordered = all_bordered - player_province
        targetable = {ip for ip in bordered if self._map[ip][-1]["owner"] != player_id}
        if singular:
            # all possible vectors
            vectors = ((s, t, self._map[s][-1]["units"]-1) for t in targetable for s in self._map[t][-1]["connection"] if s in player_province)
            # actual vectors (units > 1) if not show_zero_attack
            if show_zero_attack:
                return list(vectors)
            else:
                return [it for it in vectors if it[-1] > 0]
        else:
            raise NotImplementedError
        
    def all_deployable_provinces(self, player_id: int) -> set:
        return {ip for ip in self.all_owned_provinces(player_id) if self.check_deployable(ip)}

    #=====================
    # Convenience function 
    def pname(self, pid: int) -> str:
        """Get province name; return id if not exist"""
        return self._map[pid][-1].get("province_name", str(pid))

    def capital(self, plid: int) -> int:
        """Get capital of specific player id; return None if no capital"""
        return next((ip for ip in self.all_owned_provinces(plid) if self._map[ip][-1]["is_capital"]), None)

    #=====================
    # Test functions.
    def test_start_phase(self):
        # testing the start phase. 
        # If somebody lost a capital, move it to the remaining region with the highest score. If they recaptured it AND it's not bordered with any hostile region, move it back in
        # automatically spawn units to full strength at deployable positions. In real phase, this reinforcement will be multiplied with an improvable coefficient
        # automatically delete random units if the current strength exceeded full. In real phase, this deletion might be partially delayed with a coefficient 
        # automatically delete half of units of a region being surrounded. In real phase, this deletion will be reliant on a coefficient and will happens starting from a 2nd turn; and will also affect a blob of region
        for i in range(self._player_count):
            player_province = self.all_owned_provinces(i) # in id format 
            
            #==========
            # knockout related
            if len(player_province) == 0:
                print("Player {:d} knocked out; phase skipped.".format(i))
                continue
            
            #==========
            # Capital-related
            # check for original capital 
            orig_capital = self._map[self._original_capital[i]][-1]
            if orig_capital["owner"] != i:
                # not owning original; check if new capital had been created, if not, create one 
                if all(not self._map[ip][-1]["is_capital"] for ip in player_province):
                    # no new capital yet, create one 
                    new_capital = max(player_province, key=lambda ip: self._map[ip][-1]["score"])
                    self._map[new_capital][-1]["is_capital"] = True
                    # announce
                    print("New capital for Player {:d} is set at {}".format(i, self.pname(new_capital)))
                # else has new capital; ignore
            else:
                # do own the original capital 
                if not orig_capital["is_capital"]:
                    # ..but not the current capital; check if there is any foreign direct-border region 
                    bordered_foreign = any( (self._map[p][-1]["owner"] != i for p in self._map[self._original_capital[i]][-1]["connection"]) ) 
                    if not bordered_foreign:
                        # safe, move back 
                        for p in player_province:
                            self._map[p][-1]["is_capital"] = False 
                        orig_capital["is_capital"] = True 
                        print("Player {:d} restored {} as capital.".format(i, self.pname(self._original_capital[i])))
                # else do nothing
            
            #==========
            # Deployment-related 
            owned = [self._map[ip][-1] for ip in player_province]
            max_strength = sum((o["score"] for o in owned))
            current_strength = sum((o["units"] for o in owned))
            if current_strength > max_strength:
                # overstrength, disbanding random units across the owned province 
                disband = current_strength - max_strength
                for _ in range(disband):
                    # should only target provinces with more than one unit 
                    available = [p for p in owned if p["units"] > 1]
                    if len(available) == 0:
                        print("No disband-able region left; only disbanded upto {:d}".format(_))
                        break
                    # select a random one
                    random.choice(available)["units"] -= 1
                if len(available) > 0:
                    # recheck to make sure break had not been attempted. TODO shouldn't need this 
                    print("Disbanded {:d} units of Player {:d} randomly.".format(disband, i))
            elif current_strength < max_strength:
                # understrength, find an appropriate deployable region and throw them there
                reinforcement = max_strength - current_strength 
                target_id = self._player_bot[i].calculate_deployment(self._map, reinforcement)
#                target_id = random.choice(self.all_deployable_provinces())
                if target_id is not None:
                    self.perform_action_deploy(reinforcement, target_id, recheck=False)
                    print("Player {:d} received {:d} reinforcement at {}".format(i, reinforcement, self.pname(target_id)))
                else:
                    print("Player {:d} declined reinforcement.".format(i))
            # else ignore
            
            #==========
            # Encirclement related 
            for ip in player_province:
                if self._map[ip][-1]["is_capital"]:
                    # capital is exempted from this check 
                    continue
                immediate_border = self._map[bp][-1]["connection"]
                if all((self._map[bp][-1]["owner"] != i for bp in immediate_border)):
                    # encircled 
                    before = self._map[ip][-1]["units"]
                    self._map[ip][-1]["units"] = after = max(int(before // 2), 1)
                    print("Player {:d} is encircled at {}(border: {}); units halved {:d}->{:d}".format(i, self.pname(ip), immediate_border, before, after))


    def test_random_occupy(self, targetting_hostile: bool=False):
        # testing the perform_action_attack - each iteration, each player randomly target an empty bordered province & try occupying it with 10 units; repeat ad nauseam
        # testing the perform_action_movement - each iteration when cannot attack, move units from reserve (non-border) to front (border)
        print("Performing new occupying test, targetting hostile allowed: {} (currently not allowed)".format(targetting_hostile))
        for i in range(self._player_count):
            player_province = self.all_owned_provinces(i) # in id format 
            # knockout related
            if len(player_province) == 0:
                print("Player {:d} knocked out; movement skipped.".format(i))
                continue

            action = self._player_bot[i].calculate_movement(self._map, allowable_range=2)
            if action is None:
                print("Player {:d} do not move.".format(i))
            else:
                source_id, target_id, amount = action
                result, result_str = self.perform_action_movement(amount, source_id, target_id, allowable_range=2)
                if result:
                    print("Player {:d} moved {:d} units from {} to {}".format(i, amount, self.pname(source_id), self.pname(target_id)))
                else:
                    print("Player {:d} failed to move {:d} units from {} to {}, error: {}".format(i, amount, self.pname(source_id), self.pname(target_id), result_str))
            ## OCCUPY section 
#            if targetting_hostile:
#                targetable = {ip for ip in bordered if self._map[ip][-1]["owner"] != i}
#            else:
#                targetable = {ip for ip in bordered if self._map[ip][-1]["owner"] is None}
#            if len(targetable) == 0:
#                print("Player {:d} has no targetable border province (bordered {}). Ignoring.".format(i, bordered))
#                continue 
#            else:
#                target_id = random.choice(list(targetable))
        for i in range(self._player_count):
            player_province = self.all_owned_provinces(i) # in id format 
            # knockout related
            if len(player_province) == 0:
                print("Player {:d} knocked out; movement skipped.".format(i))
                continue
            action = self._player_bot[i].calculate_attacks(self._map)
            if action is not None:
                source_id, target_id, amount = action
                print("Player {:d} attacking {}(belong to {}) with {:d} units...".format(i, self.pname(target_id), self._map[target_id][-1]["owner"], amount))
                self._map[source_id][-1]["units"] -= amount # TODO incorporate into perform
                result, target, casualty = self.perform_action_attack(i, amount, target_id)
                if result:
                    print("Attack succeeded; player occupied {} with {:d} units, casualty {:d} units".format(self.pname(target_id), target["units"], casualty))
                else:
                    print("Attack failed; {:d} units remained in {:d}, {:d} units lost".format(target["units"], i, casualty))
            else:
                print("Player {:d} do not attack.".format(i))
