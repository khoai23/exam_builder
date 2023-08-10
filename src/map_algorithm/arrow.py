"""Code to give appropriate arrows between border subregions.
Will give appropriate control points to allow "jumping" basing on input 
"""
from collections import defaultdict 

from src.map_algorithm.subregion import has_border, sq_eu_d, eu_d

from typing import Optional, List, Tuple, Any, Union, Dict, Set

def mapped_has_border(mreg1, mreg2): # adapt the has_border for mapped 
    return has_border(mreg1[-1], mreg2[-1])

def list_connections(regions: List[ Tuple[Any, List] ], return_dict: bool=True) -> Union[Dict, List]:
    """Find all possible connections between associating regions. Input must be list of ({center}, {polygon})
    Return a dict {region_idx}: {all_connections} or list ({region_1_idx}, {region_2_idx}) """
    result = (  (i, j)
        for i in range(len(regions)-1)
        for j in range(i+1, len(regions))
            if has_border(regions[i][-1], regions[j][-1]))
    if(return_dict):
        rdict = defaultdict(list)
        for p1id, p2id in result:
            rdict[p1id].append(p2id)
            rdict[p2id].append(p1id)
        return rdict
    else:
        return list(result)
            
def format_arrow(arrow: Tuple[Tuple[float, float], Tuple[float, float]], thickness: float=1.0, color: str="black", control_offset: Tuple[float, float]=None, offset_in_ratio_mode: bool=False, create_bound: bool=False) -> Dict:
    """Convert the attribute of an arrow depending on selected property. Output a dictionary containing all the properties.
    If create_bound; convert all coordinates to this specific bound"""
    result = {}
    # arrow/edges will be formatted as ({point}, {contour point}); contour point can be None at which the line is straight.
    result["points"] = [(p, None) for p in arrow]
    if control_offset:
        # for now all arrows in quadratic mode
        center = (arrow[0][0] + arrow[1][0]) / 2, (arrow[0][1] + arrow[1][1]) / 2
        # control_offset if in ratio mode will be scaled by flat length of current arrow 
        if(offset_in_ratio_mode):
            scale = eu_d(arrow[0], arrow[1])
            control_offset = (control_offset[0] * scale, control_offset[1] * scale)
        # calculate the control point
        control_point = (center[0] + control_offset[0], center[1] + control_offset[1])
        # put at last 
        result["points"][1] = (arrow[1], control_point)
    result["thickness"] = thickness
    result["color"] = color
    # create corresponding arrow-head by assimilating thickness. 
    # TODO push the arrow back +width to let arrow tip stop at point, right now stop at width+2
    # TODO customizable arrowhead
#    width, height = thickness * 2, thickness * 3
    result["arrowhead"] = {
        "markerUnits": "strokeWidth",
        "markerWidth": 2,
        "markerHeight": 3,
        "refX": 2/2,
        "refY": 3/2,
        "orient": "auto"
    }
    result["arrowhead_poly"] = [(0, 0), (2, 3/2), (0, 3)]
    if create_bound:
        # normal bound - minimum/maximum rectangle
        min_x = min(*(p[0][0] for p in result["points"]), *(p[1][0] for p in result["points"] if p[1] is not None))
        min_y = min(*(p[0][1] for p in result["points"]), *(p[1][1] for p in result["points"] if p[1] is not None))
        max_x = max(*(p[0][0] for p in result["points"]), *(p[1][0] for p in result["points"] if p[1] is not None))
        max_y = max(*(p[0][1] for p in result["points"]), *(p[1][1] for p in result["points"] if p[1] is not None))
        # add padding to prevent clipping 
        pad = thickness * 5 
        # convert all points accordingly. TODO prevent bound from exceeding expected width/height
        bound = (min_x-pad, min_y-pad, max_x-min_x+pad, max_y-min_y+pad)
        x, y = min_x-pad, min_y-pad 
        # convert all points accordingly
        result["points"] = [((p[0]-x, p[1]-y), (c if c is None else (c[0]-x, c[1]-y))) for p, c in result["points"]]
        return bound, result
    else:
        return result
