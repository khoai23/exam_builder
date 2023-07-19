import io, os, csv, re 
import traceback
from functools import partial

from src.crawler import generic

INCLUDE_KEY = {"bai-hoc", "trac-nghiem", "de-kiem-tra"}
FILTER_KEY = {"..", ".jsp", "dang-nhap", "void"}
APPEND_DOMAIN = "https://tracnghiem.net"

def get_neighbor_links(soup_or_url, include_key=INCLUDE_KEY, filter_key=FILTER_KEY, append_domain=APPEND_DOMAIN):
    return generic.get_neighbor_links(soup_or_url, filter_key=filter_key, append_domain=append_domain)
    
def perform_crawl(*args, neighbor_link_fn=get_neighbor_links, **kwargs):
    return generic.perform_crawl(*args, neighbor_link_fn=neighbor_link_fn, **kwargs)

_CORRECT_NAME = {"A": 1, "B": 2, "C": 3, "D": 4}
EXPLANATION_TRIM_CUE = "Chọn đáp án"
COUNTER = {None: 0}
def process_data(soup, url=None, writer=None, keep_partial_question=True):
    """Receive the necessary data and write it to a csv."""
    # print(soup)
    try:
        question = soup.find("h1", class_="title28Bold")
        if(question is not None):
            # check if exist any image in question; if yes, append it in the question itself
            if(question.find("img")):
                generic.logger.debug("Question has image, currently append to the end of text. TODO better positioning")
                question = question.text.strip() + "\n" + " ".join(["|||{}|||".format(img["src"]) for img in question.find_all("img", src=True)])
            else:
                question = question.text.strip()
            answers = (a.text.replace("\xa0", "").strip() for a in soup.find_all("div", class_="radio-control"))
            answers = [a[2:].strip() if a[1] == "." else a for a in answers]
            right = _CORRECT_NAME.get( soup.find("span", class_="right-answer").find("b").text, -1 )
            explanation = soup.find("div", class_="answer-result").text.strip()
            if(EXPLANATION_TRIM_CUE in explanation):
                # special case: if has this cue; throw the last part away
                explanation = explanation.split(EXPLANATION_TRIM_CUE)[0]
            topics = soup.find_all("div", class_="topic-col")
            if(len(topics) >= 2):
                # tag_wrapper, subject_wrapper = topics[:2]
                subject_wrapper = next((t for t in topics if "Môn:" in t.text), None)
                if(subject_wrapper is not None):
                    category = subject_wrapper.find("a").text.strip()
                else:
                    category = ""
                tags = [tag_field.text.strip() for t in topics for tag_field in t.find_all("a") if t is not subject_wrapper]
            elif("huong-nghiep" in url):
                category, tags = "Khác", ""
            elif("tieng-anh" in url):
                category, tags = "English", ""
            elif("dai-hoc" in url):
                category, tags = "Đại học", ""
            else:
                category = tags = ""
    #        print(question, answers, right, explanation)
            data = dict(question=question, correct_id=right, explanation=explanation, tag=", ".join(tags), category=category, url=url)
            if(keep_partial_question):
                data.update({"answer{:d}".format(i+1):a for i, a in enumerate(answers)})   
            else:
                a1, a2, a3, a4 = answers
                data.update(answer1=a1, answer2=a2, answer3=a3, answer4=a4)
#            logger.debug("Queston correctly parsed: {}".format(data))
            writer.writerow(data)
            COUNTER[None] += 1
            generic.logger.info("Link {} has a valid quiz; appending to {:d}.".format(url, COUNTER[None]))
        else:
            generic.logger.debug("Link {} is not a valid quiz; exiting.".format(url))
    except Exception as e:
        generic.logger.error("Parsing link {} has error: {}\n, quiz skipped.".format(url, traceback.format_exc()))

_MULTIPLE_ANSWER_CUE = re.compile(r"^[1-4 ;,]$")
def convert_question_to_multiple(data, special_tag="is_multiple_choice"):
    """Attempt to convert appropriate multiple-choice question in single-choice mode into properly formatted multiple choice.
    Shelved due to positioning question"""
    # check if question is a real multiple question (only have id number in answer)
    raise NotImplementedError
    if(all(re.match(_MULTIPLE_ANSWER_CUE, q[field]) for field in ("answer1", "answer2", "answer3", "answer4"))):
        # correct; attemp to load appropriate cues.
        true_answers_index = [None] * 4
        for i in range(4, 0, -1):
            indices = (m.start() for m in re.finditer(str(i), data["question"]))
            for idx in indices:
                if(i < 4 and idx > true_answers_index[i+1]):
                    # number after the corresponding index; break away 
                    break
                if(data["question"][idx+1] in ". " and data["question"][idx+2] not in "0123456789"):
                    # naive way to exclude number 
                    true_answers_index[i] = idx 
                    break
            #
    else:
        return data

if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO)
    start_url = "https://tracnghiem.net/de-thi/cau-hoi-co-su-khac-nhau-ve-mau-da-giua-cac-chung-toc-la-do-dau-149980.html" 
    DUMP_PATH = "test/tracnghiem_net.pkl"
    if(len(sys.argv) > 2):
        target_location = sys.argv[1]
    else:
        print("Using default: test/tracnghiem_net.txt")
        target_location = "test/tracnghiem_net.txt"
    csv_path = "test/tracnghiem_net.csv"
    file_existed = os.path.isfile(csv_path)
    with io.open(csv_path, "a" if file_existed else "w", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["question", "answer1", "answer2", "answer3", "answer4", "correct_id", "category", "tag", "special", "variable_limitation", "explanation", "url"], dialect="unix")
        if(not file_existed):
            writer.writeheader()
#        soup = generic.get_parsed(start_url)
#        process_data(soup, start_url, writer=writer)
        process_data_fn = partial(process_data, writer=writer)
        return_code = perform_crawl(start_url, target_location, process_data_fn=process_data_fn, recovery_dump_path=DUMP_PATH, prefer_cue="cau-hoi-", retrieve_interval=(0.1, 0.3))
    sys.exit(return_code)

