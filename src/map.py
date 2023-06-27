"""Here to create and draw corresponding maps for each region (category) of the whole database.
TODO: 
    - Each tag with specific amount of count drawn for each sub-region 
    - Drawable arrows between regions
    - Trigger a link when an arrow is clicked
    - Upon finishing a test, colorized sub-region to indicate progress
"""
import math
from typing import Optional, List, Tuple, Any, Union, Dict
from scipy.spatial import Voronoi
import numpy as np

import logging 
logger = logging.getLogger()

DEFAULT_COLOR = ["green", "blue", "red", "purple", "orange", "yellow"]
def generate_map(data: List[Dict], width: float=1000, height: float=1000):
    """Generate a region map from list of current data."""
    center_x, center_y = width / 2, height / 2
    radius = min(width, height) / 2 * 0.75
    # for each region, generate appropriate center point {radius} away from center 
    categories = set((d.get("category", "N/A") for d in data))
    catpoints = [(center_x + radius * math.sin(360 / len(categories) * i), center_y + radius * math.cos(360 / len(categories) * i)) for i in range(len(categories))]
    # apply voronoi to draw the polygons and 
    polygons_with_points = create_voronoi(catpoints, width=width, height=height)
    trimmed_polygons = perform_trim(polygons_with_points, width=width, height=height)
    # with every polygon, create a corresponding mapping to be viewed by the map.html
    mapped = [(0, 0, width, height, polygon, {"fg": color}) for polygon, color in zip(trimmed_polygons, DEFAULT_COLOR)]
    return mapped

def create_voronoi(center_points: List[Tuple[float, float]], width: float, height: float, return_obj: bool=False):
    # just use scipy 
    distant_points = [(width*2*ix, height*2*iy) for ix, iy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]]
    np_points = np.array(center_points + distant_points)
    vor = Voronoi(np_points)
    # print(vor.vertices, vor.regions, vor.ridge_vertices, vor.ridge_points)
    vertices = vor.vertices 
    regions = [r for r in vor.regions if len(r) > 0]
    polygons = []
    for point, region in zip(center_points, regions):
        polygon = []
        for v in region:
            if(v != -1):
                # is outer region; ignore 
                polygon.append(vertices[v])
        # format in the non-restricted form 
        polygons.append( (point, polygon) )
    if(return_obj):
        return vor 
    else:
        return polygons

def create_voronoi_deprecated(center_points: List[Tuple[float, float]], width: float, height: float):
    # attempt to create a voronoi from the center points.
    # This is a generic variant (split in the middle). TODO weight-affected variants
    for point in center_points:
        # for each point, designated the default region as the entirety of the board 
        edges = {(0, 0, width, 0), (0, 0, 0, height), (width, 0, width, height), (0, height, width, height)}
        for other in center_points:
            if(other == point):
                # is self; ignore 
                continue 
            # is not self, create the perpendicular bisector and cut it with all edges 

# from https://stackoverflow.com/questions/20677795/how-do-i-compute-the-intersection-point-of-two-lines
def line_intersection(a, b, c, d, first_is_segment=True, second_is_segment=True):
    t1 = ((a[0] - c[0]) * (c[1] - d[1]) - (a[1] - c[1]) * (c[0] - d[0])) 
    t2 = ((a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0]))
    u1 = ((a[0] - c[0]) * (a[1] - b[1]) - (a[1] - c[1]) * (a[0] - b[0])) 
    u2 = ((a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0]))
    # print(a, b, c, d)
    # print(t1, t2, u1, u2) 
    if t2 == 0 or u2 == 0:
        # detected zeroval; considered False 
        return False
    t = t1 / t2
    u = u1 / u2

    # check if line actually intersect
    if ( (not first_is_segment or 0 <= t <= 1) and (not second_is_segment or 0 <= u <= 1)):
        return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    else: 
        return False

# from https://stackoverflow.com/questions/1560492/how-to-tell-whether-a-point-is-to-the-right-or-left-side-of-a-line 
# side should be 
def side(line_start, line_end, point):
  return (line_end[0] - line_start[0])*(point[1] - line_start[1]) - (line_end[1] - line_start[1])*(point[0] - line_start[0])

def perform_trim(polygons: List[Tuple[ Tuple[float, float], List[Tuple[float, float]] ]], width: float, height: float):
    # the input polygons are unrestricted (e.g edges are not in respective range of width x height view)
    # intersect line vs edge; if meet, use the intersected point instead of current 
    c = [(0, 0), (width, 0), (width, height), (0, height)]
    edges = [(c[0], c[1]), (c[1], c[2]), (c[2], c[3]), (c[3], c[0])]
    result = []
    for point, polygon in polygons:
        trimmed = []
        print(point, polygon)
        for start, end in zip(polygon, polygon[1:] + polygon[:1]):
            # if line intersected by any of the border, the end vertices will be put into trimmed instead of itself.
            used_intersect_point = False
            for ste, ede in edges:
                # check intersection with second as line (as opposed to segment)
                intersect = line_intersection(start, end, ste, ede, second_is_segment=False)
                if(intersect):
                    # if found intersection, choose the point which is NOT at the same side with the core 
                    print("Found intersect", intersect, " between ", start, end)
                    if(side(ste, ede, point) * side(ste, ede, start) > 0):
                        # start is same side; replace end 
                        trimmed.append(start); trimmed.append(intersect)
                    else:
                        # end is same side; replace start 
                        trimmed.append(intersect); trimmed.append(end)
                    used_intersect_point = True 
                    break 
            if(not used_intersect_point):
                # not used an intersection point; put the first point into trim 
                trimmed.append(start)
        trimmed = [tuple(p) for p in trimmed]
        # in addition to this; if there is out-of-bound point after this, limit them to the respective range 
        limit_x = lambda x: x if 0 <= x <= width else 0 if x < 0 else width
        limit_y = lambda y: y if 0 <= y <= height else 0 if y < 0 else height 
        trimmed = [(limit_x(x), limit_y(y)) for x, y in trimmed]
        # clear possible duplication 
        trimmed = [p for i, p in enumerate(trimmed) if p not in trimmed[:i] ]
        # thrown into result 
        result.append(trimmed)
    return result

if __name__ == "__main__":
#    from scipy.spatial import voronoi_plot_2d
#    test_points = [[10, 25], [20, 30], [30, 10], [10, 5]]
#    vor = create_voronoi(test_points, 40, 40, return_obj=True)
#    import matplotlib.pyplot as plt
#    fig = voronoi_plot_2d(vor)
#    plt.show()
    fake_data = [{"category": "v1"}, {"category": "v1"}, {"category": "v1"}, {"category": "v1"}, 
            {"category": "v2"}, {"category": "v2"}, {"category": "v2"}, {"category": "v2"},  
            {"category": "v3"}, {"category": "v3"}, {"category": "v3"}, {"category": "v4"},]
    print(generate_map(fake_data, width=600, height=600))
