"""Appropriate form of the campaign game.
Each player have an amount of units to be distributed on all its controlled tiles. It also have a "capital", which is either its first starting tile, or the highest value tile the player still control
Each tile have a score, the sum of this score decide the amount of units each player has. If the number exceeded this sum, units are disbanded randomly. If the number is less, new units will spawn in any tile -3 away from nearest hostile tile.
For every turn, each player get to move a number of adjacent units against one external tile. If that exceeds the units presently on the tile, the tile is captured by half of the remaining attacking unit. If not, substract upto -1 of attacker units on both side.
Winning condition is achieved by having 75% of total tile points."""
import random

from src.campaign.bot import Bot, RandomBot, LandGrabBot, FrontlineBot
from src.campaign.name import NameGenerator, NAME_GENERATOR_BY_CUE
from src.map import generate_map_by_region, generate_map_by_subregion, format_arrow

from typing import Optional, List, Tuple, Any, Union, Dict 

class CampaignMap:
    """The map on which the game is played. Support:
        Region names: regions can be named by a NameGenerator if available. If not, use simple index as name
        Bot: autonomous unit that take control of the player units. 
        Arrows: Performed actions will receive corresponding arrows, depending on the display mode, these arrows will be shown on the map"""
    def __init__(self, player_count: int=4, region_count: int=9, subregion_count: int=6, capital_point: int=10, region_point=30, 
            bot_class: Bot=RandomBot, name_generator: Optional[NameGenerator]=None,
            attack_per_turn: int=1, movement_per_turn: int=2, deployment_province_count: int=2):
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
        # use for player_alive's cache 
        self._dead = set()
        # use for arrow caches 
        self._arrows = {i: list() for i in range(self._player_count)}
        # additinal setting 
        self._setting = dict(colorscheme=["yellowgreen", "salmon", "powderblue", "moccasin"], attack_per_turn=attack_per_turn, movement_per_turn=movement_per_turn, deployment_province_count=deployment_province_count, maximum_deployment=20, minimum_strength=10)
        self._action_order = list(range(self._player_count))
        self._update_action_order()
        self._context = {
            "casualties": {i: 0 for i in range(self._player_count)},
            "province_seized": {i: 1 for i in range(self._player_count)},
            "greatest_army_size": {i: 10 for i in range(self._player_count)},
            "greatest_occupied": {i: 1 for i in range(self._player_count)},
            "turn": 1
        } # for displaying, allow rules to affect things, and bot to properly calculate necessary actions
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

    def retrieve_player_color(self):
        return self._setting["colorscheme"]

    def retrieve_draw_map(self, colorscheme: List[str]=None, default="transparent"):
        colorscheme = colorscheme or self._setting["colorscheme"]
        # just use the current map for now 
        # appropriate fg/bg; TODO set bg in accordance with the amount of available units, or maybe transparency?
        for i, srg in enumerate(self._map):
            attr = srg[-1]
            attr["fg"] = colorscheme[attr["owner"]] if attr["owner"] is not None else default
            attr["bg"] = "black"
            if attr["is_capital"]:
                attr["symbol"] = "\u272A"
            else:
                attr.pop("symbol", None)
            attr["name"] = attr.get("province_name", str(i))
            attr["text"] = "{:d} ({:d}\u2605)".format(attr["units"], attr["score"]) # display only score for now
        return self._map
     
    def retrieve_draw_arrows(self, colorscheme: List[str]=None, default="black"):
        colorscheme = colorscheme or self._setting["colorscheme"]
        # load the arrows in appropriate format
        all_arrows = []
        for player_id, player_arrows in self._arrows.items():
            for (action_type, source_id, target_id, amount) in player_arrows:
                # convert accordingly from center to points 
                # print("Map index:", self._map[source_id], self._map[target_id])
                base_sx, base_sy, _, _, _, source = self._map[source_id]
                raw_sx, raw_sy = source["center"]
                source_coord = (base_sx + raw_sx, base_sy + raw_sy)
                base_tx, base_ty, _, _, _, target = self._map[target_id]
                raw_tx, raw_ty = target["center"]
                target_coord = (base_tx + raw_tx, base_ty + raw_ty)
                # TODO limiting the associating regions within coordinates
                # if delta of source -> target close to vertical (deltax / deltay < 10), use straight arrow; if not, use bevel
                offset = (0, -0.5)
                if abs(target_coord[0] - source_coord[0]) * 10 < abs(target_coord[1] - source_coord[1]):
                    offset = None 
                # scale the thickness according to the amount moved 
                thickness = max(min(int(amount / 4), 14), 2) # limit in 2-14 range 
                # rescale accordingly
                bound, arrow_dict = format_arrow((source_coord, target_coord), thickness=thickness, color=default, control_offset=offset, offset_in_ratio_mode=True, create_bound=True)
                # add a dashing format for movement 
                if action_type == "move":
                    arrow_dict["dash"] = 5
                # append; bound should be flattened as it control the rect
                all_arrows.append( (*bound, arrow_dict) )
        return all_arrows

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

    def perform_action_draw(self, source_ids: List[int], draw_amount: List[int], target_id: int, strict: bool=True):
        # attempt to draw units from specified tiles; return True if the drawing process worked 
        sources = [self._map[i][-1] for i in source_ids]
        if strict:
            assert len(sources) > 0
            assert all((s["owner"] == sources[0]["owner"] for s in sources))
            assert all((target_id in s["connection"] for s in sources))
            assert len(sources) == len(draw_amount)
        # zip, check 
        can_draw = all((s["units"] > d for s, d in zip(sources, draw_amount)))
        if can_draw:
            # check passed; performing the draw attempt
            for s, d in zip(sources, draw_amount):
                s["units"] -= d
        return can_draw

    def perform_action_attack(self, player_id: int, attacking: int, target_id: int, attack_modifier: float=1.0, defend_modifier: float=1.0, preserve_modifier: float=2.0):
        # perform an attack from a player, with up to {attacking} units, to target province
        # allow a "crit" modifier for later upgrade, and a "preserve" ratio which affect the amount of units kept after winning
        # all attacking units should have been consumed
        target = self._map[target_id][-1]
        assert target["owner"] is None or player_id != target["owner"], "Cannot attack same player province {}({})".format(target_id, player_id)
        true_attack = attacking * attack_modifier # multiply by modifier, round 
        true_defense = target["units"] * defend_modifier
        if true_defense > true_attack:
            # less than acceptable; subtract from defender 
            target["units"] -= int(true_attack / defend_modifier)
            return False, target, int(attacking)
        else:
            # more than acceptable; change ownership and put the remainder on the target 
            surplus = true_attack - true_defense
            new_occupant_units = min(max(int(surplus / preserve_modifier), 1), attacking) # minimum 1 occupant, maximum the original attacking force 
            losses = max(attacking - new_occupant_units, 0)
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
            return 0, "can only move in friendly provinces"
        if source["units"] < move + 1:
            return 0, "not enough units to move"
        if target_id not in self.check_range(source_id, allowable_range, owner=source["owner"]):
            return 0, "{} not in {} range of {}".format(target_id, allowable_range, source_id)
        # everything is ok, performing movement 
        # TODO put into queue, allow multiple movement submission for a phase
        source["units"] -= move 
        target["units"] += move  
        return move, None


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
            return (deploy, target)
        else:
            return (0, target)

    #=====================
    # Bot-compatible functions.
    def all_owned_provinces(self, player_id: int) -> set:
        return set(ip for ip, p in enumerate(self._map) if p[-1]["owner"] == player_id)

    def _update_context(self):
        provs = {pid: self.all_owned_provinces(pid) for pid in range(self._player_count)}
        self._context["total_owned"] = {pid: len(powned) for pid, powned in provs.items()}
        self._context["total_score"] = {pid: sum((self._map[p][-1]["score"] for p in powned)) for pid, powned in provs.items()} 
        self._context["biggest_player"] = self.biggest_player(use_cache=False)
        self._context["smallest_player"] = self.smallest_player(use_cache=False)
        # update statistics as well
        self._context["greatest_occupied"] = {pid: max(self._context["greatest_occupied"][pid], self._context["total_owned"][pid]) for pid in range(self._player_count)}

    def biggest_player(self, use_cache: bool=True):
        if use_cache:
            return self._context["biggest_player"]
        return max((pid for pid in range(self._player_count) if pid not in self._dead), key=lambda i: (self._context["total_owned"][i], self._context["total_score"][i])) 

    def smallest_player(self, use_cache: bool=True):
        if use_cache:
            return self._context["smallest_player"]
        return min((pid for pid in range(self._player_count) if pid not in self._dead), key=lambda i: (self._context["total_owned"][i], self._context["total_score"][i])) 

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

    def player_alive(self, plid: int, use_cache: bool=True) -> bool:
        """If use_cache, check from set; if not check directly"""
        if use_cache: # use cache
            alive = plid not in self._dead
        else: # not using cache; check directly
            alive = not len(self.all_owned_provinces(plid)) == 0
            if not alive:
                self._dead.add(plid)
        return alive

    #=====================
    # Phasing function 
    def phase_set_capital(self, player_id: int, player_province: set):
        # check for original capital 
        orig_capital = self._map[self._original_capital[player_id]][-1]
        if self.capital(player_id) is None:
            # no capital; check if there is a 
#            if orig_capital["owner"] != player_id:
            # no new capital yet, create one 
            new_capital = max(player_province, key=lambda ip: self._map[ip][-1]["score"])
            self._map[new_capital][-1]["is_capital"] = True
            # announce
            print("New capital for Player {:d} is set at {}".format(player_id, self.pname(new_capital)))
        elif orig_capital["owner"] == player_id and not orig_capital["is_capital"]:
            # do own the original capital, but is not the current capital, check if there is any foreign direct-border region 
            bordered_foreign = any( (self._map[p][-1]["owner"] != player_id for p in self._map[self._original_capital[player_id]][-1]["connection"]) ) 
            if not bordered_foreign:
                # safe, move back 
                for p in player_province:
                    self._map[p][-1]["is_capital"] = False 
                orig_capital["is_capital"] = True 
                print("Player {:d} restored {} as capital.".format(player_id, self.pname(self._original_capital[player_id])))
            # else do nothing
        # else has new capital; ignore
        assert self.capital(player_id) is not None, "Capital for Player {:d} must have been set after this".format(player_id)

    def phase_deploy_reinforcement(self, player_id: int, player_province: set, reinforcement_coef: float=0.5, disbanding_coef: float=0.25):
        # Deployment-related (deploying & disbanding)
        owned = [self._map[ip][-1] for ip in player_province]
        max_strength = max( sum((o["score"] for o in owned)), self._setting["minimum_strength"] ) # max_strength is always at least `minimum_strength`; to allow 1pm to recover
        current_strength = sum((o["units"] for o in owned))
        if current_strength > max_strength:
            # overstrength, disbanding random units across the owned province 
            disband = max(int( (current_strength - max_strength) * disbanding_coef ), 1) # always disband at least 1
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
                print("[P{:d}] {:d} unit randomly disbanded.".format(player_id, disband))
        elif current_strength < max_strength:
            # understrength, find an appropriate deployable region and throw them there
            # default upper limit is 20; limit-by-province owned would cause a death spiral
            upper_limit = self._setting["maximum_deployment"]  # 
            reinforcement = min(max(int( (max_strength - current_strength) * reinforcement_coef ), 1), upper_limit)
            target_id = self._player_bot[player_id].calculate_deployment(self._map, reinforcement)
#            target_id = random.choice(self.all_deployable_provinces())
            if target_id is not None:
                deployed, target = self.perform_action_deploy(reinforcement, target_id, recheck=False)
                print("[P{:d}] {:d} units deployed at {}".format(player_id, deployed, self.pname(target_id)))
                self._context["greatest_army_size"][player_id] = max(self._context["greatest_army_size"][player_id], current_strength+deployed)
            else:
                print("[P{:d}] reinforcement declined.".format(player_id))
        # else ignore

    def phase_check_encirclement(self, player_id: int, player_province: set, deserter_coef: float=0.5):
        # TODO set coefficient to count this type of casualty too, since it might be better
        for ip in player_province:
            if self._map[ip][-1]["is_capital"]:
                # capital is exempted from this check 
                continue
            immediate_border = self._map[ip][-1]["connection"]
            if all((self._map[bp][-1]["owner"] != player_id for bp in immediate_border)):
                # encircled 
                before = self._map[ip][-1]["units"]
                self._map[ip][-1]["units"] = after = max(int(before * deserter_coef), 1)
                print("Player {:d} is encircled at {}(border: {}); units deserted {:d}->{:d}".format(player_id, self.pname(ip), immediate_border, before, after))
                self._context["casualties"][player_id] += max(before - after, 0)

    def phase_perform_movement(self, player_id: int, override_action: Optional[list]=None):
        # Reinforcement distribution related. 
        # override_action is a backup option to allow manual action to replace it 
        action = override_action if override_action is not None else self._player_bot[player_id].calculate_movement(self._map, allowable_range=2)
        # if None and/or blank list, is not performing anything
        if not action:
            print("[P{:d}] Move declined.".format(player_id))
        else:
            if isinstance(action, tuple) and len(action) == 3 and isinstance(action[0], int):
                # old bot, outputting only a single movement 
                action = [action]
            for source_id, target_id, amount in action:
                result, result_str = self.perform_action_movement(amount, source_id, target_id, allowable_range=2)
                self._arrows[player_id].append( ("move", source_id, target_id, amount) )
                if result:
                    print("[P{:d}] Moved {}--{:d}->{}".format(player_id, self.pname(source_id), result, self.pname(target_id)))
                else:
                    print("Player {:d} failed to move {:d} units from {} to {}, error: {}".format(player_id, amount, self.pname(source_id), self.pname(target_id), result_str))

    def phase_perform_attack(self, player_id: int, override_action: Optional[list]=None):
        # Attack related 
        # also have override_action
        action = override_action if override_action is not None else self._player_bot[player_id].calculate_attacks(self._map)
        if isinstance(action, list) and len(action) > 0 and isinstance(action[0], tuple):
            # do nothing 
            pass 
        elif action: # dont accept either None or empty list 
            # if single action, set to a list and perform accordingly 
            action = [action]
            print("Single action attack detected (likely old bot); converting to list.")
        else:
            # no action, do nothing
            print("[P{:d}] Attack declined.".format(player_id))
            return 
        # reach here means have valid attacks to run
        # list of attacks, MUST have the same target id or is discarded 
        source_ids, target_ids, draw_amount = [list(it) for it in zip(*action)] 
        target_ids = set(target_ids)
        if len(target_ids) == 1:
            # valid target, attempt to perform draw 
            target_id = list(target_ids)[0]
            target_owner = self._map[target_id][-1]["owner"]
            print("[P{:d}] Attacking --{:d}--> {} ({})".format(player_id, sum(draw_amount), self.pname(target_id), "P{:d}".format(target_owner) if target_owner is not None else "unowned"))
            can_draw = self.perform_action_draw(source_ids, draw_amount, target_id)
            if can_draw:
                # valid and drawn the necessary force 
                amount = sum(draw_amount)
                result, target, casualty = self.perform_action_attack(player_id, amount, target_id)
                for source_id, draw in zip(source_ids, draw_amount):
                    self._arrows[player_id].append( ("attack", source_id, target_id, draw) )
                if result:
                    print("Attack succeeded; player occupied {} with {:d} units, casualty {:d} units".format(self.pname(target_id), target["units"], casualty))
                    self._context["province_seized"][player_id] += 1
                else:
                    print("Attack failed; {:d} units remained in {:d}, {:d} units lost".format(target["units"], player_id, casualty))
                self._context["casualties"][player_id] += max(casualty, 0)
            else:
                print("Submitted attacks cannot gain enough force; requested: {}".format({self.pname(player_id): a for player_id, a in zip(source_ids, draw_amount)}))
        else:
            print("Player {:d} submitted multiple attacks targets: {}({}). Ignoring.".format(player_id, target_ids, action))

    #=========
    # Phase functions. Use full_phase shorthand as it will
    def full_phase_deploy(self):
        for i in self._action_order:
            player_province = self.all_owned_provinces(i) # in id format 
            #==========
            # knockout related - check if player is alive here, use this cached value on subsequent phases
            if not self.player_alive(i, use_cache=False):
                continue
            # run appropriate phasing function
            self.phase_set_capital(i, player_province)
            self.phase_deploy_reinforcement(i, player_province)
            self.phase_check_encirclement(i, player_province)

    def full_phase_move(self):
        for i in self._action_order:
            # knockout related
            if not self.player_alive(i, use_cache=False):
                continue 
            self.phase_perform_movement(i)

    def full_phase_attack(self):
        for i in self._action_order:
            # knockout related
            if not self.player_alive(i, use_cache=False):
                continue
            self.phase_perform_attack(i)

    def _update_action_order(self):
        """Update the order of action for each player. This should at leasts alleviate some stalemate.
        TODO orders need to be submitted simultaneously."""
        random.shuffle(self._action_order)

    def end_turn(self):
        # clean up all cached data each turn 
        for arrows in self._arrows.values():
            arrows.clear()
        # TODO perform winning condition check 
        # additionally, calculate the biggest player value for this phase
        self._update_context()
        print("Biggest player: {}; Smallest player {};\nFull context: {}".format(self.biggest_player(), self.smallest_player(), self._context))
        self._update_action_order()
        self._context["turn"] += 1


class PlayerCampaignMap(CampaignMap):
    """Version of campaign map that support player actions instead of bots. The bot can still be used for suggestion and/or substitution.
    """
    def __init__(self, *args, players: List[int], **kwargs):
        super(PlayerCampaignMap, self).__init__(*args, **kwargs)
        self._is_players = set(players)
        self._action_dict = {}
        self._current_phase = "deploy"

    @property
    def current_phase(self):
        return self._current_phase 

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
            override_action = self._action_dict.get( (player_id, "attack"), [] )
        return super(PlayerCampaignMap, self).phase_perform_attack(player_id, override_action=override_action)

    def phase_perform_movement(self, player_id: int, override_action: Optional[list]=None):
        # override the action, if exist then use itself, if not use empty list to disable bot action 
        # If need to let bots take over, the dict value must be written with None
        if player_id in self._is_players:
            override_action = self._action_dict.get( (player_id, "move"), [] )
        return super(PlayerCampaignMap, self).phase_perform_movement(player_id, override_action=override_action)

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
        return super(PlayerCampaignMap, self).full_phase_deploy()

    def full_phase_move(self):
        # next phase is attack 
        self._current_phase = "attack"
        return super(PlayerCampaignMap, self).full_phase_move()

    def full_phase_attack(self):
        # next phase is end; this should trigger the next button on the site
        self._current_phase = "end"
        return super(PlayerCampaignMap, self).full_phase_attack()

    def retrieve_all_deployment(self, player_id: int):
        # retrieve all possible deploy point for the player 
        return self.all_deployable_provinces(player_id)

    def end_turn(self):
        # also wipe the action dict 
        self._action_dict.clear() 
        # next phase
        self._current_phase = "deploy"
        return super(PlayerCampaignMap, self).end_turn()
