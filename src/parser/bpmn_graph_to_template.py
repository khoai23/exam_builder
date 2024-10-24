"""This will handle converting BPMN element of a graph into associating templated data. This is useful in both recreating interactive novel (e.g Antal) and plotting a course with multiple tags."""

import io, json
import xml.etree.ElementTree as ET 
from bs4 import BeautifulSoup

from typing import List, Dict, Tuple, Optional

import logging 
logger = logging.getLogger(__name__)

def bpmn_default_extractor(element_type: str, item) -> Dict:
    """Default taking info from nodes in bpmn. For now, get only id and description (name)."""
    data = {"type": element_type}
    data["id"] = item.get("id", None)
    if element_type == "sequenceFlow":
        # linkage, extract sourceRef and targetRef accordingly.
        data["source"] = item.get("sourceRef")
        data["target"] = item.get("targetRef")
        # description will only be added if available; as "name" may not be available during single-result transition
        if item.get("name", None):
            data["description"] = item.get("name")
    else:
        # default; extract child <incoming>/<outgoing> if any.
        data["description"] = item.get("name", None)
        incomings, outgoings = [], [] 
        for c in item.children:
            if c.name == "incoming":
                incomings.append(c.text)
            elif c.name == "outgoing":
                outgoings.append(c.text)
            else:
                logger.debug("Unknown child: {} (of item {}). This will be ignored".format(c, item))
        if incomings:
            data["incomings"] = incomings
        if outgoings:
            data["outgoings"] = outgoings
    return data

def extract_bpmn(content: str, requested_tags: List[str], property_extractor_fn: callable=bpmn_default_extractor)-> Dict[str, Dict]:
    """Extract the necessary nodes & connection from the xml."""
    # root = ET.fromstring(content)
    soup = BeautifulSoup(content, features="xml")
    extracted_data = dict()
    for tag in requested_tags:
        start_length = len(extracted_data)
        for element in soup.find_all(tag):
            # extract data & save
            props = property_extractor_fn(tag, element)
            extracted_data[props["id"]] = props
        logger.info("Searched for <{:s}>, added {:d} entries".format(tag, len(extracted_data) - start_length))
    return extracted_data
    
    
def convert_to_scenario(data: Dict[str, dict], templates: Dict[str, str]):
    """Convert from XML to templated scenario. Format the associated template type (static, roll, random) with appropriate key types."""
    for key, props in data.items():
        if props["type"] == "sequenceFlow":
            continue # arrow item, ignore 
        # parse the name and throw the correct identifier 
        if ":" not in (props.get("description", "") or ""):
            logger.debug("Item {} have an invalid description; item will be ignored.".format(props))
            continue
        prefix, props["true_description"] = props["description"].split(":")
        if "(" in prefix: # has shortcuts, add it into their outgoings 
            if "outgoings" not in props:
                props["outgoings"] = [] # support not having native outgoing (everything lead to death)
            true_id, shortcuts = prefix.replace(")", "").split("(")
            for s in shortcuts.split(","):
                props["outgoings"].append(int(s)) # index values must be integer. TODO allow arbitrary format later, somehow.
        else:
            true_id = prefix 
        if "/" in true_id: # has multiple lead-up to each other; generating duplicates and note to user about this (plus purposely damage the template later on.
            logger.warning("The following items ({}) are the same consequentially but narratively different; they will be broken and force you to update their flow manually.".format(true_id))
            props["true_id"] = true_ids = [int(i) for i in true_id.split("/")]
        else:
            props["true_id"] = int(true_id)
        # if end-state, also generate conforming result key to be used by the 
    # now with true_id ready, create the associating items and narrative map 
    generated_sections, narrative_graph = dict(), dict()
    for key, props in data.items():
        if props["type"] == "sequenceFlow" or "true_id" not in props:
            continue # arrow item or decidedly wrong nodes, ignore again
        if isinstance(props["true_id"], (tuple, list)):
            true_ids = props["true_id"]  
        else: 
            true_ids = (props["true_id"], )
        multiple_target_issue = False
        if props["type"] in ("exclusiveGateway", "task"): # choice/random item; generate appropriate response from template
            # generate the choices using annotated outward signs. Report in case where it lost the annotation if the mode is .
            is_choice = props["type"] == "exclusiveGateway"
            if is_choice:
                choice_dict = {}
                missing_name_issue = False
            else:
                result_array = []

            # convert the outgoings list into proper outcome dict/list matching the types
            for out_key in props["outgoings"]:
                if isinstance(out_key, str):
                    # is arrow object id; retrieve the correct id variant
                    arrow = data[out_key]
                    target_section = data[arrow["target"]] 
                    target_id = target_section["true_id"]
                    # choices outward must be properly narrated in case of the `choice` variant.
                    choice_name = arrow.get("description", None)
                    if choice_name is None:
                        choice_name = "!!Missing Choice Name!!"
                        missing_name_issue = True 
                        logger.warning("[{}] Section no. {}'s choice is not annotated. The name will be replaced with a default value.".format(key, props["true_id"]))
                else: 
                    assert not is_choice, "[{}] Section no. {} is a choice but has an independent shortcut outward. Check the graph construction.".format(key, props["true_id"])
                    # is int/tuple; rollback with this specific 
                    target_id = out_key

                if isinstance(target_id, (tuple, list)):
                    # need manual correction what-to-where; purposely set up a wrong pathway and warn through logging 
                    logger.warning("[{}] Section no. {} lead to one of {}; Make sure to manually realign them afterward.".format(key, props["true_id"], target_id))
                    multiple_target_issue = True 
                    composite_id_str = "/".join((str(i) for i in target_id))
                    if is_choice:
                        choice_dict["to_section_{}".format(composite_id_str)] = choice_name
                    else:
                        result_array.append( (1, "to_section_{}".format(composite_id_str)) ) # standard weight for now
                else:
                    # is already a working version; just linkup as-is
                    if is_choice:
                        choice_dict["to_section_{:d}".format(target_id)] = choice_name 
                    else:
                        result_array.append((1, "to_section_{:d}".format(target_id)))

            outgoings = props["outgoings"]
            if is_choice:
                assert len(choice_dict) == len(outgoings), f"{choice_dict} different size to {outgoings}"
            else:
                assert len(result_array) == len(outgoings), f"{result_array} different size to {outgoings}"

            # if multiple true_id,  generate equivalent templates accordingly to each of those
            for i in true_ids:
                if is_choice:
                    section_data = dict(templates["choice"])
                    section_data["choices"] = dict(choice_dict)
                    section_data["outcome"] = narrative_graph["section_{:d}".format(i)] = {k: v.replace("to_", "") for k, v in section_data["choices"].items()}
                else:
                    section_data = dict(templates["random"])
                    # recalculate the result array with any correct percentage 
                    weights = {2: [50, 50], 3: [30, 30, 40], 4: [25, 25, 25, 25]}
                    result_weight_array = weights[len(result_array)]
                    section_data["choices"] = [(w, k) for w, (iw, k) in zip(result_weight_array, result_array)]
                    section_data["outcome"] = narrative_graph["section_{:d}".format(i)] = {v: v.replace("to_", "") for w, v in section_data["choices"]}

                section_data["narration"] = [
                    "This is autogenerated data for Section {:d}. Please replace with the appropriate text & illustration (if any).".format(i),
                    props.get("true_description", "!Missing true description!").strip(),
                    "The section is of type \"{:s}\". Make sure to supply the narrative context for the wording of the choices.".format("choice" if is_choice else "random")
                ]
                if missing_name_issue and is_choice:
                    # only append this warning in choice mode (roll mode doesn't need this)
                    section_data["narration"].append("NOTE: There are missing choice names. Make sure to amend that.")
                if multiple_target_issue:
                    section_data["narration"].append("NOTE: There are choices which are incorrectly designated. Make sure to amend that.")
                generated_sections["section_{:d}".format(i)] = section_data 
        else: # static item; for endEvent, assure there is no outward connection; for other, assure the leadout is properly generated.
            for i in true_ids:
                section_data = dict(templates["static"])
                section_data["narration"] = [
                        "This is autogenerated data for Section {:d}. Please replace with the appropriate text & illustration (if any).".format(i)
                ]
                if props.get("outgoings", None):
                    if props["type"] == "endEvent":
                        # endEvent should not have outgoings atm. 
                        logger.warning("[{}] Section {} should not have outgoing indication; but the graph do have them {}. The data will be ignored.".format(key, i, props["outgoings"]))
                    else:
                        # other will have it as the "outcome" property. Should be only one 
                        outgoings = props["outgoings"]
                        if len(outgoings) > 1:
                            # multiple result available; pick 1st. TODO pick best (in case we have route to some explanation)
                            logger.warning("[{}] Section {} should only have one outgoing indication; but the graph do have multiple {}. Only the 1st will be evaluated.".format(key, i, props["outgoings"]))
                        outcome = outgoings[0]
                        if isinstance(outcome, str):
                            # is an arrow id (default); retrieve the correct target from the graph 
                            arrow_data = data[outcome]
                            outcome = data[arrow_data["target"]]["true_id"]
                        if isinstance(outcome, tuple):
                            # lead up to multiple result; like before, purposely damage it
                            logger.warning("[{}] Section no. {} lead to one of {}; Make sure to manually realign them afterward.".format(key, props["true_id"], outcome))
                            section_data["narration"].append("NOTE: There are choices which are incorrectly designated. Make sure to amend that.")
                            narrative_graph["section_{:d}".format(i)] = section_data["outcome"] = "section_{}".format("/".join(outcome))
                        else:
                            narrative_graph["section_{:d}".format(i)] = section_data["outcome"] = "section_{}".format(outcome)
                generated_sections["section_{:d}".format(i)] = section_data
    return generated_sections, narrative_graph
                    
if __name__ == "__main__":
    logging.basicConfig()
    logger.setLevel(logging.INFO)
    test_xml = "test/learn_bpmn.xml"
    with io.open(test_xml, "r") as tf:
        data = extract_bpmn(tf.read(), ["startEvent", "intermediateThrowEvent", "endEvent", "exclusiveGateway", "task", "sequenceFlow"])
#    logger.info(json.dumps(data, indent=2))
    # try to run to construct the whole thing 
    templates = {k: {"scenario_type": k, "size": [600, 600], "mapless_mode": True} for k in ["static", "choice", "random"]}
    sections, graph = convert_to_scenario(data, templates)
    logger.debug("------------")
    logger.debug(json.dumps(sections, indent=2))
    logger.debug("------------")
    logger.debug(json.dumps(graph, indent=2))
