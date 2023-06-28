"""Code to assign a bunch of subregions to respective region
"""
import math, random 
from statistics import mean
from collections import defaultdict 
import numpy as np 
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
from scipy.cluster.vq import kmeans 

from typing import Optional, List, Tuple, Any, Union, Dict 

def sq_eu_d(a, b): # squared euclid distance between A and B; mostly used for comparing
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

def eu_d(a, b): # euclid distance between A and B 
    return math.sqrt(sq_eu_d(a, b))

def wcen(pointlist): # centered point of the region. rename it soon
    x, y = zip(*pointlist)
    return mean(x), mean(y)

def assign_subregions(keys: Dict[Tuple[str], int], subregions: List[Tuple[Tuple[float, float], List]], width: float, height: float, return_center: bool=False):
    """Assign {subregions} to {keys}; with first value of key denoting the joined region. 
    Return two list: 
        list of organized subregion, each section belong to a region, following the subregions format
        list of organized keys, each matching the following subregions"""
    # each categories hold how many subregions
    categories = defaultdict(int)
    for k in keys.keys():
        categories[k[0]] += 1
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


def border_based_merge(subregions: List[Tuple[Tuple[float, float], List]], regions: List[int]):
    """Merge basing on the border mechanism - perform merge & cuts in ways that allow the maximum amount of bordered subregions."""
    # establish bordering region 
    bordered = defaultdict(lambda: False)
    border_count = defaultdict(int)
    for i in range(len(subregions)-1):
        for j in range(i+1, len(subregions)):
            (_, sedge), (_, eedge) = subregions[i], subregions[j]
            # if +2 vertices shared; is two bordered regions 
            if len(set(sedge) & set(eedge)) > 2:
                bordered[(i, j)] = True 
                border_count[i] += 1
                border_count[j] += 1 
    # started merging. 
    current_regions = [(n, []) for n in regions]
    mergeable = True 
    ignore = {} # should not be used
    while mergeable:
        # select a subregion with the least bordered variants 
        # TODO choose on proximity to other regions as well
        target_idx, _ = min(border_count.items(), key=lambda it: it[1])
        # if has 
