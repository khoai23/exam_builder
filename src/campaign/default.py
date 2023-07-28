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
                distribution -= capital_point
                tiles = [t for t in tiles if t[-1] != capital]
            # for all applicable tiles, distribute point-by-point, favor higher. TODO better distribution
            points = [1] * len(tiles)
            ids = list(range(len(tiles)))
            while sum(points) < distribution:
                # TODO prevent lopsided point distribution; capital should be the highest one
                next_id = random.choices(ids, weights=points, k=1)[0]
                points[next_id] += 1
            # once fully distributed; set the tiles values & ownership
            for p, t in zip(points, tiles):
                t[-1]["score"] = p
                t[-1]["owner"] = None 
        # once all regions accounted for, flatten
        self._map = [subregion for region in regions.values() for subregion in region]
    
    def retrieve_draw_map(self, colorscheme=["green", "red", "blue", "yellow"], default="transparent"):
        # just use the current map for now 
        # appropriate fg/bg; TODO set this as class property 
        for srg in self._map:
            attr = srg[-1]
            attr["fg"] = colorscheme[attr["owner"]] if attr["owner"] is not None else default
            attr["bg"] = "black" if attr["owner"] else "white"
            attr["text"] = attr["score"] # display only score for now
        return self._map
