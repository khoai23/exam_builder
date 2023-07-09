import requests
from bs4 import BeautifulSoup

def get_parsed(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser");
    return soup 
    
def get_text_from_url(url):
    return getParsed(url).text
    
def get_neighbor_links(soup_or_url, filter_key={"bai-hoc", "trac-nghiem"}, append_domain="https://tech12h.com"):
    if(isinstance(soup_or_url, str)):
        soup = get_parsed(soup_or_url)
    else:
        soup = soup_or_url
    links = (l["href"] for l in soup.find_all("a", href=True))
    if(append_domain):
        # append only when 
        links = (append_domain + l if "https" not in l else l for l in links)
    filtered_links = [l for l in links if any((k in l for k in filter_key))]
    return filtered_links
    
if __name__ == "__main__":
    import sys, random, time, io, os
    start_url = "https://tech12h.com/bai-hoc/trac-nghiem-tin-hoc-10-canh-dieu-bai-2-bien-phep-gan-va-bieu-thuc-so-hoc.html"
    DUMP_PATH = "test/tech12.pkl"
    # get_neighbor_links(start_url)
    if(os.path.isfile(DUMP_PATH)):
        with io.open(DUMP_PATH, "rb") as df:
            passed, queue = pickle.load(df)
            passed = set(passed)
            queue = list(queue)
    else:
        passed = {start_url}
        queue = [start_url]
    # usable_links = []
    incremental_wait_on_failed_resolve = 0
    failed_run = False
    if len(sys.argv) > 1:
        linkfile = io.open(sys.argv[1], "a", encoding="utf-8")
        #    linkfile.write("\n".join(usable_links))
        print("Ready to write result to: " + sys.argv[1])
    else:
        linkfile = None
    while len(queue) > 0:
        if(not failed_run):
            current_url = queue.pop(0)
            passed.add(current_url);
            print("Checking: " + current_url)
            #if("bai-hoc" in current_url and "trac-nghiem" in current_url):
            # usable_links.append(current_url)
            if(linkfile is not None):
                linkfile.write(current_url + "\n")
        else:
            print("Re-checking: " + current_url)
        try:
            other_links = get_neighbor_links(current_url, filter_key={"bai-hoc", "trac-nghiem"})
            failed_run = False
        except Exception as e:
            if(not failed_run):
                # first entry into the error; save into dump to be restarted (if needed)
                import pickle
                with io.open(DUMP_PATH, "wb") as df:
                    pickle.dump((passed, queue), df)
            # wait incrementally before retrying; reenable a flag to reuse the current_url
            incremental_wait_on_failed_resolve += 1.0 + random.random() * 9.0
            print("Encountered error: {}\nwaiting for {:.2f}s".format(sys.exc_info()[-1], incremental_wait_on_failed_resolve))
            time.sleep(incremental_wait_on_failed_resolve)
            failed_run = True
            continue
        valid_queue_links = [l for l in other_links if l not in passed]
        if(valid_queue_links):
            print("Adding links:\n" + "\n".join(valid_queue_links))
            passed.update(valid_queue_links)
            queue.extend(valid_queue_links)
        else:
            print("No valid link to add; continuing.")
        random_wait = random.random() * 4.0 + 1.0
        print("Waiting for {:.2f}s; passed [{:d}], currently left in queue [{:d}]".format(random_wait, len(passed), len(queue)))
        time.sleep(random_wait)
        # also reset the incremental wait to 0
        incremental_wait_on_failed_resolve = 0
    print("Finished crawling.")
    if(os.path.isfile(DUMP_PATH)):
        # if still have the dump path, throw it away
        os.remove(DUMP_PATH)
    if(linkfile is not None):
        linkfile.close()