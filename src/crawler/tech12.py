import io, os, csv, time, re
import traceback
from functools import partial

from src.crawler import generic

INCLUDE_KEY = {"bai-hoc", "trac-nghiem", "de-bai"}
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
        "vat-li": "Vật lý", 
        "sinh-hoc": "Sinh học", 
        "tieng-anh": "Tiếng Anh", 
        "lich-su": "Lịch Sử", 
        "hoa-hoc": "Hóa học", 
        "hoa": "Hóa học", 
        "gdcd": "GDCD", 
        "dia-ly": "Địa lý",
        "dia-li": "Địa lý",
        "tin-hoc": "Tin học",
        "cong-nghe": "Công nghệ",
        "hdtn": "Hoạt động trải nghiệm",
        "hoat-dong-trai-nghiem": "Hoạt động trải nghiệm",
        "tkcn": "Thiết kế công nghệ",
        "tu-nhien-va-xa-hoi": "Tự nhiên & Xã hội",
        "tnxh": "Tự nhiên & Xã hội",
        "ktpl": "Kinh tế & Pháp luật",
        "kinh-te-va-phap-luat": "Kinh tế & Pháp luật",
        "tieng-viet": "Tiếng Việt",
        "hinh-hoc": "Toán",
        "dao-duc": "GDCD"
}
CATEGORY_PREFIX = { # deprecated
    "-7": "Lớp 7",
    "-8": "Lớp 8",
    "-9": "Lớp 9",
    "-10": "Lớp 10",
    "-11": "Lớp 11",
    "-12": "Lớp 12",
}
CATEGORY = {k1+k2: v1+" "+v2 for k2, v2 in (("-{:d}".format(i), "Lớp {:d}".format(i)) for i in range(1, 13)) for k1, v1 in CATEGORY_SUFFIX.items()}
TAG = {
    "thptqg": "Đề THPT QG",
    "thpt-quoc-gia": "Đề THPT QG",
    "chuyen-de": "Chuyên",
    "canh-dieu": "CD",
    "ket-noi": "KNTT", # most should be ket-noi-tri-thuc
    "chan-troi": "CTST", # most should be chan-troi-sang-tao
    "de-bai": "SBT",
    "ky-ii": "HKII",
    "ky-i-": "HKI",
    "ky-i.": "HKI", # extra score/separator to prevent mismatch with HKII
}
def parse_tag(question, url):
    # deduce appropriate question & tag by url variation 
    url = url.lower()
    # category:
    category = next((cat for cat in CATEGORY if cat in url), None)
    if category is None:
        # attempt fallback with corresponding suffixes 
        category = next((cat for cat in CATEGORY_SUFFIX if cat in url), None)
    if category is not None:
        # if exist, put into the question 
        question["category"] = category
#    cat_suffix = next((cat for cat in CATEGORY_SUFFIX if cat in url), None)
#    if(cat_suffix is not None):
#        cat_prefix = next((cat for cat in CATEGORY_PREFIX if cat in url), None)
#        if(cat_prefix is not None):
#            category = CATEGORY_SUFFIX[cat_suffix] + " " + CATEGORY_PREFIX[cat_prefix]
#        else:
#            category = CATEGORY_SUFFIX[cat_suffix]
#        question["category"] = category 
    # tags, de-duplicated & sorted
    tags = list(sorted({TAG[t] for t in TAG if t in url}))
    if tags:
        question["tag"] = tags
    return question
        
REMOVAL_CUE = re.compile(r"^(A\.|B\.|C\.|D\.|E\.|F\.|G\.|H\.|Câu \d+:)")
COUNT = {None: 0}
SINGLE_QUESTION_CUE = {"Câu": "question", "A.": "answer1", "B.": "answer2", "C.": "answer3", "D.": "answer4", "E.": "answer5", "F.": "answer6", "G.": "answer7", "H.": "answer8"}
CORRECT_ID_CUE = "Đáp án"
def process_data(soup, url=None, writer=None, driver=None, wait_after_click: float=0.5, ignore_failed_row: bool=True, allow_extra_answers: bool=True):
    if allow_extra_answers: # allow correct_id parsing above it default (4)
        ANSWER_CUE = "ABCDEFGH"
    else:
        ANSWER_CUE = "ABCD"
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
#            print("All valid 'accordionExample' div: ", [len(d.findChildren(recursive=False)) for d in soup.find_all("div", id="accordionExample")], [len(d.findChildren(recursive=False)) for d in result_soup.find_all("div", id="accordionExample")])
            # first, parse the quiz. Use the original soup to keep any mathjax sequence intact
            quiz_table = list(sorted(soup.find_all("div", id="accordionExample"), key=lambda it: len(it.findChildren(recursive=False)) ))[-1] # quiz_table is chosen to be the one with the largest concentration of children 
            # also auto-clear google-autoad
            quiz_table = [c for c in quiz_table.findChildren(recursive=False) if "google-auto-placed" not in c.attrs.get("class", "")]
            table_length = len(quiz_table)
            # TODO what if data is splitted between multiple
            try:
                results = (t.findChildren(recursive=False) for t in result_soup.find_all("div", id="accordionExample"))
                valid = ([c for c in r if "google-auto-placed" not in c.attrs.get("class", "")] for r in results)
                result_table = [v for v in valid if len(v) == table_length][0]
            except IndexError as e:
                # mismatched render; find the closest result_table & print them to the console 
                results = (t.findChildren(recursive=False) for t in result_soup.find_all("div", id="accordionExample"))
                valid = ([c for c in r if "google-auto-placed" not in c.attrs.get("class", "")] for r in results)
                closest = list(sorted(valid, key=lambda it: abs(len(it) - table_length)))[0]
                # pad either to the closest 
                if len(closest) > len(quiz_table):
                    quiz_table.extend([None] * (len(closest) - len(quiz_table)))
                else:
                    closest.extend([None] * (len(quiz_table) - len(closest)))
                print("Mismatch found; associating cells:")
                for i, (tabcell, rescell) in enumerate(zip(closest, quiz_table)):
                    print("====CELL {}====".format(i))
                    print(tabcell)
                    print("---------------")
                    print(rescell)
                print("\n\n") # extra spacing
                # raise error anyway 
                raise e
            generic.logger.debug("Found matching table set with {:d} subitem".format(table_length))
            questions, current_question = [], None
            for child, result in zip(quiz_table, result_table):
                if child.name in ("p", "h6", "h5", "div"): # allow initiation as header and div as well
                    if(current_question is None):
                        # if paragraph & no new question, append new question 
                        current_question = dict(question=re.sub(REMOVAL_CUE, "", child.text.replace("\xa0", "")).strip(), url=url)
                    else:
                        # if existed question, join in
                        current_question["question"] += child.text.replace("\xa0", "").strip()
                elif child.name == "ul":
                    # if ul, append children (li) as answer 
                    # TODO detected empty li row; throw them away
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
                if q.get("tag", None): # if exist valid tag set, join them
                    q["tag"] = ",".join(q["tag"])
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
                        if c in ANSWER_CUE:
                            question["correct_id"] = ANSWER_CUE.index(c) + 1
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
            question["tag"] = ", ".join(question["tag"] + ["single"]) if question.get("tag", None) else "single" # also add `single` tag
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
        writer = csv.DictWriter(cf, fieldnames=["question", "answer1", "answer2", "answer3", "answer4", "correct_id", "category", "tag", "special", "variable_limitation", "explanation", "url"] + ["answer5", "answer6", "answer7", "answer8"], dialect="unix")
        if(not file_existed):
            writer.writeheader()
        with generic.acquire_driver() as driver:
#            prior_soup = generic.get_parsed(start_url)
#            process_data(prior_soup, url=start_url, writer=writer, driver=driver)
            process_data_fn = partial(process_data, writer=writer, driver=driver)
            return_code = perform_crawl(start_url, target_location, process_data_fn=process_data_fn, recovery_dump_path=DUMP_PATH, prefer_cue="trac-nghiem-", retrieve_interval=(0.1, 0.3))
