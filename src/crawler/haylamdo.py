import io, os, csv, re 
import traceback
from functools import partial

from src.crawler import generic

INCLUDE_KEY = {"bai-", "trac-nghiem"}
FILTER_KEY = {"..", "void"}
APPEND_DOMAIN = "https://haylamdo.com"

def get_neighbor_links(soup_or_url, include_key=INCLUDE_KEY, filter_key=FILTER_KEY, append_domain=APPEND_DOMAIN):
    return generic.get_neighbor_links(soup_or_url, filter_key=filter_key, append_domain=append_domain)
    
def perform_crawl(*args, neighbor_link_fn=get_neighbor_links, **kwargs):
    return generic.perform_crawl(*args, neighbor_link_fn=neighbor_link_fn, **kwargs)

CUES = {
        "Câu": ("question", 4)
        "A.": ("answer1", 2)
        "B.": ("answer2", 2)
        "C.": ("answer3", 2)
        "D.": ("answer4", 2)
}
ANSWER_CONVERSION = {"A": 1, "B": 2, "C": 3, "D": 4}
def process_data(soup, url=None, writer=None):
    # data is oriented by internal paragraphs; isolate by section.
    data = soup.find("div", class_="main-content-detail")
    rows = []
    current_data = dict()
    last_used_field = None
    for node in data.getChildren():
        if(node.find("section")):
            # is finalizer; first add the appropriate result 
            answer_box = node.find("div", class_="toggle-content")
            current_data["correct_id"] = ANSWER_CONVERSION[answer_box.find("span").text.strip()] # dangerous?
            paragraphs = answer_box.find_all("p")
            for i, p in enumerate(paragraphs):
                if("trả lời" in p.text.lower()):
                    # explanation box next to it 
                    current_data["explanation"] = paragraphs[i+1].text.strip()
            rows.append(current_data)
            current_data = dict()
            last_used_field = None 
            continue
        text = node.text.strip()
        used = False
        for cue, (data_field, startlimit) in CUES.items():
            if cue in text:
                # if found appropriate cue; add to respective field
                used = True 
                last_used_field = data_field
                current_data[data_field] = text[startlimit:].strip()
                break
        if(not used):
            # if not found any cue; add to previous field (found in last_used_field)
            current_data[last_used_field] += text.strip()
        if(node.find("img")):
            # found an image; convert accordingly 
            current_data[last_used_field] += " ".join(["|||{}|||".format(img["src"]) for img in node.find_all("img", src=True)])
    # after the loop, should have enough data to write into rows 
    print(rows)


if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO)
    start_url = "https://haylamdo.com/toan-6-ket-noi/trac-nghiem-bai-tap-cuoi-chuong-viii.jsp" 
    soup = generic.get_parsed(start_url)
    process_data(soup, start_url, writer=writer)
