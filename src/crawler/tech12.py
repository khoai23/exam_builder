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

CATEGORY_SUFFIX = {
        "ngu-van": "Ngữ văn", 
        "toan": "Toán", 
        "vat-ly": "Vật lý", 
        "sinh-hoc": "Sinh học", 
        "tieng-anh": "Tiếng Anh", 
        "lich-su": "Lịch Sử", 
        "hoa-hoc": "Hóa học", 
        "gdcd": "GDCD", 
        "dia-ly": "Địa lý"
}
CATEGORY_PREFIX = {
    "-10": "Lớp 10",
    "-11": "Lớp 11",
    "-12": "Lớp 12",
}
TAG = {
    "thptqg": "Đề THPT QG",
    "thpt-quoc-gia": "Đề THPT QG",
    "chuyen-de": "Chuyên",
    "canh-dieu": "CD",
    "ket-noi-tri-thuc": "KNTT",
    "chan-troi-sang-tao": "CTST",
    "de-bai": "SBT"
}
def parse_tag(question, url):
    # deduce appropriate question & tag by url variation 
    url = url.lower()
    # category:
    cat_suffix = next((cat for cat in CATEGORY_SUFFIX if cat in url), None)
    if(cat_suffix is not None):
        cat_prefix = next((cat for cat in CATEGORY_PREFIX if cat in url), None)
        if(cat_prefix is not None):
            category = CATEGORY_SUFFIX[cat_suffix] + " " + CATEGORY_PREFIX[cat_prefix]
        else:
            category = CATEGORY_SUFFIX[cat_suffix]
        question["category"] = category 
    # tags, de-duplicated & sorted
    tags = list(sorted({TAG[t] for t in TAG if t in url}))
    if tags:
        question["tag"] = tags
    return question
        
REMOVAL_CUE = re.compile(r"^(A\.|B\.|C\.|D\.|Câu \d+:)")
COUNT = {None: 0}
SINGLE_QUESTION_CUE = {"Câu": "question", "A.": "answer1", "B.": "answer2", "C.": "answer3", "D.": "answer4"}
CORRECT_ID_CUE = "Đáp án"
def process_data(soup, url=None, writer=None, driver=None, wait_after_click: float=0.5, ignore_failed_row: bool=True):
    try:
        if(soup.find("div", class_="kqua")):
            # can be parsed as a full exam, start attempt
            driver.get(url)
            generic.driver_wait_element_clickable(driver, 40, (generic.By.CLASS_NAME, "kqua"))
            kqua_button = driver.find_element(generic.By.CLASS_NAME, "kqua")
            #kqua_button.click()
            driver.execute_script("arguments[0].click();", kqua_button) # trigger by javascript to prevent nonsense
            time.sleep(wait_after_click)
            result_soup = generic.get_parsed_from_str(driver.page_source)
            # first, parse the quiz. Use the original soup to keep any mathjax sequence intact
            quiz_table = list(sorted(soup.find_all("div", id="accordionExample"), key=lambda it: len(it.findChildren(recursive=False)) ))[-1] # quiz_table is chosen to be the one with the largest concentration of children 
            table_length = len(quiz_table.findChildren(recursive=False))
            # TODO what if data is splitted between multiple
            result_table = [t for t in result_soup.find_all("div", id="accordionExample") if len(t.findChildren(recursive=False)) == table_length][0] 
            generic.logger.debug("Found matching table set with {:d} subitem".format(table_length))
            questions, current_question = [], None
            for child, result in zip(quiz_table.findChildren(recursive=False), result_table.findChildren(recursive=False)):
                if child.name in ("p", "h6", "h5", "div"): # allow initiation as header and div as well
                    if(current_question is None):
                        # if paragraph & no new question, append new question 
                        current_question = dict(question=re.sub(REMOVAL_CUE, "", child.text.replace("\xa0", "")).strip(), url=url)
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
                    current_question["question"] += "\n" + " ".join( "|||{}|||".format(img["src"]) for img in child.find_all("img", src=True))
            # once all questions are parsed, time to write into writer 
            for i, q in enumerate(questions):
                q = parse_tag(q, url)
                try:
                    writer.writerow(q)
                except Exception as e:
                    if ignore_failed_row:
                        generic.logger.warning("Row ({}){} has failed, skipping. Error: \n{}".format(i, q, traceback.format_exc()))
                    else:
                        raise e
            generic.logger.info("Updated massed {} questions to {}.".format(len(questions), COUNT[None]))
            COUNT[None] += len(questions)
        elif(soup.find("div", class_="trac_nghiem")):
            # find all non-accordion sub-child and parse accordingly 
            # build fixed mould
            question = parse_tag(dict(url=url), url)
            main_panel = soup.find("div", class_="trac_nghiem")
            current_field = None
            for field in main_panel.find_all("p"):
#                print(field)
#                if field.name == "h2" or field.get("id") == "headingOne":
#                    # sign of extra useless data; remove 
#                    continue
                if field.find("p"):
                    # has nested paragraph; ignore 
                    continue
                text = field.text.replace("\xa0", "").strip()
                if text == "":
                    # no valid text; ignore 
                    continue
                if(text.startswith(CORRECT_ID_CUE)):
                    # parse the correct id using a simple search 
                    for c in text[::-1]: # parse in reverse
                        if c in "ABCD":
                            question["correct_id"] = "ABCD".index(c) + 1
                            break 
                    assert "correct_id" in question, "correct_id field cannot be parsed: {}".format(text)
                    # any subsequent field is explanation 
                    current_field = "explanation"
                else:
                    # check with all other possible text 
#                    print(text)
                    current_field = next((SINGLE_QUESTION_CUE[c] for c in SINGLE_QUESTION_CUE if text.startswith(c)), None) or current_field 
#                    print("->", current_field)
                    # add in; 
                    if current_field in question:
                        question[current_field] = question[current_field] + "\n" + text 
                    else:
                        question[current_field] = re.sub(REMOVAL_CUE, "", text)
            # once written, commit the appropriate category/tag 
            question = parse_tag(question, url)
            writer.writerow(question)
            # log out the appropriate file
            generic.logger.info("Updated single question to {}".format(COUNT[None]))
            COUNT[None] += 1
    except Exception as e:
        generic.logger.error("Parsing link {} has error: {}\n, quiz skipped.".format(url, traceback.format_exc()))
    

if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO)
    start_url = "https://tech12h.com/de-bai/y-nao-sau-day-la-boi-canh-lich-su-tac-dong-den-cuoc-cach-mang-cong-nghiep-lan-thu-ba.html"
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
