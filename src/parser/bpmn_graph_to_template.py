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
                logger.debug("Unknown child: {}. This will be ignored".format(c))
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
        logger.debug("Searching for <" + tag + ">")
        for element in soup.find_all(tag):
            # extract data & save
            props = property_extractor_fn(tag, element)
            extracted_data[props["id"]] = props
    return extracted_data
    
    
def convert_to_scenario(data: Dict[str, dict], templates: Dict[str, str]):
    """Convert from XML to templated scenario. Format the associated template type (static, roll, random) with appropriate key types."""
    for key, props in data.items():
        if props["type"] == "sequenceFlow":
            continue # arrow item, ignore 
        # parse the name and throw the correct identifier 
        if ":" not in props["description"]:
            logger.debug("Item {} have an invalid description; item will be ignored.".format(props))
            continue
        prefix, props["true_description"] = props.split(":")
        if "(" in prefix: # has shortcuts, add it into their outgoings 
            true_id, shortcuts = prefix.replace(")", "").split("(")
            for s in shortcuts.split(","):
                props["outgoings"].append(int(s)) # index values must be integer. TODO allow arbitrary format later, somehow.
        else:
            true_id = prefix 
        if "/" in true_id: # has multiple lead-up to each other; generating duplicates and note to user about this (plus purposely damage the template later on.
            logger.warning("The following items ({}) are the same consequentially but narratively different; they will be broken and force you to update their flow manually.")
            props["true_id"] = true_ids = [int(i) for i in true_id.split("/")]
        else:
            props["true_id"] = int(true_id)
        # if end-state, also generate conforming result key to be used by the 
    # now with true_id ready, create the associating items and narrative map 
    generated_sections, narrative_graph = dict(), dict()
    for key, props in data.items():
        if props["type"] == "sequenceFlow":
            continue # arrow item, ignore again
        true_ids = props["true_id"] if isinstance(props["true_id"], tuple) else (props["true_id"], )
        multiple_target_issue = False
        if props["type"] == "exclusiveGateway": # choice item; generate appropriate response from template
            # if exclusiveGateway, generate the choices using annotated outward signs. Report in case where it lost the annotation.
            choice_dict = {}
            missing_name_issue = False
            for out_key in outgoings:
                # cannot have int as choices outward must be properly narrated
                arrow = data[out_key]
                target_section = data[arrow["targetRef"]] 
                target_id = target_section["true_id"]
                choice_name = arrow.get("description", None)
                if choice_name is None:
                    choice_name = "!!Missing Choice Name!!"
                    missing_name_issue = True 
                    logger.warning("[{}] Section no. {}'s choice is not annotated. The name will be replaced with a default value.".format(key, props["true_id"]))
                if isinstance(target_id, tuple):
                    # need manual correction what-to-where; purposely set up a wrong pathway and warn through logging 
                    logger.warning("[{}] Section no. {} lead to one of {}; Make sure to manually realign them afterward.".format(key, props["true_id"], target_id))
                    multiple_target_issue = True
                    choice_dict["to_section_{}".format("/".join(target_id))] = choice_name
                else:
                    # is already a working version; just linkup as-is
                    choice_dict["to_section_{:d}".format(target_id)] = choice_name
            # if true_ids, generate equivalent templates accordingly 
            for i in true_ids:
                section_data = dict(templates["choice"])
                section_data["choices"] = dict(choice_dict)
                section_data["narration"] = [
                    "This is autogenerated data for Section {:d}. Please replace with the appropriate text & illustration (if any).".format(i),
                    "The section is of type \"choice\". Make sure to supply the narrative context for the wording of the choices."
                ]
                if missing_name_issue:
                    section_data["narration"].append("NOTE: There are missing choice names. Make sure to amend that.")
                if multiple_target_issue:
                    section_data["narration"].append("NOTE: There are choices which are incorrectly designated. Make sure to amend that.")
                generated_sections["section_{:d}".format(i)] = section_data 
                narrative_graph["section_{:d}".format(i)] = {k: v.replace("to_", "") for k, v in }
        elif props["type"] == "task": # roll item; generate roughly equal chance to each possible option 
            # TODO prioritize narratively important nodes
                       
        else: # static item; for endEvent, assure there is no outward connection; for other, assure the leadout is properly generated.
            for i in true_ids:
                section_data = dict(templates["static"])
                section_data["narration"] = [
                        "This is autogenerated data for Section {:d}. Please replace with the appropriate text & illustration (if any).".format(i)
                ]
                if props.get("outgoings", None):
                    if props["type"] == "endEvent":
                        # endEvent should not have outgoings atm. 
                        logger.warning("[{}] Section {} should not have outgoing arrows; but the graph do have them {}. The data will be ignored.".format(key, i, props["outgoings"]))
                    else:
                        # other will have it as the "outcome" property
                    
if __name__ == "__main__":
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)
    test_xml = "test/learn_bpmn.xml"
    with io.open(test_xml, "r") as tf:
        data = extract_bpmn(tf.read(), ["startEvent", "intermediateThrowEvent", "endEvent", "exclusiveGateway", "task", "sequenceFlow"])
    logger.info(json.dumps(data, indent=2))
