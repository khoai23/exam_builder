import io, os, csv, time, re
import traceback
from functools import partial

from src.crawler import generic

INCLUDE_KEY = {"bai-hoc", "trac-nghiem"}
FILTER_KEY = {".."}
APPEND_DOMAIN = "https://tech12h.com"

def get_neighbor_links(soup_or_url, include_key=INCLUDE_KEY, filter_key=FILTER_KEY, append_domain=APPEND_DOMAIN):
    return generic.get_neighbor_links(soup_or_url, filter_key=filter_key, append_domain=append_domain)
    
def perform_crawl(*args, neighbor_link_fn=get_neighbor_links, **kwargs):
    return generic.perform_crawl(*args, neighbor_link_fn=neighbor_link_fn, **kwargs)

REMOVAL_CUE = re.compile(r"^(A\.|B\.|C\.|D\.|Câu \d+:)")
COUNT = {None: 0}
def process_data(soup, url=None, writer=None, driver=None, wait_after_click=0.5):
    try:
        if(soup.find("div", class_="kqua")):
            # can be parsed, start attempt
            driver.get(url)
            generic.driver_wait_element_clickable(driver, 40, (generic.By.CLASS_NAME, "kqua"))
            kqua_button = driver.find_element(generic.By.CLASS_NAME, "kqua")
            #kqua_button.click()
            driver.execute_script("arguments[0].click();", kqua_button) # trigger by javascript to prevent nonsense
            time.sleep(wait_after_click)
            result_soup = generic.get_parsed_from_str(driver.page_source)
            # first, parse the quiz. Use the original soup to keep any mathjax sequence intact
            quiz_table, result_table = soup.find("div", id="accordionExample"), result_soup.find("div", id="accordionExample")
            questions, current_question = [], None
            for child, result in zip(quiz_table.findChildren(recursive=False), result_table.findChildren(recursive=False)):
                if child.name == "p":
                    if(current_question is None):
                        # if paragraph & no new question, append new question 
                        current_question = dict(question=re.sub(REMOVAL_CUE, "", child.text.replace("\xa0", "")).strip())
                    else:
                        # if existed question, join in
                        current_question["question"] += child.text.replace("\xa0", "").strip()
                elif child.name == "ul":
                    # if ul, append children (li) as answer 
                    for i, (a, r) in enumerate(zip(child.findChildren(recursive=False), result.findChildren(recursive=False))):
                        current_question["answer{}".format(i+1)] = re.sub(REMOVAL_CUE, "", a.text.replace("\xa0", "")).strip()
                        # the li in result with a h6 header means the correct index 
                        if(r.find("h6")):
                            current_question["correct_id"] = i+1 
                    # after done; load them into the questions list 
                    questions.append(current_question)
                    current_question = None
                elif(current_question is None):
                    # weird result (item directly after ul/empty), ignore
                    generic.logger.warning("Invalid child type for start of question: ({}){} - {}. Ignored".format(child.name, child, result))
                else:
                    # if anything else; load them into current question 
                    if(child.name == "table"):
                        # for table; assume it has a single oriented tbody; load them.
                        join_rows = lambda tr: "\t".join([td.text.replace("\xa0", "").strip() for td in tr.findChildren(recursive=False)])
                        join_table = lambda tbody: "\n".join([join_rows(tr) for tr in tbody.findChildren(recursive=False)])
                        current_question["question"] += "\n" + join_table(child.find("tbody"))
                    elif(child.name == "ol"):
                        # for ordered list, append necessary order 
                        current_question["question"] += "\n" + "\n".join(["{:d}. {}".format(i+1, item.text.replace("\xa0", "").strip()) for i, item in enumerate(child.findChildren(recursive=False))])
                    else:
                        # for anything else; print warning 
                        generic.logger.warning("Unrecognized child type {} for question; will append raw text.".format(child.name))
                        current_question["question"] += "\n" + child.text.replace("\xa0", "").strip()
    #            print(child.name, current_question)
                # also export all images found in specific format 
                if(child.find("img")):
                    current_question["question"] += "\n" + " ".join( "|||{}|||".format(img["src"]) for img in child.find("img", src=True))
            # once all questions are parsed, time to write into writer 
            for q in questions:
                writer.writerow(q)
            generic.logger.info("Updated {} questions to {}.".format(COUNT[None], len(questions)))
            COUNT[None] += len(questions)
    except Exception as e:
        generic.logger.error("Parsing link {} has error: {}\n, quiz skipped.".format(url, traceback.format_exc()))
    

if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO)
    start_url = "https://tech12h.com/bai-hoc/trac-nghiem-tin-hoc-10-canh-dieu-bai-2-bien-phep-gan-va-bieu-thuc-so-hoc.html"
    DUMP_PATH = "test/tech12.pkl"
    if(len(sys.argv) > 2):
        target_location = sys.argv[1]
    else:
        print("Using default: test/tech12.txt")
        target_location = "test/tech12.txt"
    csv_path = "test/tech12.csv"
    file_existed = os.path.isfile(csv_path)
    with io.open(csv_path, "a" if file_existed else "w", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["question", "answer1", "answer2", "answer3", "answer4", "correct_id", "category", "tag", "special", "variable_limitation", "explanation", "url"], dialect="unix")
        if(not file_existed):
            writer.writeheader()
        with generic.acquire_driver() as driver:
#            prior_soup = generic.get_parsed(start_url)
#            process_data(prior_soup, url=start_url, writer=writer, driver=driver)
            process_data_fn = partial(process_data, writer=writer, driver=driver)
            return_code = perform_crawl(start_url, target_location, process_data_fn=process_data_fn, recovery_dump_path=DUMP_PATH, prefer_cue="trac-nghiem-", retrieve_interval=(0.1, 0.3))
