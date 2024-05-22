import io, json, pickle

from src.crawler.generic import get_parsed 
from src.crawler.bricktactical import generate_md

BASE_PATH = "http://www.brickarms.com/{:s}.php"
ALL_PREFIX = "weapons"
PREFERRED_PREFIXES = ["modern", "world-war"]
OTHER_PREFIXES = ["historical", "blades", "scifi"]

def retrieve_items(path, get_name_only: bool=False):
    soup = get_parsed(path)
    items = dict() if not get_name_only else set()
    for item in soup.find_all("div", class_="home-products"):
        name = item.find("div", class_="caption").find("h5").text.strip()
        if get_name_only:
            items.add(name); continue
        img_wrapper = item.find("div", class_="thumbnail-img")
        link = img_wrapper.find("a")["href"].strip().replace(" ", "%20")
        image = img_wrapper.find("img")["src"]
        items[name] = dict(link=link, base_image=image)
    return items

def retrieve_categorized_items():
    categorized = {k: dict() for k in PREFERRED_PREFIXES + OTHER_PREFIXES}
    all_items = retrieve_items(BASE_PATH.format(ALL_PREFIX), get_name_only=False)
    for prfx in PREFERRED_PREFIXES + OTHER_PREFIXES:
        cat_items = retrieve_items(BASE_PATH.format(prfx))
        for item_name in cat_items:
            if item_name not in all_items:
                # TODO check
                print("Item {} of cat {} not available in full; check back later.".format(item_name, prfx))
            categorized[prfx][item_name] = all_items.pop(item_name, cat_items[item_name])
    categorized["unknown"] = all_items 
    return categorized

def _safe_link(raw_link: str):
    if any(raw_link.startswith(cue) for cue in ("http", "www")):
        # correct link, ignore 
        return raw_link
    return "http://www.brickarms.com/" + raw_link 

if __name__ == "__main__":
    import sys 
    if len(sys.argv) < 2:
        print("Must be {script} full|crawl|convert")
        sys.exit(-1)
    arg = sys.argv[-1]
    if arg in ("full", "crawl"):
        data = retrieve_categorized_items()
        with io.open("test/brickarms.json", "w", encoding="utf-8") as btf:
            json.dump(data, btf, indent=2)
        print("Crawled data.")
    else:
        with io.open("test/brickarms.json", "r", encoding="utf-8") as btf:
            data = json.load(btf)
        print("Loaded data.")
    if arg in ("full", "convert"):
        # data should already been categorized.
        md_text = generate_md(data, title="Brick Arms", ensure_safe_fn=_safe_link)
        with io.open("data/lessons/brickarms.md", "w", encoding="utf-8") as mf:
            mf.write(md_text)
        print("Formatting data to .md file.")
    print("Done")

