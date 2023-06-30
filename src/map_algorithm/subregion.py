"""Code to assign a bunch of subregions to respective region
"""
import math, random 
from statistics import mean
from collections import defaultdict 
import numpy as np 
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
from scipy.cluster.vq import kmeans 

from typing import Optional, List, Tuple, Any, Union, Dict, Set

def sq_eu_d(a, b): # squared euclid distance between A and B; mostly used for comparing
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

def eu_d(a, b): # euclid distance between A and B 
    return math.sqrt(sq_eu_d(a, b))

def tr_area(a, b, c): # area of triangle by point coordinate
    return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[1]*(a[1]-b[1]))

def ply_area(*points): # area of polygon by point coordinate; split into sum of children triangle 
    assert len(points) > 2, "must have more than 2 points for a valid polygon"
    return sum((tr_area(points[0], points[i], points[i+1]) for i in range(1, len(points)-1)))

def wcen(pointlist): # centered point of the region. rename it soon
    x, y = zip(*pointlist)
    return mean(x), mean(y)

def has_border(region1, region2): # if two regions has at least one shared border (2 shared vertices), return true 
#    print(set([tuple(e) for e in sedge]))
#    print(set([tuple(e) for e in eedge]))
    # if +2 vertices shared; is two bordered regions 
    return len(set([tuple(e) for e in region1]) & set([tuple(e) for e in region2])) >= 2

def assign_subregions(keys: Dict[Tuple[str], int], subregions: List[Tuple[Tuple[float, float], List]], width: float, height: float, assign_mode: str="kmean", return_center: bool=False):
    """Assign {subregions} to {keys}; with first value of key denoting the joined region. 
    Return two list: 
        list of organized subregion, each section belong to a region, following the subregions format
        list of organized keys, each matching the following subregions"""
    # each categories hold how many subregions
    categories = defaultdict(int)
    for k in keys.keys():
        categories[k[0]] += 1
    if(assign_mode == "kmean"):
        regions = kmean_merge(subregions, categories)
    elif(assign_mode == "border"):
        regions = border_based_merge(subregions, categories)
    else:
        raise NotImplementedError("Invalid assign_mode: {}".format(assign_mode))
    # after all points had been assigned, return the organized list 
    result_subregions, result_tags = [], []
    for cat, (center, _, ids) in regions.items():
        tags = [t for t in keys.keys() if t[0] == cat]
        # print(len(tags), len(ids))
        for t, i in zip(tags, ids):
            # assign each region to each tag 
            result_subregions.append(subregions[i])
            result_tags.append(t) 
    if(return_center):
        return result_subregions, result_tags, {cat: center for cat, (center, _, _) in regions.items()}
    else:
        return result_subregions, result_tags

def kmean_merge(subregions: List[Tuple[Tuple[float, float], List]], categories: Dict[Any, int]):
    """Merge by using kmean to select region core, and select other points using it.
    Not very reliable as kmean tend to land on single points in sparse data"""
    # use kmeans to select core cluster point 
    points = [p for p, _ in subregions]
    centers, minvar = kmeans(points, len(categories), iter=5)
    # assign points by distance preference 
    # the further a point is from all centroids, the more it should be prefered
    points.sort(key=lambda p: sum((eu_d(p, c) for c in centers)), reverse=True)
    # the closer a point to a centroid relative to the next one, the more it should be prefered 
    def cmpdist(p):
        dists = sorted((eu_d(p, c) for c in centers))
        return dists[1] - dists[0]
    #points.sort(key=cmpdist, reverse=True)
    regions = {cat: (center, num, []) for center, (cat, num) in zip(centers, categories.items())}
    for p in points:
        # select all assignable centers
        usable = [item for item in regions.items() if item[1][1] > 0]
        # select the closest one 
        cat, (center, num, pids) = min(usable, key=lambda it: sq_eu_d(it[1][0], p))
        # write in and update the assigned_category
        # pid = points.index(p)
        pids.append(points.index(p))
        regions[cat] = (center, num-1, pids)
    return regions

def border_loss(target_idx: int, recv_idx: int, bordered: Set[Tuple[int, int]], border_count: Dict[int, int]):
    """Check upon {target_idx} being absorbed to {recv_idx}, lose how many border unit."""
    count = 0
    for index in border_count:
        if index == target_idx or index == recv_idx:
            continue # not related 
        # for a neutral field; check if it is bordering both the target and recv. If yes, lose 1
        if (target_idx, index) in bordered or (index, target_idx) in bordered:
            if (recv_idx, index) in bordered or (index, recv_idx) in bordered:
                count += 1
    return count

def border_based_merge(subregions: List[Tuple[Tuple[float, float], List]], categories: Dict[Any, int], subregion_based: bool=True):
    """Merge basing on the border mechanism - perform merge & cuts in ways that allow the maximum amount of bordered subregions."""
    # establish bordering region 
    bordered = set()
    border_count = defaultdict(int)
    for i in range(len(subregions)-1):
        for j in range(i+1, len(subregions)):
            # if +2 vertices shared; is two bordered regions 
            if has_border(subregions[i][1], subregions[j][1]):
                bordered.add( (i, j) )
                border_count[i] += 1
                border_count[j] += 1 
    print(bordered)
    # started merging. 
    current_regions = [(n, [], None, cat) for cat, n in categories.items()]
    mergeable = True 
    ignore = set() # used when kicking out first regions
    while mergeable:
        # check bordered or empty region, need more first 
        receiver = num, reg, recv_idx, cat = max(current_regions, key=lambda it: it[0])
        region_idx = current_regions.index(receiver)
#        target_idx, _ = min(border_count.items(), key=lambda it: it[1])
        if(num == 0):
            # all regions are satisfied; break 
            mergeable = False 
            break
        elif(len(receiver[1]) == 0):
            # if receiver region is empty, just push in a random smallest one 
            smallest = min(c for i, c in border_count.items() if i not in ignore)
            # select subregions with the least border
            possible_targets = [target_idx for target_idx, value in border_count.items() if value == smallest and target_idx not in ignore]
            # also prefer one that doesn't border existing core; if not found any, revert to possible_targets
            preferred_targets = [i for i in possible_targets if not any( (i, ri) in bordered or (ri, i) in bordered for ri in ignore)]
            if(len(preferred_targets) > 0):
                target_idx = random.choice(preferred_targets)
            else:
                target_idx = random.choice(possible_targets)
            # once pushed, the region will use the target_idx's values from this point onward
            reg.append(target_idx)
            current_regions[region_idx] = (num-1, reg, target_idx, cat)
            ignore.add(target_idx)
            # first subregion will be called "core" internally
            print("Assigning region {} with first subregion {}({})".format(cat, target_idx, subregions[target_idx]))
        elif(subregion_based):
            # basing on the subregion, best region bordering ANY current region first
            applicable = [(i, c) for i, c in border_count.items() if i not in ignore and  # not IS a core region 
                any( ((i, ri) in bordered or (ri, i) in bordered for ri in ignore)) ] # has a border with a core 
            # checking for smallest counts (c)
            for target_idx, c in sorted(applicable, key=lambda it: it[1]):
                used = False 
                for region_idx, receiver in enumerate(current_regions):
                    num, reg, recv_idx, cat = receiver
                    if(((target_idx, recv_idx) in bordered or (recv_idx, target_idx) in bordered) and num > 0):
                        # valid, allow input 
                        reg.append(target_idx)
                        current_regions[region_idx] = (num-1, reg, recv_idx, cat)
                        # set used and breakout
                        used = True 
                        break
                if(used):
                    break 
            if(not used):
                # something is seriously wrong, no applicable border point 
                print("Cores:", ignore)
                print("Applicable:", applicable)
                print("Border", bordered)
                print("Exit prematurely. FIX")
                raise ValueError("Generation failed; try again or quit")
            print(applicable)
            print("Assigning region {} with bordered subregion {}({})".format(cat, target_idx, subregions[target_idx]))
            # if all region requested zero, break here 
            if(all((r[0] == 0 for r in current_regions))):
                break
            # merge the target_idx with the recv_idx & recalculate the border count 
            bordered_unordered = ((p1, p2) if p1 != target_idx and p2 != target_idx \
                    else (p1, recv_idx) if p2 == target_idx \
                    else (p2, recv_idx) \
                    for p1, p2 in bordered)
            bordered = {(p1, p2) if p1 < p2 else (p2, p1) for p1, p2 in bordered_unordered if p1 != p2}
            new_border_count = defaultdict(int)
            for p1, p2 in bordered:
                # bordered will get half the value when bordering a core region
                new_border_count[p1] += (1 if p2 not in ignore else 0.5)
                new_border_count[p2] += 1
            assert len(border_count) > len(new_border_count), "Should have eliminated an index {} and reduced border count by one; yet still is {} -> {}".format(target_idx, border_count, new_border_count)
            border_count = new_border_count
        else:
            # basing on the region, needed most first
            # if receiver region is not empty, first choose the one bordering the receiver 
            possible_targets = [target_idx for target_idx in border_count if ((target_idx, recv_idx) in bordered or (recv_idx, target_idx) in bordered) and target_idx not in ignore]
            if(len(possible_targets) == 0):
                print("Exit prematurely. FIX")
                raise ValueError("Generation failed; try again or quit")
            # choose the region that mimimizes border loss
#            target_idx = min(possible_targets, key=lambda t: border_loss(t, recv_idx, bordered, border_count))
            loss = sorted(possible_targets, key=lambda t: border_loss(t, recv_idx, bordered, border_count))
            print("Loss:", [(l, border_loss(l, recv_idx, bordered, border_count)) for l in loss])
            target_idx = loss[0]

            reg.append(target_idx)
            current_regions[region_idx] = (num-1, reg, recv_idx, cat)
            print("Assigning region {} with bordered subregion {}({})".format(cat, target_idx, subregions[target_idx]))
            # if all region requested zero, break here 
            if(all((r[0] == 0 for r in current_regions))):
                break
            # merge the target_idx with the recv_idx & recalculate the border count 
            bordered_unordered = ((p1, p2) if p1 != target_idx and p2 != target_idx \
                    else (p1, recv_idx) if p2 == target_idx \
                    else (p2, recv_idx) \
                    for p1, p2 in bordered)
            bordered = {(p1, p2) if p1 < p2 else (p2, p1) for p1, p2 in bordered_unordered if p1 != p2}
            new_border_count = defaultdict(int)
            for p1, p2 in bordered:
                # bordered will get half the value when bordering a core region
                new_border_count[p1] += (1 if p2 not in ignore else 0.5)
                new_border_count[p2] += 1
            assert len(border_count) > len(new_border_count), "Should have eliminated an index {} and reduced border count by one; yet still is {} -> {}".format(target_idx, border_count, new_border_count)
            border_count = new_border_count
        # print for debug 
        print(bordered)
    # once out of the loops, all regions should have been accounted for.
    return {cat: (None, None, reg) for (num, reg, recv_idx, cat) in current_regions}
