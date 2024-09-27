"""Tactical (battalion-level) map/scenario. For now we will have railroaded scenarios basing on result of a test.
Goal is for this to be updated to have interactable impact."""

import json

class Scenario:
    """A scenario should consist of a terrain map, a list of offensive/defensive units and for now, the script that it'll adhere to. Upon requested, the scenario will play out as scripted."""
    def convert_to_template_data(self):
        """Convert internal data to html-compatible dictionary.
        Returns:
            a dict of:
                - map: either a base64 string of an image, or None for blank, or TODO svg support for dynamic buildup.
                - o/d units: list of {unit_properties} of each force; which must have "id" as a field. TODO support unit names display as well.
                - o/d color: HTML color used for the units.
                - script: list of positions & states of each unit per phase."""
        data = {}
        # converting units to dict 
        data["offensive_units"] = [{"id": v, "name": k} for k, v in self.offensive_units.items()]
        data["defensive_units"] = [{"id": v, "name": k} for k, v in self.defensive_units.items()]
        # no map for now.
        data["map"] = None 
        # script is converted to json to be given to javascript hardcoded 
        # TODO properly assign necessary health 
        offensive_ids, defensive_ids = set(self.offensive_units.values()), set(self.defensive_units.values())
        steps = [
            {
                "offensive": {i: [x, y, 100.0, action] for i, (x, y, action) in script_raw_step.items() if i in offensive_ids},
                "defensive": {i: [x, y, 100.0, action] for i, (x, y, action) in script_raw_step.items() if i in defensive_ids}
            }
            for script_raw_step in self.script]
        data["railroad_script"] = json.dumps(steps)
        # rest is given as-is
        for attr in ["offensive_color", "defensive_color"]:
            data[attr] = getattr(self, attr)
        return data


class HardcodedScenario(Scenario):
    # hardcoding a simple ambush
    def __init__(self):
        self.size = (600, 600)
        self.offensive_units = {"attacking_unit_1": 0, "attacking_unit_2": 1}
        self.defensive_units = {"defending_unit_1": 2, "defending_unit_2": 3}
        self.offensive_color = "red"
        self.defensive_color = "blue"
        self.script = [
            # attacking unit moving through a curve
            {0: (300, 0, "move"), 1: (300, 50, "move"),    2: (400, 275, "hide"), 3: (400, 325, "hide")},
            {0: (300, 100, "move"), 1: (300, 150, "move"), 2: (400, 275, "hide"), 3: (400, 325, "hide")},
            {0: (300, 200, "move"), 1: (300, 250, "move"), 2: (400, 275, "hide"), 3: (400, 325, "hide")},
            {0: (300, 300, "move"), 1: (350, 300, "move"), 2: (400, 275, "attack"), 3: (400, 325, "attack")},
            # fighting start, 1st unit destroyed, 2nd fallback
            {0: (300, 300, "hold"), 1: (325, 300, "defend"), 2: (375, 275, "attack"), 3: (370, 325, "attack")},
            {0: (275, 300, "move"), 1: (300, 300, "rout"), 2: (350, 300, "attack"), 3: (350, 350, "attack")},
            # defensive unit moved up, one outflanking the 2nd and mop up the remainder
            {0: (275, 300, "hold"), 1: (None, None, "rout"), 2: (350, 300, "hold"), 3: (250, 350, "move")},
            {0: (275, 300, "defend"), 1: (None, None, "rout"), 2: (350, 300, "attack"), 3: (225, 275, "move")},
            {0: (275, 300, "defend"), 1: (None, None, "rout"), 2: (320, 300, "attack"), 3: (250, 275, "attack")},
            {0: (275, 300, "rout"), 1: (None, None, "rout"), 2: (310, 300, "attack"), 3: (250, 310, "attack")},
            {0: (None, None, "rout"), 1: (None, None, "rout"), 2: (310, 300, "hold"), 3: (250, 310, "hold")}
        ]
