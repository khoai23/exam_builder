"""Appropriate form of the campaign game.
Each player have an amount of units to be distributed on all its controlled tiles. It also have a "capital", which is either its first starting tile, or the highest value tile the player still control
Each tile have a score, the sum of this score decide the amount of units each player has. If the number exceeded this sum, units are disbanded randomly. If the number is less, new units will spawn in any tile -3 away from nearest hostile tile.
For every turn, each player get to move a number of adjacent units against one external tile. If that exceeds the units presently on the tile, the tile is captured by half of the remaining attacking unit. If not, substract upto -1 of attacker units on both side.
Winning condition is achieved by having 75% of total tile points."""
import random

from src.map import generate_map_by_region, generate_map_by_subregion, format_arrow

class CampaignMap:
    """The map on which the game is played."""
    def __init__(self, player_count: int=4, region_count: int=9, subregion_count: int=6, capital_point: int=10, region_point=30):
        self._player_count = player_count
        # generate by region; this should help causing hubbed map 
        # TODO make varied subregions
        distribution = [dict(category=str(rg), tag=str(i)) for rg in range(region_count) for i in range(subregion_count)]
        regions = generate_map_by_subregion(distribution, bundled_by_category=True, do_recenter=True, do_shrink=0.98, return_connections=True)
        # with the map created, assign appropriate player capital & ensure each region have relatively same score 
        player_starter = random.sample(list(range(region_count)), player_count)
        for i, tiles in enumerate(regions.values()):
            distribution = region_point
            if i in player_starter:
                # apply the capital in a random province 
                capital = random.choice(tiles)[-1]
                capital["score"] = capital_point
                capital["owner"] = player_starter.index(i)
                capital["units"] = capital_point
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
            for p, t in zip(points, tiles):
                t[-1]["score"] = p
                t[-1]["owner"] = None
                t[-1]["units"] = p
        # once all regions accounted for, flatten
        self._map = [subregion for region in regions.values() for subregion in region]
        print("Created map with {} subregion".format(len(self._map)))
    
    def retrieve_draw_map(self, colorscheme=["green", "red", "blue", "yellow"], default="transparent"):
        # just use the current map for now 
        # appropriate fg/bg; TODO set this as class property 
        for srg in self._map:
            attr = srg[-1]
            attr["fg"] = colorscheme[attr["owner"]] if attr["owner"] is not None else default
            attr["bg"] = "black"
            attr["text"] = "{:d} ({:d} star)".format(attr["units"], attr["score"]) # display only score for now
        return self._map
        
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
        else:
            # more than acceptable; change ownership and put the remainder on the target 
            surplus = true_attack - target["units"]
            new_occupant_units = min(max(int(surplus / preserve_modifier), 1), attacking) # minimum 1 occupant, maximum the original attacking force
            target["owner"] = player_id
            target["units"] = new_occupant_units
        # TODO add log 
        return target
        
    def test_random_occupy(self):
        # testing the perform_action_attack - each iteration, each player randomly target an empty bordered province & try occupying it with 10 units; repeat ad nauseam
        print("Performing new occupying test")
        for i in range(self._player_count):
            player_province = set(ip for ip, p in enumerate(self._map) if p[-1]["owner"] == i) # in id format
            all_bordered = set((bp for ip in player_province for bp in self._map[ip][-1]["connection"]))
            bordered = all_bordered - player_province
            # print("player_province: {}, all bordered: {}; bordered: {}".format(player_province, all_bordered, bordered))
            unoccupied = {ip for ip in bordered if self._map[ip][-1]["owner"] is None}
            if len(unoccupied) == 0:
                print("Player {:d} has no unoccupied border province (bordered {}). Ignoring.".format(i, bordered))
                continue 
            target_id = random.choice(list(unoccupied))
            print("Attacking {:d} with fixed 10 units...".format(target_id))
            target_result = self.perform_action_attack(i, 10, target_id)
            if target_result["owner"] == i:
                print("Attack succeeded; Player {:d} occupied {:d} with {:d} units".format(i, target_id, target_result["units"]))
            else:
                print("Attack failed; {:d} units remained in {:d} ".format(target_result["units"], i))