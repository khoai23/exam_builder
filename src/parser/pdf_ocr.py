"""This will be standalone for now; try to get all data from pdf and run it through tesseract to get the raw text input.
Should output in both organized (json) and unorganized (txt) variant."""

import sys, io, re
import fitz 
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = 'D:\Program Files\Tesseract-OCR/tesseract.exe'

RAW_JSON_FILE = "test/ocr_extracted_text.json"
CLEANED_JSON_FILE = "test/cleaned_text.json"

def mass_image_to_text(pdf_path, start_index: int=0, end_index: int=None):
    pdf = fitz.open(pdf_path)
    data = {}
    end_index = end_index or len(pdf)
    for page_idx in range(start_index, end_index):
        data[page_idx] = ""
        page = pdf.load_page(page_idx)
        for image_index, (xref, *_) in enumerate(page.get_images(full=True)):
            image = pdf.extract_image(xref)
            image_bytes = image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            data[page_idx] = data[page_idx] + "\n\n" + text
        print("Parsed page {}; data is text with {} characters".format(page_idx, len(data[page_idx])))
    return data

single_linebreak_cleaner = re.compile("(?<!\n)\n(?!\n)")
section_regex = re.compile("Section (\d+)") # doesnt work

def throwaway_until_threshold(boundary_set: set, max_range: int=400):
    """Try to throw away as many outlier as possible until boundary is ranged under max_range value"""
    if max(boundary_set) - min(boundary_set) <= max_range:
        # satisfied, just breakout 
        return boundary_set
    avg = sum(boundary_set) / len(boundary_set)
    worst = max(boundary_set, key=lambda v: abs(v-avg)) # furthest distance from avg 
    result_set = boundary_set - {worst}
    return throwaway_until_threshold(result_set, max_range=max_range) 

def clean(data: dict):
    # clean up associating data. OCR keep linebreak as-is; so only keep double-linebreak
    cleaned = dict()
    pieces = list()
    for k, v in data.items():
        v = re.sub(single_linebreak_cleaner, " ", v)
        v = v.replace("\u2019", "'").replace("\u2014", "-").replace("\u201c", "\"").replace("\u201d", "\"").strip()
        pieces.extend( (p.strip() for p in v.split("\n\n")) )
        cleaned[k] = v
    # after cleaning, we have "pieces" of narrative dialog; attempt to find all possible boundaries. 
    section_boundary = dict()
    for pid, p in enumerate(pieces):
        section_head = re.findall(section_regex, p)
        if section_head and "go to section" not in p.lower():
            # possible section; check boundary on every of them. more is better than misses, but too much is fundamentally wrong
            for sid in section_head:
                if sid not in section_boundary:
                    section_boundary[sid] = {pid}
                else:
                    section_boundary[sid].add(pid)
    return cleaned, pieces, section_boundary

if __name__ == "__main__":
    import json, os
    # P1: generate raw data, put into json
    if os.path.isfile(RAW_JSON_FILE):
        with io.open(RAW_JSON_FILE, "r") as ef:
            data = json.load(ef)
    else:
        data = mass_image_to_text(sys.argv[1], start_index=10)
        with io.open(RAW_JSON_FILE, "w") as ef:
            json.dump(data, ef, indent=2)
    # P2: clean; this always run for now
    cleaned, pieces, sectioned = clean(data)
    # throw away what could be wrong
    threshold_guess = {k: throwaway_until_threshold(v, max_range=400) for k, v in sectioned.items()}
    print("\n".join("{}: [{}-{}]({}) = {}".format(k, min(v), max(v), max(v)-min(v), v) for k, v in threshold_guess.items()))
    # if there are unclaimed regions between sections, it automatically go to the previous
    thresholds = {int(sid): (min(boundary), max(boundary)+1) for sid, boundary in threshold_guess.items()}
    for sid in thresholds:
        if sid-1 in thresholds and thresholds[sid-1][-1] < thresholds[sid][0]:
            lower, upper = thresholds[sid-1]
            thresholds[sid-1] = (lower, thresholds[sid][0]-1)
    sections = ["[{}]:\n".format(sid) + "\n".join(pieces[lower:upper+1]) for sid, (lower, upper) in thresholds.items()]
    with io.open(CLEANED_JSON_FILE, "w") as ef:
        json.dump(sections, ef, indent=2)

