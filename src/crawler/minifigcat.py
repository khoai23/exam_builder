import io, json, traceback
from functools import partial 

import src.crawler.generic as generic

DUMP_PATH = "test/minifigcat.pkl"
APPEND_DOMAIN = "https://www.minifigcat.com/shop/"
FILTER_KEY = [".jpg"] # image has link for some reason; ignore.

def clear_link(link: str):
    if "?" in link:
        # if pageId is part of the link; preserve that to allow traversing multiple-page. Otherwise just delete all 
        if "?pageId=" in link: 
            if "&" in link: # has additional arg behind the pageId; just drop those
                link = link.split("&", 1)[0]
            else 
                pass # keep as-is
        else:
            link = link.split("?", 1)[0]
    if "#" in link:
        link = link.split("#", 1)[0]
    return link

def sanitize(string: str):
    """Disallow anything that isnt alphanumeric or space"""
    return "".join((c if c.isalnum() or c.isspace() else " " for c in string))

def get_neighbor_links(soup_or_url, filter_key=FILTER_KEY, append_domain=APPEND_DOMAIN):
    links = [clear_link(l) for l in generic.get_neighbor_links(soup_or_url, filter_key=filter_key, append_domain=append_domain)]
    return links #[l.split("?", 1)[0] if "?" in l else l for l in links] # additional removal of possible redundant arguments.

def get_colors(color_url="https://www.minifigcat.com/shop/Colors/"):
    soup = generic.get_parsed(color_url)
    colors_full_text = [s.text.strip() for s in soup.find_all("span", class_="subcategory-name")]
    colors_name_raw = (s.split(")")[-1] if ")" in s else s for s in colors_full_text)
    colors_name = set((s.replace("-", " ") for s in colors_name_raw if s and "=" not in s))
    # removed the special SP Green / Tank Green 2 variant; add them back
    colors_name.update(["SP Green", "Tank Green 2"])
    return list(sorted(colors_name, key=lambda x: len(x), reverse=True)) # organize from long -> short

def parse_name_and_color(full_name, all_colors: list=None, rejoin: bool=False) -> tuple:
    parsed = sanitize(full_name) #"".join((c if c.isalnum() or c.isspace() else " " for c in full_name))
    color = next((clr for clr in all_colors if clr in parsed), None)
    if color is None:
        generic.logger.info("@parse_name_and_color: Cannot parse for \"{}\". Algorithm is not good enough, or no color specified.".format(parsed))
        return parsed, "N/A"
    prefix, suffix = parsed.split(color)
    if rejoin:
        # if rejoin; both halves are returned together. Not ideal as the category number, e.g (55) can still remain as prefix
        return prefix.strip() + " " + suffix.strip(), color
    else:
        if len(prefix) >= len(suffix):
            return prefix.strip(), color
        else:
            return suffix.strip(), color

def process_data(soup, url=None, data=None, colors=None):
    """Get into the link and attempt to extract according section if any."""
    try:
        item_info_box = soup.find("div", class_=["product-details", "box-product"])
        if item_info_box is None:
            generic.logger.debug("Link {} has no info box; skipping.".format(url))
            return 
        full_name = item_info_box.find("h1", class_="fn title").text.strip()
        image = item_info_box.find("img")
        image_source = image["src"]
#        if "_" in full_name: # color_itemname is very common here. There is a variant of i-tem-na-me-color but that has to be handled the other way.
#            color, name = full_name.split("_", 1)
#        else:
#            color, name = "N/A", full_name 
        name, color = parse_name_and_color(full_name, colors)
        description = item_info_box.find("div", {"id": "product-details-tab-description"})
        if description: 
            description = description.text.strip().replace("\n", " ")
        # category is the next-to-last node in breadcrumb
        breadcrumb = soup.find("ul", class_="breadcrumb")
        categories = [t for t in (t.text.strip() for t in breadcrumb.children) if t]
        category, parent_categories = categories[-2], categories[:-2]
        if name in sanitize(category):
            # the current sub-category belong to a single type of item; discard it & use a higher one.
            category, parent_categories = categories[-3], categories[:-3]
        data[full_name] = item = {"name": name, "color": color, "image": image_source, "link": url, "category": category, "categories": parent_categories, "description": description}
        generic.logger.info("Link {} has item ({} | {}). Append & continuing. Total items atm [{:d}]".format(url, name, color, len(data)))
    except Exception as e:
        generic.logger.error("Parsing link {} has error: {}\n, (possible) item skipped.".format(url, traceback.format_exc()))

def autocategorize(data, colors: list=None, collapse_threshold: int=20):
    # convert data to matching category. This mostly help with generating md in per-category sections 
    categorized = dict()
    for k, d in data.items():
        category = d["category"]
        if colors and any(clr in category for clr in colors):
            # category is wrong; and can't really be arsed to reverse-search them.
            category = "Other"
        if category not in categorized:
            categorized[category] = dict()
        # convert to a name/color key pair to match associating items.
        true_name, color = new_key = d["name"], d["color"]
        categorized[category][new_key] = d
    for k, length in list(sorted( ((k, len(v)) for k, v in categorized.items()), key=lambda i: i[-1]):
        # category from low -> high; attempt to merge up to any parent section if they exists.
        # this may automerge parent that are too small as well; but eh. 
        if length > collapse_threshold:
            # from here onward its more than the threshold; break out 
            break 
        # get a random item; traverse backward through its parent & stop at an existing category. If cannot find; either leave it as-is, or add into other. For now let's just leave it 
        item = next(iter(categorized[k].values()))
        parent_categories_backward = item["categories"][::-1]
        transfered = False
        for cat in parent_categories:
            if cat in categorized:
                # pop the child & add it into the parent
                categorized[cat].update(categorized.pop(k))
                transfered = True
                break
        # if want to move to other; have condition to do transfering -> Other here instead.

    return categorized

def generate_md(data):
    """Tabled basing on color. This is exclusively a minifigcat thing, but should make viewing stuff much nicer."""
    sections = ["# LEGO-Compatible: MinifigCat\n"]
    def create_image_if_any(name, color, checker_dict):
        # check if (name, color) exist in checker_dict; if true, output the matching image+href; if not, leave blank
        exist_data = checker_dict.get((name, color), None)
        if exist_data:
            image = exist_data["image"]
            if not image.startswith("http") and image.startswith("//"):
                # special case happening to image
                image = "https:" + image 
            if exist_data["description"]:
                description = "title='{:s}'".format(exist_data["description"].strip().replace("\r", "").replace("\n", " ").replace("'", ""))
            else:
                description = ""
            image_str = "<img src='{:s}' width=100 {:s}></src>".format(image, description)
            linked_image_str = "<a href='{:s}'>{:s}</a>".format(exist_data["link"], image_str)
            return linked_image_str
        else:
            return "   " # blank
    for catname, catdata in data.items():
        category_header = "## {:s}\n".format(catname)
        rows = list(set((name for name, color in catdata.keys())))
        columns = list(set((color for name, color in catdata.keys())))
        # generate header
        table_header = "|" + "|".join(["Item"] + columns) + "|"
        table_separator = "|" + "|".join([":----"] + [":---:"] * len(columns)) + "|"
        section = [category_header, table_header, table_separator]
        # generate data row
        for item_name in rows:
            row = "|" + "|".join([item_name] + [create_image_if_any(item_name, color, catdata) for color in columns]) + "|"
            section.append(row)
        # convert to string & put into list of sections
        sections.append("\n".join(section))
    return "\n\n".join(sections)
    
if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO if "log" not in sys.argv else logging.DEBUG)
    if len(sys.argv) < 2:
        print("Must be {script} full|crawl|convert")
        sys.exit(-1)
    arg = sys.argv[1]

    all_colors = get_colors()
    print("Found all designated colors: {}".format(all_colors))
    if arg == "test":
        full_data = dict()
        test_url = "https://www.minifigcat.com/shop/Black_MN00-Ammo-backpack.html?category_id=452"
        test_soup = generic.get_parsed(test_url)
        print(test_soup)
        process_data(test_soup, url=test_url, data=full_data, colors=all_colors)
        print(full_data)
        md = generate_md(autocategorize(full_data))
        print(md)
        sys.exit()
    
    if arg in ("full", "crawl"):
        start_url = APPEND_DOMAIN # use the default shop link too
        full_data = dict()
        process_data_fn = partial(process_data, data=full_data, colors=all_colors)
        # must crawl in single session; due to full_data being transient variable.
        # TODO reload the json file & append to it?
        return_code = generic.perform_crawl(start_url, "test/minifigcat.txt", process_data_fn=process_data_fn, neighbor_link_fn=get_neighbor_links, retrieve_interval=(0.1, 0.3))
        with io.open("test/minifigcat.json", "w", encoding="utf-8") as btf:
            json.dump(full_data, btf, indent=2)
        print("Crawled data.")
    else:
        with io.open("test/minifigcat.json", "r", encoding="utf-8") as btf:
            full_data = json.load(btf)
        print("Loaded data.")
    if arg in ("full", "convert"):
        # data should already been categorized.
        md_text = generate_md(autocategorize(full_data, colors=all_colors))
        with io.open("data/lessons/minifigcat.md", "w", encoding="utf-8") as mf:
            mf.write(md_text)
        print("Formatting data to .md file.")
    print("Done")
    # Test first 

