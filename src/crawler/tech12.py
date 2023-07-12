from src.crawler import generic

INCLUDE_KEY = {"bai-hoc", "trac-nghiem"}
FILTER_KEY = {"..", ".jsp"}
APPEND_DOMAIN = "https://tech12h.com"

def get_neighbor_links(soup_or_url, include_key=INCLUDE_KEY, filter_key=FILTER_KEY, append_domain=APPEND_DOMAIN):
    return generic.get_neighbor_links(soup_or_url, filter_key=filter_key, append_domain=append_domain)
    
def perform_crawl(*args, neighbor_link_fn=get_neighbor_links, **kwargs):
    return generic.perform_crawl(*args, neighbor_link_fn=neighbor_link_fn, **kwargs)

if __name__ == "__main__":
    import sys
    start_url = "https://tech12h.com/bai-hoc/trac-nghiem-tin-hoc-10-canh-dieu-bai-2-bien-phep-gan-va-bieu-thuc-so-hoc.html"
    DUMP_PATH = "test/tech12.pkl"
    if(len(sys.argv) > 2):
        target_location = sys.argv[1]
    else:
        print("Using default: test/tech12.txt")
        target_location = "test/tech12.txt"
    return perform_crawl(start_url, target_location, recovery_dump_path=DUMP_PATH)

