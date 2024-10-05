"""Tactical (battalion-level) map/scenario. For now we will have railroaded scenarios basing on result of a test.
Goal is for this to be updated to have interactable impact."""

import json, io, os
import random, base64

from typing import Dict, List, Optional

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
        # there is a mapless mode; reserved for static variant for now
        if getattr(self, "mapless_mode", False):
            # mapless mode initiated. Only take the type, narration & leave
            data["mapless_mode"] = True 
            data["scenario_type"] = "static"
            data["narration"] = self.narration
            return data
        # converting units to dict 
        data["offensive_units"] = {k: {"id": k, "tooltip": v["name"], **v} for k, v in self.offensive_units.items()}
        data["defensive_units"] = {k: {"id": k, "tooltip": v["name"], **v} for k, v in self.defensive_units.items()}
        data["neutrals"] = {k: {"id": k, "tooltip": v["name"], **v} for k, v in getattr(self, "neutrals", dict()).items()} # could be object or unrelated units. Can be empty
        # no map for now.
        data["map"] = getattr(self, "map", None) 
        # script is converted to json to be given to javascript hardcoded 
        offensive_ids, defensive_ids = set(self.offensive_units.keys()), set(self.defensive_units.keys())
        # TODO properly assign necessary health for all three scenario types.
        if self.scenario_type == "static":
            data["railroad_script"] = json.dumps(self.script)
            if getattr(self, "outcome", None): # if can be redirected, this will allow moving on
                data["next_section"] = "Continue"
        elif self.scenario_type == "choice":
            data["choices"] = self.choices
            data["choice_script"] = json.dumps(self.script)
        elif self.scenario_type == "random":
            data["railroad_script"] = json.dumps(self.script)
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

    def return_next_result(self) -> Optional[str]:
        """This will trigger for scenario_type == static. If can lead outward to a different scenario, this will return the appropriate key. If cannot, this return None. Ideally returning that (None) should never happens, but who knows."""
        assert self.scenario_type == "static", "@return_next_result: cannot get a static result from scenario_type != static. ({})".format(self.scenario_type)
        return getattr(self, "outcome", None)

    def return_choice_result(self, choice: str) -> str:
        """This will trigger for scenario_type == choice. Go to the appropriate outcome depending on the choice taken"""
        assert self.scenario_type == "choice", "@return_choice_result: cannot get a choice result from scenario_type != choice. ({})".format(self.scenario_type)
        return self.outcome[choice]

    def return_specific_result(self, result: float) -> str:
        """This will trigger for scenario_type == random, or its quiz mode. Quiz mode will come up to a value between 0-100; while choices MUST be limited to 100 roll range, sorted from bad -> good as well."""
        assert self.scenario_type == "random", "@retrieve_specific_result: cannot get a randomized/quized result from scenario_type != random. ({})".format(self.scenario_type)
        assert 0 <= result <= 100.0, "@retrieve_specific_result: result cannot be outside of [0-100] range"
        current_upper_bound = 0
        for chance, outcome_str in self.choices:
            current_upper_bound += chance 
            if result < current_upper_bound:
                return self.outcome[outcome_str]
        raise ValueError("If reach here, choices' collective chance does not reach 100 (only {}). Fix the scenario.".format(current_upper_bound))

    def roll_for_result(self) -> str:
        """The above but randomly roll for a result."""
        return self.return_specific_result(random.random() * 100.0)


class HardcodedScenario(Scenario):
    # hardcoding a simple static ambush
    def __init__(self):
        self.scenario_type = "static"
        self.size = (600, 600)
        self.narration = [
            "This is an example scenario detailing a simple ambush.",
            "The ambushed side (red) was known to patrol along a known path, and the ambushers (blue) hid in nearby terrain waiting to strike.",
            "Surprised by the sudden contact, the following red unit retreated, leaving its sibling exposed to enemy attack",
            "Further indecision from this unit means it did not mount an effective defense to the ambusher onslaught, who circled around and outflanked it during subsequent combat."
        ]
        self.offensive_units = {0: {"name": "Patrol squad 1", "icon": "1-circle"}, 1: {"name": "Patrol squad 2", "icon": "2-circle"}}
        self.defensive_units = {2: {"name": "Ambush squad 1", "icon": "1-circle"}, 3: {"name": "Ambush squad 2", "icon": "2-circle"}}
        self.offensive_color = "red"
        self.defensive_color = "blue"
        self.script = [
            # attacking unit moving through a curve
            {0: (300, 0, 100.0, "move"), 1: (300, 50, 100.0, "move"),    2: (400, 275, 100.0, "hide"), 3: (400, 325, 100.0, "hide")},
            {0: (300, 100, 100.0, "move"), 1: (300, 150, 100.0, "move"), 2: (400, 275, 100.0, "hide"), 3: (400, 325, 100.0, "hide")},
            {0: (300, 200, 100.0, "move"), 1: (300, 250, 100.0, "move"), 2: (400, 275, 100.0, "hide"), 3: (400, 325, 100.0, "hide")},
            {0: (300, 300, 100.0, "move"), 1: (350, 300, 100.0, "move"), 2: (400, 275, 100.0, "attack"), 3: (400, 325, 100.0, "attack")},
            # fighting start, 1st unit destroyed, 2nd fallback
            {0: (300, 300, 100.0, "hold"), 1: (325, 300, 50.0, "defend"), 2: (375, 275, 90.0, "attack"), 3: (370, 325, 90.0, "attack")},
            {0: (275, 300, 100.0, "move"), 1: (300, 300, 10.0, "rout"), 2: (350, 300, 85.0, "attack"), 3: (350, 350, 80.0, "attack")},
            # defensive unit moved up, one outflanking the 2nd and mop up the remainder
            {0: (275, 300, 100.0, "hold"), 1: (None, None, None, "rout"), 2: (350, 300, 85.0, "hold"), 3: (250, 350, 80.0, "move")},
            {0: (275, 300, 80.0, "defend"), 1: (None, None, None, "rout"), 2: (350, 300, 75.0, "attack"), 3: (225, 275, 80.0, "move")},
            {0: (275, 300, 40.0, "defend"), 1: (None, None, None, "rout"), 2: (320, 300, 65.0, "attack"), 3: (250, 275, 75.0, "attack")},
            {0: (275, 300, 10.0, "rout"), 1: (None, None, None, "rout"), 2: (310, 300, 65.0, "attack"), 3: (250, 310, 75.0, "attack")},
            {0: (None, None, None, "rout"), 1: (None, None, None, "rout"), 2: (310, 300, 65.0, "hold"), 3: (250, 310, 75.0, "hold")}
        ]

        self.paths = [
            {"path": "M300 0 L300 300 L600 300", "color": "brown", "width": "2"} # road
        ]
        self.regions = [
            {"path": "M425 310 L310 320 L225 225 L200 350 L210 400 L425 400 L425 310 Z", "fill": "green", "border": "green"} # ambush region A
        ]

        self.outcome = None

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
        self.offensive_units = {0: {"name": "Attack squad", "icon": "1-circle", "rank_icon": "star"}}
        self.defensive_units = {1: {"name": "Defend squad 1", "icon": "1-circle"}, 2: {"name": "Defend squad 2", "icon": "2-circle"}}
        self.offensive_color = "red"
        self.defensive_color = "blue"
        self.script = {
            "initial":
                [{0: (300, 0, 100.0, "hold"), 1: (300, 100, 80.0, "hold"), 2: (400, 275, 35.0, "hold")}],
            "choice_1": 
                [
                    {0: (300, 75, 100.0, "attack"), 1: (300, 100, 80.0, "hold"), 2: (400, 275, 35.0, "hold")},
                    {0: (300, 75, 100.0, "attack"), 1: (300, 100, 80.0, "defend"), 2: (375, 250, 35.0, "move")},
                    {0: (300, 80, 100.0, "attack"), 1: (300, 105, 80.0, "defend"), 2: (350, 225, 35.0, "move")},
                    {0: (300, 85, 100.0, "attack"), 1: (300, 105, 80.0, "rout"), 2: (350, 150, 35.0, "move")},
                    {0: (325, 100, 100.0, "move"), 1: (275, 125, 80.0, "rout"), 2: (350, 150, 35.0, "move")},
                    {0: (325, 115, 100.0, "attack"), 1: (None, None, 80.0, "rout"), 2: (330, 130, 35.0, "attack")},
                    {0: (335, 125, 100.0, "attack"), 1: (None, None, 80.0, "rout"), 2: (350, 120, 35.0, "defend")},
                    {0: (345, 125, 100.0, "attack"), 1: (None, None, 80.0, "rout"), 2: (380, 115, 35.0, "rout")},
                    {0: (345, 125, 100.0, "hold"), 1: (None, None, 80.0, "rout"), 2: (None, None, 35.0, "rout")},
                ],
            "choice_2": 
                [
                    {0: (400, 0, 100.0, "move"), 1: (300, 100, 80.0, "hold"), 2: (400, 275, 35.0, "hold")},
                    {0: (450, 50, 100.0, "move"), 1: (300, 100, 80.0, "hold"), 2: (400, 275, 35.0, "hold")},
                    {0: (450, 150, 100.0, "move"), 1: (300, 100, 80.0, "hold"), 2: (400, 275, 35.0, "hold")},
                    {0: (450, 250, 100.0, "attack"), 1: (300, 100, 80.0, "hold"), 2: (400, 275, 35.0, "hold")},
                    {0: (445, 255, 100.0, "attack"), 1: (350, 100, 80.0, "move"), 2: (400, 275, 35.0, "defend")},
                    {0: (425, 265, 100.0, "attack"), 1: (400, 100, 80.0, "move"), 2: (390, 285, 35.0, "rout")},
                    {0: (425, 265, 100.0, "hold"), 1: (400, 150, 80.0, "move"), 2: (365, 310, 35.0, "rout")},
                    {0: (400, 250, 100.0, "hold"), 1: (400, 200, 80.0, "move"), 2: (None, None, 35.0, "rout")},
                    {0: (400, 250, 100.0, "attack"), 1: (400, 230, 80.0, "attack"), 2: (None, None, 35.0, "rout")},
                    {0: (400, 260, 100.0, "attack"), 1: (400, 235, 80.0, "attack"), 2: (None, None, 35.0, "rout")},
                    {0: (400, 240, 100.0, "attack"), 1: (400, 215, 80.0, "defend"), 2: (None, None, 35.0, "rout")},
                    {0: (400, 215, 100.0, "attack"), 1: (400, 185, 80.0, "rout"), 2: (None, None, 35.0, "rout")},
                    {0: (400, 215, 100.0, "hold"), 1: (400, 135, 80.0, "rout"), 2: (None, None, 35.0, "rout")},
                    {0: (400, 215, 100.0, "hold"), 1: (None, None, 80.0, "rout"), 2: (None, None, 35.0, "rout")},
                ]
        }
        self.choices = {
            "choice_1": "Attack (1)",
            "choice_2": "Go around and attack (2)"
        }

class HardcodedRollScenario(Scenario):
    # hardcoding a simple multi-result scenario decided by a dice roll/exam question. The received HTML should link to appropriate consequence.
    def __init__(self):
        self.scenario_type = "random"
        self.size = (600, 600)
        self.narration = [
            "This is an example scenario; which will have different possible result depending on either a dice roll, or a mini-exam.",
            "You are being pounded by enemy artillery prefacing an enemy assault. You have done all you could to reinforce your position, but, sometimes, fate will get you anyway",
            "If you believe in any god, start praying."
        ]
        self.defensive_units = {0: {"name": "Defend squad 1", "icon": "1-circle"}, 1: {"name": "Defend squad 2", "icon": "2-circle"}}
        self.offensive_units = {2: {"name": "Unknown attacking force", "icon": "question-circle"}, 3: {"name": "Unknown attacking force", "icon": "question-circle"}, 4: {"name": "Unknown attacking force", "icon": "question-circle"}, 5: {"name": "Unknown attacking force", "icon": "question-circle"}}
        self.neutrals = {arty_fire_id: {"name": "Artillery fire", "icon": "patch-exclamation", "color": "yellow"} for arty_fire_id in range(101, 105)}
        self.script = [
                {0: (325, 0, 100.0, "defend"), 1: (275, 25, 100.0, "defend"), 101: (315, 15, None, "blink"), 102: (340, 5, None, "inactive"), 103: (285, 15, None, "active"), 104: (260, 25, None, "inactive"), 2: (150, 600, 100.0, "move"), 3: (300, 600, 100.0, "move"), 4: (450, 600, 100.0, "move"), 5: (300, 550, 100.0, "move")},
                {0: (325, 0, 100.0, "defend"), 1: (275, 25, 100.0, "defend"), 101: (315, 15, None, "inactive"), 102: (340, 5, None, "blink"), 103: (285, 15, None, "inactive"), 104: (260, 25, None, "blink"), 2: (150, 550, 100.0, "move"), 3: (300, 550, 100.0, "move"), 4: (450, 550, 100.0, "move"), 5: (300, 500, 100.0, "move")}
        ]
        self.defensive_color = "blue"
        self.offensive_color = "red"
        
        self.choices = [
            (25, "result_dead"),
            (75, "result_unscathed")
        ]

class WrittenScenario(Scenario):
    # scenario that is written in a json file and needed to be loaded in.
    def __init__(self, file_path: str):
        with io.open(file_path, "r", encoding="utf-8") as jf:
            data = json.load(jf)
        base_folder = os.path.dirname(file_path)
        # TODO enforcing necessary checks?
        for k, v in data.items():
            setattr(self, k, v)
            if(k.endswith("_path")):
                # additionally, for any _path property, try to retrieve the associating file and put that in as data 
                if k == "map_path":
                    if os.path.isfile(os.path.join(base_folder, v)):
                        # has the file in shared folder, use that.
                        with io.open(os.path.join(base_folder, v), "rb") as mf:
                            image_encoded = base64.b64encode(mf.read())
                            setattr(self, "map", image_encoded.decode("utf-8"))
                    elif os.path.isfile(v):
                        # has the file directly accessible from root, use that 
                        with io.open(v, "rb") as mf:
                            image_encoded = base64.b64encode(mf.read())
                            setattr(self, "map", image_encoded.decode("utf-8"))
                    else:
                        print("@WrittenScenario error: invalid (no file found) map_path: ", v)
                else:
                    raise NotImplementedError # Not implementing others yet.

class Narrative:
    """A narrative has the same structure as an interactive novel, linking multiple scenarios together depending on choices.This should handle the above at the minimum."""
    def __init__(self, narrative_graph: Dict[str, Scenario]):
        # for now, graph must be pre-constructed with all scenarios 
        self.graph = narrative_graph

    def get_scenario(self, scenario_key: str) -> Scenario:
        return self.graph[scenario_key]

    def handle_scenario_choice(self, src_scenario_key: str, choice: Optional[str]=None, quiz_result: Optional[float]=None) -> str:
        """Default, book-like variant. Simply handle going forward and backward. There is no blocking element yet. (e.g if somebody go directly to one section, they can just go from there)."""
        src_scenario = self.graph[src_scenario_key]
        if src_scenario.scenario_type == "static":
            # When encountering this, the scenario only has one choice (a narrative section), or no choice at all.
            # TODO let static have an option to continue if possible 
            next_scenario_key = src_scenario.return_next_result()
        elif src_scenario.scenario_type == "choice":
            # When encountering this, the scenario will have choice selectable by player 
            next_scenario_key = src_scenario.return_choice_result(choice)
        elif src_scenario.scenario_type == "random":
            # When encountering this, depending on if quiz_result is available, either perform a roll to determine the outcome or use that as direct outcome 
            if(quiz_result):
                next_scenario_key = src_scenario.return_specific_result(quiz_result)
            else:
                next_scenario_key = src_scenario.roll_for_result() 
        else:
            raise NotImplementedError("Invalid source scenario {} of type {}".format(src_scenario, src_scenario.scenario_type))
        return next_scenario_key

class HardcodedNarrative(Narrative):
    # hardcoded variant. Doesn't quite make sense yet; and it's ok.
    def __init__(self):
        # build the scenario 
        end_key, end_sc = "example_static", HardcodedScenario()
        roll_key, roll_sc = "example_roll", HardcodedRollScenario()
        choice_key, choice_sc = "example_choice", HardcodedChoiceScenario()
        roll_sc.outcome = {"result_unscathed": choice_key, "result_dead": end_key}
        choice_sc.outcome = {"choice_1": roll_key, "choice_2": end_key}
        super(HardcodedNarrative, self).__init__({end_key: end_sc, roll_key: roll_sc, choice_key: choice_sc})


class AntalInfantryGameNarrative(Narrative):
    # transition to json-based when done with the main scenarios.
    def __init__(self, id_to_key_fn: callable=lambda i: "antal_inf_section_{:d}".format(i)):
        narrative_graph = dict()
        section_by_id = dict()
        for section_number in [3, 4, 7, 10, 11, 12, 13, 14, 15, 16, 17, 29, 32, 39, 40, 41, 43, 45, 48, 51, 52, 53, 55, 58, 60, 61, 62, 65, 93, 96]:
            try:
                section_by_id[section_number] = narrative_graph[id_to_key_fn(section_number)] = WrittenScenario("data/game/tactical/antal_inf/section_{:d}.json".format
(section_number))
            except Exception as e:
                print("Failed section: ", section_number)
                raise e
        # current deadends: 16, 48, 51, 52, 55, 58, 62, 93, 96
        section_by_id[3].outcome = {"choice_forward_slope": id_to_key_fn(4), "choice_reverse_slope": None, "choice_split_up": None}
        section_by_id[4].outcome = id_to_key_fn(7)
        section_by_id[7].outcome = {"choice_personal_recon": id_to_key_fn(10), "choice_continue_work": id_to_key_fn(11)}
        section_by_id[10].outcome = {"result_dead": id_to_key_fn(16), "result_piper_hit": id_to_key_fn(17)}
        section_by_id[17].outcome = {"choice_help": id_to_key_fn(51), "choice_stay": id_to_key_fn(52)}
        section_by_id[11].outcome = {"choice_rest": id_to_key_fn(12), "choice_keep_working": id_to_key_fn(13)}
        section_by_id[13].outcome = {"result_arty_direct_hit": id_to_key_fn(62), "result_captured": id_to_key_fn(48), "result_survive": id_to_key_fn(15)}
        section_by_id[15].outcome = {"result_captured": id_to_key_fn(55), "result_survive_v1": id_to_key_fn(32), "result_survive_v2": id_to_key_fn(39)}
        section_by_id[39].outcome = {"result_die": id_to_key_fn(58), "result_survive": id_to_key_fn(41)}
        section_by_id[32].outcome = {"choice_withdraw": id_to_key_fn(45), "choice_stay": id_to_key_fn(43)}
        section_by_id[41].outcome = {"choice_withdraw": id_to_key_fn(45), "choice_stay": id_to_key_fn(61)}
        section_by_id[43].outcome = {"result_die": id_to_key_fn(58), "result_captured": id_to_key_fn(93)}
        section_by_id[45].outcome = {"result_fail_breakout": id_to_key_fn(44), "result_die": id_to_key_fn(58), "result_captured": id_to_key_fn(55)}
        section_by_id[61].outcome = {"result_survive": id_to_key_fn(60), "result_die": id_to_key_fn(58), "result_captured": id_to_key_fn(93)}
        section_by_id[60].outcome = {"result_survive": id_to_key_fn(65), "result_die": id_to_key_fn(58), "result_captured": id_to_key_fn(55)}
        section_by_id[65].outcome = {"result_die": id_to_key_fn(58), "result_captured": id_to_key_fn(55)}
        section_by_id[12].outcome = {"choice_personal_recon": id_to_key_fn(96), "choice_stay": id_to_key_fn(53)}
        section_by_id[53].outcome = {"result_die": id_to_key_fn(62), "result_survive": id_to_key_fn(14)}
        section_by_id[14].outcome = {"result_die": id_to_key_fn(58), "result_captured": id_to_key_fn(48), "result_survive": id_to_key_fn(29)}
        section_by_id[29].outcome = {"result_die": id_to_key_fn(62), "result_captured": id_to_key_fn(48), "result_die_2": id_to_key_fn(40)}
        super(AntalInfantryGameNarrative, self).__init__(narrative_graph)