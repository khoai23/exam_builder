"""Code to draw the regions around a list of center points"""
import math, random 
import numpy as np
from scipy.spatial import Voronoi 

from src.map_algorithm.subregion import sq_eu_d

from typing import Optional, List, Tuple, Any, Union, Dict 

def create_voronoi(center_points: List[Tuple[float, float]], width: float, height: float, return_obj: bool=False):
    # just use scipy 
    distant_points = [(width*2*ix, height*2*iy) for ix, iy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]]
    np_points = np.array(center_points + distant_points)
    vor = Voronoi(np_points)
    # print(vor.vertices, vor.regions, vor.ridge_vertices, vor.ridge_points)
    vertices = vor.vertices 
    regions = [(p, vor.regions[vor.point_region[i]]) for i, p in enumerate(center_points)]
    polygons = list() # [None] * len(center_points)
    for point, region in regions:
#        if(-1 in region or len(region) == 0):
#            # is an external/unused region; check and verify
#            print("Region had external edge; to be discarded: {} for {}".format(region, point))
#            continue 
#        index = center_points.index(point)
#        if(index == -1):
#            print("Cannot find index of point {}; using nearest.")
#            index = min((i for i in range(len(center_points))), key=lambda idx: sq_eu_d(center_points[idx], point))
        polygon = [vertices[i] for i in region if i >= 0]
        # format in the non-restricted form 
#        polygons[index] = (point, polygon) 
        polygons.append( (point, polygon) )
#    assert None in polygons, "Missing points detected. list: {}".format(polygons)
    if(return_obj):
        return vor 
    else:
        return polygons

def create_voronoi_deprecated(center_points: List[Tuple[float, float]], weights: List[float], width: float, height: float):
    # attempt to create a voronoi from the center points.
    for point in center_points:
        # for each point, designated the default region as the entirety of the board 
        edges = {(0, 0, width, 0), (0, 0, 0, height), (width, 0, width, height), (0, height, width, height)}
        for other in center_points:
            if(other == point):
                # is self; ignore 
                continue 
            # is not self, create the perpendicular bisector and cut it with all edges 


