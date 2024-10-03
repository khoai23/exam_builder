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
        offensive_ids, defensive_ids = set(self.offensive_units.values()), set(self.defensive_units.values())
        # TODO properly assign necessary health for all three scenario types.
        if self.scenario_type == "static":
            railroad_script = [
                {i: [x, y, 100.0, action] for i, (x, y, action) in script_step.items()}
                for script_step in self.script]
            data["railroad_script"] = json.dumps(railroad_script)
        elif self.scenario_type == "choice":
            data["choices"] = self.choices
            choice_script = dict()
            for choice, script_sequence in self.script.items():
                script_sequence_with_health = []
                for i in range(len(script_sequence)):
                    script_sequence_with_health.append({i: [x, y, 100.0, action] for i, (x, y, action) in script_sequence[i].items()})
                choice_script[choice] = script_sequence_with_health
            data["choice_script"] = json.dumps(choice_script)
        else:
            raise NotImplementedError
        # rest is given as-is
        for attr in ["scenario_type", "size", "offensive_color", "defensive_color", "narration"]:
            data[attr] = getattr(self, attr) # TODO designate some as optional 
        # if no map & svg path/regions are available & 
        if not data["map"]:
            paths = getattr(self, "paths", None)
            regions = getattr(self, "regions", None)
            if paths or regions:
                data.update(paths=paths, regions=regions, svg_scene=True)
        return data


class HardcodedScenario(Scenario):
    # hardcoding a simple static ambush
    def __init__(self):
        self.scenario_type = "static"
        self.size = (600, 600)
        self.narration = [
            "This is an example scenario detailing a simple ambush.",
            "The ambushed side (red) was known to patrol along a known path, and the ambushers hid in nearby terrain waiting to strike.",
            "Surprised by the sudden contact, the following red unit retreated, leaving its sibling exposed to enemy attack",
            "Further indecision from this unit means it did not mount an effective defense to the ambusher onslaught, who circled around and outflanked it during subsequent combat."
        ]
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

        self.paths = [
            {"path": "M300 0 L300 300 L600 300", "color": "brown", "width": "2"} # road
        ]
        self.regions = [
            {"path": "M425 310 L310 320 L225 225 L200 350 L210 400 L425 400 L425 310 Z", "fill": "green", "border": "green"} # ambush region A
        ]

class HardcodedChoiceScenario(Scenario):
    # hardcoding a simple interactive multi-choice scenario. The received HTML should link to appropriate consequence.
    def __init__(self):
        self.scenario_type = "choice"
        self.size = (600, 600)
        self.narration = [
            "This is an example scenario detailing a simple choice.",
            "You are in control of an unit conducting assault on known enemy defense.",
            "Opposing you are two enemy units which are stationed a distance apart. They may come to each other's aid. One unit (1) is closer and only slightly weaker than you, the other (2) was badly mauled in a prior engagement, but is stationed deeper inward.",
            "Do you launch your first attack on (1) or (2)?"
        ]
        self.offensive_units = {"attacking_unit_1": 0}
        self.defensive_units = {"defending_unit_1": 1, "defending_unit_2": 2}
        self.offensive_color = "red"
        self.defensive_color = "blue"
        self.script = {
            "initial":
                [{0: (300, 0, "hold"), 1: (300, 100, "hold"), 2: (400, 275, "hold")}],
            "choice_1": 
                [
                    {0: (300, 75, "attack"), 1: (300, 100, "hold"), 2: (400, 275, "hold")},
                    {0: (300, 75, "attack"), 1: (300, 100, "defend"), 2: (375, 250, "move")},
                    {0: (300, 80, "attack"), 1: (300, 105, "defend"), 2: (350, 225, "move")},
                    {0: (300, 85, "attack"), 1: (300, 105, "rout"), 2: (350, 150, "move")},
                    {0: (325, 100, "move"), 1: (275, 125, "rout"), 2: (350, 150, "move")},
                    {0: (325, 115, "attack"), 1: (None, None, "rout"), 2: (330, 130, "attack")},
                    {0: (335, 125, "attack"), 1: (None, None, "rout"), 2: (350, 120, "defend")},
                    {0: (345, 125, "attack"), 1: (None, None, "rout"), 2: (380, 115, "rout")},
                    {0: (345, 125, "hold"), 1: (None, None, "rout"), 2: (None, None, "rout")},
                ],
            "choice_2": 
                [
                    {0: (400, 0, "move"), 1: (300, 100, "hold"), 2: (400, 275, "hold")},
                    {0: (450, 50, "move"), 1: (300, 100, "hold"), 2: (400, 275, "hold")},
                    {0: (450, 150, "move"), 1: (300, 100, "hold"), 2: (400, 275, "hold")},
                    {0: (450, 250, "attack"), 1: (300, 100, "hold"), 2: (400, 275, "hold")},
                    {0: (445, 255, "attack"), 1: (350, 100, "move"), 2: (400, 275, "defend")},
                    {0: (425, 265, "attack"), 1: (400, 100, "move"), 2: (390, 285, "rout")},
                    {0: (425, 265, "hold"), 1: (400, 150, "move"), 2: (365, 310, "rout")},
                    {0: (400, 250, "hold"), 1: (400, 200, "move"), 2: (None, None, "rout")},
                    {0: (400, 250, "attack"), 1: (400, 230, "attack"), 2: (None, None, "rout")},
                    {0: (400, 260, "attack"), 1: (400, 235, "attack"), 2: (None, None, "rout")},
                    {0: (400, 240, "attack"), 1: (400, 215, "defend"), 2: (None, None, "rout")},
                    {0: (400, 215, "attack"), 1: (400, 185, "rout"), 2: (None, None, "rout")},
                    {0: (400, 215, "hold"), 1: (400, 135, "rout"), 2: (None, None, "rout")},
                    {0: (400, 215, "hold"), 1: (None, None, "rout"), 2: (None, None, "rout")},
                ]
        }
        self.choices = {
            "choice_1": "Attack (1)",
            "choice_2": "Go around and attack (2)"
        }

class WrittenScenario(Scenario):
    # scenario that is written in a json file and needed to be loaded in.
    def __init__(self, file_path: str):
        with io.open(file_path, "r", encoding="utf-8") as jf:
            data = json.load(jf)
        # TODO enforcing necessary checks?
        for k, v in data.items():
            setattr(self, k, v)
