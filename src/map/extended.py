"""Generating map with similar protocol to CK2 map - adding impassables (mountain ranges, inland/outland seas), obstructions (rivers, hills), and observables (cities/castles/towns/division location/trees)
Specific features related to each map would be updated when converting to appropriate forms."""
import random

from .default import generate_map_by_region

from typing import Optional, Dict, Tuple, Callable

import logging 
logger = logging.getLogger()

SEA_REGION, LAND_REGION = 0, 1

def check_neighbor(coord: Tuple[int, int], fn: Callable[Tuple[int, int], bool], any_or_all_mode=any) -> bool:
    x, y = coord
    neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
    return any_or_all_mode((fn(n) for n in neighbors))

def region_by_distance(full_map: Dict[Tuple[int, int], int], region_type: int=SEA_REGION, distance_region_type: int=LAND_REGION) -> iter:
    # create an incremental iterable and sort the regions accordingly
    compatible = {r for r, t in full_map.items() if t == region_type}
    # direct neighbor
    distance_one = {r for r in compatible if check_neighbor(r, lambda nb: full_map.get(nb, None) == distance_region_type) }
    remaining = compatible - distance_one
    # output as the iterable 
    for r in distance_one:
        yield (r, 1)
    current_distance = 1
    last_distance_regions = distance_one
    # update progressively until no remaining 
    while len(remaining) != 0:
        current_distance += 1
        current_distance_regions = {r for r in remaining if check_neighbor(r, lambda nb: nb in last_distance_regions)}
        for r in current_distance_regions:
            yield (r, current_distance)
        remaining = remaining - current_distance_regions
        last_distance_regions = current_distance_regions
#    raise StopIteration

def generate_map_landmass(map_size: Tuple[int, int], landmass_size: int, continent_count: int=2, island_ratio: float=0.1, box_size: int=16):
    """Generate a 'world map'.
    Step 1: generate raw regions by 'boxes' (to be updated later)
    Step 2: Assign landmass until reaching `landmass_size`; 
        Will first assign `continent_count` large blocs that took up landmass_size * (1 - island_ratio)
        Then assign random island with the rest 
        # TODO assigning large archipelago for better immersion?
    Step 3: TODO assigning randomized impassables
    Step 4: TODO assigning randomized obstructions & observables 

    Args:

    Results:
        A tuple of:
            land_region: centers of the region in the landmass 
            sea_region: center of regions in the seas/ocean
            TODO impassables/obstructions region
    """
    width, height = map_size
    full_map = {(i, j): SEA_REGION for i in range(0, width // box_size) for j in range(0, height // box_size)}
    # run the logic to generate the continents. Fix glaring issues later
    island_landmass = int(landmass_size * island_ratio)
    continent_landmass = landmass_size - island_landmass
    # assign 1st core of each continent; as far from each other as possible
    continent_size_count = [0] * continent_count
    continents = {i: set() for i in range(continent_count)}
    valid_neighbors = {i: set() for i in range(continent_count)}
    for ci in range(continent_count):
        # not actually randomized core yet 
        core_location_x = int( (width // box_size) // continent_count * (ci + 0.5) )
        core_location_y = random.randint(int(height // box_size * 0.1), int(height // box_size * 0.9))
        core = (core_location_x, core_location_y)
        continents[ci].add(core)
        continent_size_count[ci] += 1
        # adding in neighbors as well
        possible_neighbors = [(core_location_x-1, core_location_y), (core_location_x+1, core_location_y), (core_location_x, core_location_y-1), (core_location_x, core_location_y+1)]
        valid_neighbors[ci].update([n for n in possible_neighbors if n in full_map])
        full_map[core] = LAND_REGION 
    # from this point onward, keep assigning random point between each continent;
    # this doesn't guarantee independent continents, balancely distributed continents, or eliminating elongated exclaves. Yet
    while sum(continent_size_count) < continent_landmass:
        # still have landmass to distribute; select a random neighbors
        ci = random.choice(range(continent_count))
        add_region = x, y = random.choice(list(valid_neighbors[ci]))
        # set it as part of the continent
        continents[ci].add(add_region)
        continent_size_count[ci] += 1
        full_map[add_region] = LAND_REGION 
        # check and add possible sea neighbors; if they are 
        possible_neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
        valid_neighbors[ci].update([n for n in possible_neighbors if full_map.get(n, None) == SEA_REGION ])
        # costly - recheck the region to prevent continent joining.
        valid_neighbors[ci] = {n for n in valid_neighbors[ci] if full_map[n] == SEA_REGION}

    # island follow the same mechanism, except it has an disminishing chance of generating new islands
    # Can try exclude land bridges later.
    island_size_count = []
    islands = dict()
    valid_neighbors = dict()
    island_new_weight = 0
    while sum(island_size_count) < island_landmass:
        # still has landmass to distribute; depending on a weighted roll, either add to existing ones or create a new one 
        roll = random.randint(0, len(island_size_count) + island_new_weight)
        # print("Rolling choice:", roll, len(island_size_count))
        if roll < len(island_size_count):
            # if fall on an existing island; attempt to see if it can be expanded or not 
            if len(valid_neighbors[roll]) < 0:
                print("False hit: no valid neighbor for {} - current {}, neighbors {}".format(roll, islands[roll], valid_neighbors[roll]))
                continue # skip and retry 
            add_region = x, y = random.choice(list(valid_neighbors[roll]))
            islands[roll].add(add_region)
            island_size_count[roll] += 1
            full_map[add_region] = LAND_REGION
            possible_neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
            valid_neighbors[roll].update([n for n in possible_neighbors if full_map.get(n, None) == SEA_REGION and check_neighbor(n, lambda nb: full_map.get(nb, SEA_REGION) == SEA_REGION)])
        else:
            # if fall outside, generate a new island. Always try for the furthest sea region that can be found (costly, probably).
            #for region, region_type in full_map:
            #    if region_type != SEA_REGION:
            #        continue 
            region = distance = None
            for r, d in region_by_distance(full_map, SEA_REGION, LAND_REGION):
                region, distance = r, d
                # just run until (A) exhausted, or (B) hitting 50% chance with >10 away from shore
                if d > 10 and random.random() < (0.05*(d-10)) :
                    break 
            assert d > 1, "Should not create an island that directly stood on shore."
            x, y = region 
            new_island_index = len(island_size_count)
            islands[new_island_index] = {region}
            island_size_count.append(1)
            full_map[region] = LAND_REGION
            possible_neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
            valid_neighbors[new_island_index] = {n for n in possible_neighbors if full_map.get(n, None) == SEA_REGION}
    # for now print all what was created
    print("Continents: ", [len(c) for c in continents.values()])
    print("Islands:", [len(i) for i in islands.values()])
    return full_map

def merge_region(full_map: Dict[Tuple[int, int], int], expected_land_region: int, expected_sea_region: Optional[int]=None, expected_islands: Optional[int]=None, inland_sea_threshold: Optional[int]=3):
    """From the above 'world-map', attempt to merge into lower regions using some rules.
        Should try to prioritize merging upper ones into reflecting planet curvature
        Should try to merge sea zones to this level
    Args:
        expected_smth: expected region size or number of item. None means unchanged.
        inland_sea_threshold: if true, any inland sea that is smaller than this threshold is voided and turn into land.
    Return:
        The merged map in land/seas
        The region assignment matching the expected land/sea region
    """
    # trim off the inland seas first 
    sea_regions_by_shore_distance = dict()
    for sea_region, distance in region_by_distance(full_map, SEA_REGION, LAND_REGION):
        if distance > inland_sea_threshold:
            # no need to compute anywhere further than necessary 
            break 
        region_group = sea_regions_by_shore_distance[distance] = sea_regions_by_shore_distance.get(distance, set())
        region_group.add(sea_region)
    # after this we'll have a list of valid inland seas; work backward and eliminate any that does not connect to valid sections 
    if not sea_regions_by_shore_distance.get(inland_sea_threshold, None):
        # if no such distance is available, all inland seas are considered valid. Should not happen, but if does, this 
        logging.warning("No sea region reached distance >= {} from shore; all sea region will remain as-is".format(inland_sea_threshold))
    else:
        region_accepted, region_removed = set(sea_regions_by_shore_distance[inland_sea_threshold]), set()
        for d in range(inland_sea_threshold-1, 0, -1):
            # successively check for accepted parents; if not, prompt removal 
            for r in sea_regions_by_shore_distance[d]:
                if check_neighbor(r, lambda nb: nb in region_accepted, any_or_all_mode=any):
                    region_accepted.add(r)
                else:
                    region_removed.add(r)
        # after calculation; remove all the regions that are designated so by setting it to land 
        for r in region_removed:
            full_map[r] = LAND_REGION 
    # merging mechanism. Assign all regions with appropriate form; then attempt merging, prioritize (1) closer to top/bottom edge, (2) small, and (3) consistency (as big of a contact as possible)
    # tiered - do not attempt to merge lower level if upper ones are still at the same size
    tier_size = 4 * 2
    tier_span = ( max((y for (x, y), region_type in full_map.items())) + 1 ) // tier_size
    tier_range = [ti * tier_span for ti in range(tier_size)]
    tier_favoritism = [int(abs(4.5 - i) - 0.5) for i in range(tier_size)]
    sea_region_id, land_region_id = -1, 1
    regions = dict() # formatted as region_id: (tier, children, neighbors)
    regions_by_tier = {ti: set() for ti in range(tier_size)}
    current_land_region = current_sea_region = 0
    for r, region_type in full_map.items():
        # match the regions to itself 
        x, y = r
        possible_neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
        regions[r] = (set(), set(nb for nb in possible_neighbors if nb in full_map))
        regions[r][0].add(r) # if can confirm {r} will not unload the properties, that would be better
        # check backward - if higher to the lower bound of a region, assign to that region. Should never fail
        region_tier = next( (ti for ti in range(tier_size-1, 0, -1) if y >= tier_range[ti]) )
        regions_by_tier[region_tier].add(r)
    # for now doing manual merging. TODO optimize?
    while current_land_region > expected_land_region:
        # priortize as stated above 
        score, selected_region = min(( (-tier_favoritism[t] + len(regions[r][0]), r) for t, trs in regions_by_tier.items() for r in trs))
        current_region, neighbors = regions[r]
        # choose a neighbor to absorb; choose smaller partner which should have as few different neighbors to the original region as possible
        

    return full_map   

if __name__ == "__main__":
    import cv2, numpy
    logging.basicConfig(level=logging.DEBUG)
    size = [1024, 1024]
    full_map = generate_map_landmass(size, 1600, continent_count=2, island_ratio=0.1, box_size=16) 
    full_map = merge_region(full_map, expected_land_region=800, expected_sea_region=256, expected_islands=8, inland_sea_threshold=3)
    img_size = size + [1]
    img = numpy.zeros(img_size)
    for (x, y), region_type in full_map.items():
        if region_type == LAND_REGION:
            # the relevant square will be white instead 
            for sqw in range(16):
                for sqh in range(16):
                    img[x*16+sqw][y*16+sqh][0] = 255.0
    cv2.imshow("image", img)
    cv2.waitKey(0)
