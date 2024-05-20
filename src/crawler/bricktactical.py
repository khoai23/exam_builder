import io, json, pickle

from src.crawler.generic import get_parsed 

CATALOG_TEMPLATE = "https://bricktactical.com/collections/weapons?page={:d}"
def iterate_catalog(size: int, retrieve_extra_image: bool=False):
    """Get soup & extract all concerning links"""
    all_items = dict()
    for page in range(1, size+1):
        soup = get_parsed(CATALOG_TEMPLATE.format(page))
        items = soup.find_all("a", class_="product-card")
        for item in items:
            # print(item)
            item_name = item.find("div", class_="product-card__name").text.strip()
            item_base_image_raw = item.find("img", class_="product-card__image")
            if item_base_image_raw and "src" in item_base_image_raw.attrs:
                base_image = item_base_image_raw["src"]
            else:
                base_image = None
            item_base_image_backup_raw = item.find("img", class_="lazyload")
            if item_base_image_backup_raw and "data-src" in item_base_image_backup_raw.attrs:
                base_image_backup = item_base_image_backup_raw["data-src"]
            else:
                base_image_backup = None
            # print("----------------\n", item, "\n", item_base_image_raw, "\n", item_base_image_backup_raw)
            link = item["href"]
            all_items[item_name] = dict(link=link, base_image=base_image, base_image_backup=base_image_backup)
            print("Found item {}: {}".format(item_name, all_items[item_name]))
    return all_items

def _safe_link(raw_link: str):
    if raw_link.startswith("//"):
        # double slash is missing https 
        return "https:" + raw_link 
    elif raw_link.startswith("/"):
        # single slash is missing domain 
        return "https://bricktactical.com" + raw_link
    else:
        return raw_link

def autocategorize(base: dict, category_cue: dict={"Packs": ["pack", "stack", "squad", "modular"], "Certain (Ruskie)": ["ak", "svd", "pk", "rpk", "rpd", "bt47", "bt74"], "Certain (US)": ["m16", "m4", "m60", "m249", "m79", "m97"], "Weird/SW": ["blaster", "energy", "beam", "space", "plasma", "zombie", "raygun"], "Melee": ["sword", "knife", "hammer", "axe", "hilt"], "Parts": ["body", "leg", "helmet", "headset", "vest"], "Others": ["lord", "overmold", "sign", "bottle", "ball", "printed", "random", "crate", "knuckle", "beaker"]}, default_category: str="Default"):
    """Split into categories to hopefully make things less bloated."""
    categorized = {default_category: dict(), **{k: dict() for k in category_cue.keys()}}
    for item_name, item_info in base.items():
        is_default = True
        lowered_item_name = item_name.lower()
        for cat, cues in category_cue.items():
            if any(c in lowered_item_name for c in cues):
                is_default = False 
                categorized[cat][item_name] = item_info
                break 
        if is_default:
            categorized[default_category][item_name] = item_info 
    return categorized

def generate_md(categorized: dict, ensure_safe_fn: callable=lambda x: x):
    sections = []
    # construct header
    header = "# LEGO-compatible: BrickTactical\n"
    sections.append(header)
    # print(categorized)
    for cat, items in categorized.items():
        category_header = "{:s}\n".format(cat)
        table_header = "|Item|Image|"
        table_separator = "|:----|:---:|"
        rows = [r"|[{:s}]({:s})|<img src='{:s}'></src>|".format(name, ensure_safe_fn(data["link"]), ensure_safe_fn(data["base_image"])) for name, data in items.items()]
        table_data = "\n".join([category_header, table_header, table_separator] + rows)
        sections.append(table_data) 

    full_md_text = "\n\n".join(sections)
    return full_md_text

if __name__ == "__main__":
    import sys 
    if len(sys.argv) < 2:
        print("Must be {script} full|crawl|convert")
        sys.exit(-1)
    arg = sys.argv[-1]
    if arg in ("full", "crawl"):
        data = iterate_catalog(19)
        with io.open("test/bricktac.json", "w", encoding="utf-8") as btf:
            json.dump(data, btf, indent=2)
        print("Crawled data.")
    else:
        with io.open("test/bricktac.json", "r", encoding="utf-8") as btf:
            data = json.load(btf)
        print("Loaded data.")
    if arg in ("full", "convert"):
        categorized = autocategorize(data)
        md_text = generate_md(categorized, ensure_safe_fn=_safe_link)
        with io.open("data/lessons/bricktac.md", "w", encoding="utf-8") as mf:
            mf.write(md_text)
        print("Formatting data to .md file.")
    print("Done")
