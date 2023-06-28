"""Here to create and draw corresponding maps for each region (category) of the whole database.
TODO: 
    - Each tag with specific amount of count drawn for each sub-region 
    - Drawable arrows between regions
    - Trigger a link when an arrow is clicked
    - Upon finishing a test, colorized sub-region to indicate progress
"""
import math, random 
from collections import defaultdict 
import colorsys

from src.map_algorithm.region import create_voronoi
from src.map_algorithm.subregion import assign_subregions

import logging 
logger = logging.getLogger()

from typing import Optional, List, Tuple, Any, Union, Dict 

def get_color(i: int, total: int, mode: str="hsv"):
    # get color variants by "slicing" the hsv into {total} subregion
    # for now just use the light variant (S at 40%)
    hsv = (1.0 * i / total, 0.4, 0.8)
    rgb = [int(255 * v) for v in colorsys.hsv_to_rgb(*hsv)]
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

DEFAULT_COLOR = ["green", "blue", "red", "purple", "orange", "yellow"]
def generate_map_by_region(data: List[Dict], width: float=1000, height: float=1000, center_generate_mode: str="radial", center_noise: Optional[float]=None):
    """Generate a region map from list of current data. Basing on the category section."""
    center_x, center_y = width / 2, height / 2
    # for each region, generate appropriate center point {radius} away from center 
    if(center_generate_mode == "radial"):
        print("Generate in radial mode")
        categories = set((d.get("category", "N/A") for d in data))
        radius = min(width, height) / 2 * 0.75
    #    for i in range(len(categories)+1):
    #        print(i, "->", math.sin(2 * math.pi / len(categories) * i), math.cos(2 * math.pi / len(categories) * i))
        centers = [(center_x + radius * math.sin(2 * math.pi / len(categories) * i), center_y + radius * math.cos(2 * math.pi / len(categories) * i)) for i in range(len(categories))]
        if center_noise:
            centers = [ (x + (random.random()-0.5) * 2 * center_noise, y + (random.random()-0.5) * 2 * center_noise) for x, y in centers ]
    else:
        print("Generate in completely random mode")
        categories = set((d.get("category", "N/A") for d in data))
        centers = [(random.random()*width, random.random()*height) for _ in categories]

    # apply voronoi to draw the polygons 
    polygons_with_points = create_voronoi(centers, width=width, height=height)
    trimmed_polygons = perform_trim(polygons_with_points, width=width, height=height)
    # with every polygon, create a corresponding mapping to be viewed by the map.html
    catlist = list(categories)
    mapped = [(0, 0, width, height, polygon, {"center": point, "fg": get_color(index, len(trimmed_polygons)), "text": catlist[index]}) for index, (point, polygon) in enumerate(trimmed_polygons)]
    return mapped

def generate_map_by_subregion(data: List[Dict], width: float=1000, height: float=1000, return_center: bool=False):
    """Generate the corresponding map with subregion (category with tag) instead.
    Generate random points equal to each unique combination of tags under each category.
    TODO allow splitting into further child-region to A. generate arbitrary shapes and B. create border regions"""
    countdict = defaultdict(int)
    for d in data:
        sorted_tag = (list(d["tag"]) if d.get("tag", []) else [])
        sorted_tag.sort()
        key = tuple([d.get("category", "N/A")] + sorted_tag)
        countdict[key] += 1
    centers = [(random.random()*width, random.random()*height) for _ in range(len(countdict))]
    # apply voronoi to draw the polygons 
    polygons_with_points = create_voronoi(centers, width=width, height=height)
    trimmed_polygons = perform_trim(polygons_with_points, width=width, height=height)
    # region check - assign nearby regions with similar color & tags 
    regioned_polygons, regioned_keys, region_centers = assign_subregions(countdict, trimmed_polygons, width=width, height=height, return_center=True)
    mapped = [(0, 0, width, height, polygon, {"center": point, "fg": get_color(index, len(regioned_polygons)), "text": "-".join(regioned_keys[index])}) for index, (point, polygon) in enumerate(regioned_polygons)]
    if(return_center):
        return region_centers, mapped 
    else:
        return mapped


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

    # check if segment actually intersect
    if ( (not first_is_segment or 0 <= t <= 1) and (not second_is_segment or 0 <= u <= 1)):
        return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    else: 
        return False

# from https://stackoverflow.com/questions/1560492/how-to-tell-whether-a-point-is-to-the-right-or-left-side-of-a-line 
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
#        print(point, polygon)
        for start, end in zip(polygon, polygon[1:] + polygon[:1]):
            # if line intersected by any of the border, the end vertices will be put into trimmed instead of itself.
            used_intersect_point = False
            for ste, ede in edges:
                # check intersection with second as line (as opposed to segment)
                intersect = line_intersection(start, end, ste, ede, second_is_segment=False)
                if(intersect):
                    # if found intersection, choose the point which is NOT at the same side with the core 
                    # print("Found intersect", intersect, " between ", start, end)
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
        trimmed = (tuple(p) for p in trimmed)
        # in addition to this; if there is out-of-bound point after this, limit them to the respective range 
        limit_x = lambda x: x if 0 <= x <= width else 0 if x < 0 else width
        limit_y = lambda y: y if 0 <= y <= height else 0 if y < 0 else height 
        trimmed = [(limit_x(x), limit_y(y)) for x, y in trimmed]
        # clear possible duplication 
        trimmed = [p for i, p in enumerate(trimmed) if p not in trimmed[:i] ]
        # if three points in the same horizontal/vertical axis, collapse them 
        # check for last and end point as well
        extended = trimmed[-1:] + trimmed + trimmed[:1]
        # trimmed is checked with +1 due to extension at the front
        centered = [i-1 for i in range(1, len(trimmed)+1) if extended[i-1][0] == extended[i][0] == extended[i+1][0]
                                                        or extended[i-1][1] == extended[i][1] == extended[i+1][1]]
#        for i in centered: 
#            print("Found collapsible: ", i, trimmed[i-1], trimmed[i], trimmed[i+1])
#        print("Before collapse: ", trimmed)
        trimmed = [p for i, p in enumerate(trimmed) if i not in centered]
#        print("After collapse: ", trimmed)
        # thrown into result 
        result.append((point, trimmed))
    return result

if __name__ == "__main__":
#    from scipy.spatial import voronoi_plot_2d
#    test_points = [[10, 25], [20, 30], [30, 10], [10, 5]]
#    vor = create_voronoi(test_points, 40, 40, return_obj=True)
#    import matplotlib.pyplot as plt
#    fig = voronoi_plot_2d(vor)
#    plt.show()
    fake_data = [{"category": "c{}".format(c), "tag": ["t{}".format(t)]} for c in range(2) for t in range(2)]
    # map_points = generate_map_by_region(fake_data, center_generate_mode="random", width=600, height=600, center_noise=50)
    region_centers, map_points = generate_map_by_subregion(fake_data, width=600, height=600, return_center=True)
#    print(map_points)
    import matplotlib.pyplot as plt 
    plt.figure()
    for *_, points, attr in map_points:
        xs, ys = zip(*(points + points[:1]))
        plt.plot(xs, ys)
    cxs, cys = zip(*[attr["center"] for *_, attr in map_points])
    cxs, cys = list(cxs), list(cys)
    plt.scatter(cxs, cys)
    for i, (*_, attr) in enumerate(map_points):
#        print(attr["text"])
        plt.annotate(attr["text"], (cxs[i], cys[i]))
    rxs, rys = zip(*region_centers.values())
    plt.scatter(rxs, rys)
    for text, (rx, ry) in region_centers.items():
        plt.annotate(text, (rx, ry))
    plt.show()

