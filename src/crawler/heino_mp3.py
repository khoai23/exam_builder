import io
import requests
from bs4 import BeautifulSoup 
from urllib.parse import unquote_plus

from .generic import get_neighbor_links

raise NotImplementedError("Need signup or whatever the hell.")

APPEND_DOMAIN = "http://8390.unknownsecret.info"
FILTER_KEY = {".."}
INCLUDE_KEY = {"Heino"}

if __name__ == "__main__":
    import sys, os
    crawl_file = "test/heino_mp3.txt"
    if "crawl" in sys.argv:
        print("Run crawling mode, downloading to {}".format(crawl_file))
        start_link = "http://8390.unknownsecret.info/mp3/Heino"
        queue = [start_link] 
        passed = {start_link}
        valid_mp3 = []
        while len(queue) > 0:
            current = queue.pop(0)
            print("Parsing {}".format(current))
            links = get_neighbor_links(current, include_key=INCLUDE_KEY, filter_key=FILTER_KEY, append_domain=APPEND_DOMAIN)
            for l in links:
                if l in passed:
                    continue # link already found somewhere
                else:
                    passed.add(l)
                    if l.endswith(".mp3"):
                        # is mp3 link, put to valid_mp3
                        print("New mp3 `{}`, add to download list.".format(l))
                        valid_mp3.append(l)
                    else:
                        # is possible expandable, put to queue 
                        print("New link `{}`, add to queue.".format(l))
                        queue.append(l)
        # write everything to crawl_file
        with io.open(crawl_file, "w", encoding="utf-8") as cf:
            cf.write("\n".join(valid_mp3))
    elif "download" in sys.argv:
        folder = "test/heino_mp3"
        with io.open(crawl_file, "r", encoding="utf-8") as cf:
            raws = cf.readlines()
        links = [l.strip() for l in raws]
        for l in links:
            filename = unquote_plus(l.split("/")[-1])
            doc = requests.get(l)
            with io.open(os.path.join(folder, filename), "wb") as mf:
                print("Writing {} bytes to {}".format(len(doc.content), filename))
                mf.write(doc.content)
    else:
        print("Script must be run as: python {script} [download|crawl]")

