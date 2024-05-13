import sys, random, time, io, os 
import pickle 
import traceback
import requests
from bs4 import BeautifulSoup

from typing import Union, Optional, Iterable

import logging 
logger = logging.getLogger(__name__)

"""Generic crawler, using a simple search using raw website"""

def get_parsed(url: str):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser");
    return soup 
    
def get_parsed_from_str(source_str: str):
    return BeautifulSoup(source_str, "html.parser")

def get_text_from_url(url: str):
    return get_parsed(url).text

def get_neighbor_links(soup_or_url, include_key=None, filter_key=None, append_domain=None, same_domain_only=True):
    if(isinstance(soup_or_url, str)):
        soup = get_parsed(soup_or_url)
    else:
        soup = soup_or_url
    links = (l["href"] for l in soup.find_all("a", href=True))
    included_links = (l for l in links if include_key is None or any((k in l for k in include_key)))
    filtered_links = (l for l in included_links if filter_key is None or all((k not in l for k in filter_key)))
    if(append_domain):
        # append only when missing;
        filtered_links = (append_domain + l if "https" not in l else l for l in filtered_links)
        if(same_domain_only):
            # filter away all external links
            filtered_links = (l for l in filtered_links if l.startswith(append_domain))
    return list(filtered_links)

def perform_crawl(start_url: Union[str, Iterable[str]], crawl_result_location: str, process_data_fn: Optional[callable]=None, neighbor_link_fn: Optional[callable]=get_neighbor_links, allow_keyboard_interrupt: bool=True, recovery_dump_path: str=None, retrieve_interval: tuple=(0.75, 0.25), delete_dump_after_done: bool=True, failed_get_incremental: float=10.0, prefer_cue: str=Optional[None]):
    """The main crawling mechanism. Will start with start_url, and attempt to scan all of them until all links are exhausted.
    crawl_result_location: when process completes, this will output all the pages that had been crawled to this.
    process_data_fn: if supplied, take and parse the "soup". Since data is already downloaded, this will save additional bandwidth.
    neighbor_link_fn: if supplied, can provide a different crawling mechanism when visit a link. The default is `get_neighbor_links` from here 
    allow_keyboard_interrupt: ignored for now, default to True.
    recovery_dump_path: if KeyboardInterrupt a process, the current data is dumped to this location to allow resuming whenever feels fit.
    retrieve_interval: base + variance; the process will wait [base-var; base+var] second before attempting the next link.
    delete_dump_after_done: if true, the recovery_dump_path will be cleared upon finishing everything.
    failed_get_incremental: with every nth failed access to a link, process will wait for n*inc second then try again.
    prefer_cue: if specified; crawled neighbors matching this will get prioritized to go first. Base with each question on page (e.g tracnghiem_net) can use this to minimize size of the queue 
    """
    # get_neighbor_links(start_url)
    if(os.path.isfile(recovery_dump_path)):
        with io.open(recovery_dump_path, "rb") as df:
            passed, queue = pickle.load(df)
            passed = set(passed)
            queue = set(queue) # backward compatibility; remove later
            if prefer_cue:
                queue = [l for l in queue if prefer_cue in l] + [l for l in queue if prefer_cue not in l]
            else:
                queue = list(queue)
    else:
        passed = {start_url} if isinstance(start_url, str) else set(start_url)
        queue = [start_url] if isinstance(start_url, str) else list(start_url)
    # usable_links = []
    incremental_wait_on_failed_resolve = 0
    retrieve_base, retrieve_variance = retrieve_interval if retrieve_interval else (0.0, 0.0)
    failed_run = False 
    try:
        while len(queue) > 0:
            if(not failed_run):
                current_url = queue.pop(0)
                passed.add(current_url);
                logger.info("Checking: " + current_url)
                #if("bai-hoc" in current_url and "trac-nghiem" in current_url):
                # usable_links.append(current_url)
            else:
                logger.info("Re-checking: " + current_url)
                # try to eject all links that are non-html 
                extension_if_any = current_url.split(".")[-1]
                if(len(extension_if_any) <= 4 and extension_if_any not in ("html", "xml")):
                    logger.warning("Link {} is very likely to be a file; ignored. Check & verify if possible.".format(current_url))
                    failed_run = False
                    continue
            try:
                # get_neighbor_links(current_url, include_key=include_key, filter_key=filter_key)
                soup = get_parsed(current_url)
                if(process_data_fn):
                    process_data_fn(soup, url=current_url)
                other_links = neighbor_link_fn(soup)
                failed_run = False
            except Exception as e:
                if(not failed_run and recovery_dump_path):
                    # first entry into the error; save into dump to be restarted (if needed)
                    with io.open(recovery_dump_path, "wb") as df:
                        pickle.dump((passed, queue), df)
                # wait incrementally before retrying; reenable a flag to reuse the current_url
                incremental_wait_on_failed_resolve += failed_get_incremental / 2 + random.random() * failed_get_incremental / 2
                logger.info("Encountered error: {}\nwaiting for {:.2f}s".format(traceback.format_exc(), incremental_wait_on_failed_resolve))
                time.sleep(incremental_wait_on_failed_resolve)
                failed_run = True
                continue
            valid_queue_links = list(set(l for l in other_links if l not in passed)) # prevent duplicate links
            if(valid_queue_links):
                logger.debug("Adding links:\n" + "\n".join(valid_queue_links))
#                logger.debug("Pre-update: passed [{}], queue [{}]".format(len(passed), len(queue)))
#                preval = len(passed), len(queue)
                passed.update(valid_queue_links)
                if(prefer_cue):
                    preferred = (l for l in valid_queue_links if prefer_cue in l)
                    not_preferred = [l for l in valid_queue_links if prefer_cue not in l]
                    queue[0:0] = preferred; queue.extend(not_preferred)
                else:
                    queue.extend(valid_queue_links) # append all at back
#                logger.debug("Post-update: passed [{}], queue [{}]".format(len(passed), len(queue)))
#                postval = len(passed), len(queue)
#                assert postval[0] - preval[0] == postval[1] - preval[1], "Issue updating: passed/queue going {} => {}, {} link is corrupted".format(preval, postval, len(valid_queue_links))
            else:
                logger.debug("No valid link to add; continuing.")
            random_wait = retrieve_base + random.random() * retrieve_variance
            logger.info("Waiting for {:.2f}s; passed [{:d}], currently left in queue [{:d}]".format(random_wait, len(passed), len(queue)))
            if(random_wait > 0):
                time.sleep(random_wait)
            # also reset the incremental wait to 0
            incremental_wait_on_failed_resolve = 0
    except KeyboardInterrupt:
        if(recovery_dump_path):
            logger.info("Dumping current run info at {}".format(recovery_dump_path))
            # first entry into the error; save into dump to be restarted (if needed)
            # re-input the last current_url 
            passed.remove(current_url)
            queue.insert(0, current_url)
            with io.open(recovery_dump_path, "wb") as df:
                pickle.dump((passed, queue), df)
        else:
            logger.warning("No dump path specified; this termination is NOT recoverable")
        # exit immediately
        return 1 # use for sys exit 
    logger.info("Finished crawling.")
    if(crawl_result_location and os.path.isfile(crawl_result_location)):
        base, extension = os.path.splitext(crawl_result_location)
        for i in range(1, 1000 + 1):
            crawl_result_location = base + "_{:d}".format(i) + extension
            if(not os.path.isfile(crawl_result_location)):
                logger.info("Found valid unused derivative: {}".format(crawl_result_location))
                break
        # this will override file 1000; but at that point it's your fault.
    with io.open(crawl_result_location, "w", encoding="utf-8") as resultfile:
        resultfile.write("\n".join(list(passed)))
    if(delete_dump_after_done and os.path.isfile(recovery_dump_path)):
        # if still have the dump path, throw it away
        os.remove(recovery_dump_path)
    return 0

def convert_crawled_dump(dumppath, targetpath, filter_key: set=None, start_key: str=None):
    """Crawled dump can be extracted to view all current link. Also can be further filtered by specific keyword"""
    with io.open(dumppath, "rb") as df:
        passed, _ = pickle.load(df)
    if(filter_key):
        passed = (p for p in passed if any((k in p for k in filter_key)))
    if(start_key):
        passed = (p for p in passed if p.startswith(start_key))
    with io.open(targetpath, "w", encoding="utf-8") as wf:
        wf.write("\n".join(passed))

"""Generic parser, using chrome in selenium to render javascript interaction."""
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
#import chromedriver_binary
def create_options():
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.binary = webdriver.firefox.firefox_binary.FirefoxBinary(r"C:\Program Files\Mozilla Firefox\firefox.exe")
    return options 
#print("Binary location: ", chromedriver_binary.chromedriver_filename)
# DRIVER = None
def get_driver():
#    if DRIVER is None:
    service = webdriver.firefox.service.Service(executable_path="src/crawler/bin/geckodriver.exe")
    driver = webdriver.Firefox(service=service, options=create_options())
    return driver

def close_driver(driver):
    if driver is not None:
        driver.quit()
#    DRIVER = None
    return driver

from contextlib import contextmanager
@contextmanager
def acquire_driver():
    """Same as generic get/close driver above; but using a context manager to ensure closure"""
    logger.info("Starting Selenium-Geckodriver..")
    driver = get_driver()
    logger.info("Driver started.")
    try:
        yield driver 
    finally:
        logger.info("Closing Selenium-Geckodriver.")
        close_driver(driver)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
def driver_wait_element_clickable(driver, duration: float, selector_args: tuple):
    # wait for the element to be clickable 
    # duration specify the maximum wait time; selector args targetting required item
    WebDriverWait(driver, duration).until(expected_conditions.element_to_be_clickable(selector_args))

if __name__ == "__main__":
#    link = "https://tracnghiem.net/de-thi/cau-hoi-co-su-khac-nhau-ve-mau-da-giua-cac-chung-toc-la-do-dau-149980.html"
#    with acquire_driver() as driver:
#        # disable the MathJax domain 
#        driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.2"]})
#        driver.get(link)
#        driver.execute_script("onSelectAnswer('0')") # this will always be a wrong answer 
#        driver.execute_script("showAnswer()")  # this will always trigger showing the 
#        right_answer_box = driver.find_element(By.CLASS_NAME, "right-answer")
#        print("Right answer: {}".format(right_answer_box.text))
#
#if False:
    logging.basicConfig(level=logging.INFO)
    if(len(sys.argv) < 2):
        logger.warning("Script must be run as {script} [dump path] [..additional filter arg]")
    else:
        dumppath, *filter_key = sys.argv[1:]
        if len(filter_key) == 0:
            filter_key = None
        base, ext = os.path.splitext(dumppath)
        if(ext != ".txt"):
            # dump in pkl/whatever the hell; use txt 
            targetpath = base + ".txt"
        else:
            # dump in text; add additional suffix 
            targetpath = base + "_links" + ext 
        convert_crawled_dump(dumppath, targetpath, filter_key=filter_key)
