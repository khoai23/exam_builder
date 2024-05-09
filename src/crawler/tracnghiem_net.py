import io, os, csv, re 
import traceback
from functools import partial 
import unicodedata

from src.crawler import generic

from typing import Tuple

INCLUDE_KEY = {"bai-hoc", "trac-nghiem", "de-kiem-tra", "de-thi", "tieng-anh", "cntt", "dai-hoc", "huong-nghiep"} # not used atm
FILTER_KEY = {"..", ".jsp", "dang-nhap", "void"}
APPEND_DOMAIN = "https://tracnghiem.net"

def get_neighbor_links(soup_or_url, include_key=INCLUDE_KEY, filter_key=FILTER_KEY, append_domain=APPEND_DOMAIN):
    return generic.get_neighbor_links(soup_or_url, filter_key=filter_key, append_domain=append_domain)
    
def perform_crawl(*args, neighbor_link_fn=get_neighbor_links, **kwargs):
    return generic.perform_crawl(*args, neighbor_link_fn=neighbor_link_fn, **kwargs)

COUNTER = {None: 0}
def per_category_writer(basepath: str, flush_interval: int=1000) -> Tuple[dict, callable]:
    # write associating file per-category on a per-demand basis 
    all_category = {}
    base_prefix, extension = os.path.splitext(basepath)
    def write_with_category(category, row):
        if category in all_category:
            # existing file; just write into it 
            all_category[category][-1].writerow(row)
        else:
            # new file; instantiate, put into all_category, and put that row in.
            category_cue_raw = unicodedata.normalize("NFKD", category).encode("ascii", "ignore").decode("utf-8")
            category_cue_alnum = "".join((c for c in category_cue_raw if c.isalnum()))
            csv_path = base_prefix + category_cue_alnum + extension
            file_existed = os.path.isfile(csv_path)
            # check file & append/continue as needed
            cf = io.open(csv_path, "a" if file_existed else "w", encoding="utf-8")
            writer = csv.DictWriter(cf, fieldnames=["question", "answer1", "answer2", "answer3", "answer4", "correct_id", "category", "tag", "special", "variable_limitation", "explanation", "url"], dialect="unix")
            if(not file_existed):
                writer.writeheader()
            # put into the category box
            all_category[category] = (cf, writer)
            # write anyway
            writer.writerow(row)
        COUNTER[None] += 1
        if flush_interval and (COUNTER[None] + 1) % flush_interval == 0:
            # also periodically flush every file if option is supplied
            for f, _ in all_category.values():
                f.flush()
    return all_category, write_with_category

_CORRECT_NAME = {"A": 1, "B": 2, "C": 3, "D": 4}
EXPLANATION_TRIM_CUE = "Chọn đáp án"

def parse_data_from_frame(soup) -> Tuple[list, str, str]:
    # parsing necessary from sub-frame section
    answers = (a.text.replace("\xa0", "").strip() for a in soup.find_all("div", class_="radio-control"))
    answers = [a[2:].strip() if a[1] == "." else a for a in answers]
    right = _CORRECT_NAME.get( soup.find("span", class_="right-answer").find("b").text, -1 )
    explanation = soup.find("div", class_="answer-result").text.strip()
    if(EXPLANATION_TRIM_CUE in explanation):
        # special case: if has this cue; throw the last part away
        explanation = explanation.split(EXPLANATION_TRIM_CUE)[0]
    return answers, right, explanation


def process_data(soup, url=None, writer_fn=None, keep_partial_question=True):
    """Receive the necessary data and write it to a csv."""
    # print(soup)
    try:
        frame = soup.find("div", class_="d9Box")
        question = soup.find("h1", class_="title28Bold")
        if frame is None:
            generic.logger.debug("Link {} is not a valid quiz (no frame); exiting.".format(url))
        elif question is None:
            generic.logger.debug("Link {} is not a valid quiz (no title); exiting.".format(url))
        else:
            # topic & tags first. If can find in appropriate slot, use that; if not, try to get a pseudo equivalent with the navigator breadcrumb
            topics = soup.find_all("div", class_="topic-col")
            if(len(topics) >= 2):
                # tag_wrapper, subject_wrapper = topics[:2]
                subject_wrapper = next((t for t in topics if "Môn:" in t.text), None)
                if(subject_wrapper is not None):
                    category = subject_wrapper.find("a").text.strip()
                else:
                    category = ""
                tags = [tag_field.text.strip() for t in topics for tag_field in t.find_all("a") if t is not subject_wrapper]
            else:
                # category are inferred from the breadcrumb object; tag is empty 
                category = soup.find("div", class_="breadcrumb").text.strip().split("\n")[-1].strip()
                tags = ""

            # check if exist any image in question; if yes, append it in the question itself
            if(question.find("img")):
                generic.logger.debug("Question has image, currently append to the end of text. TODO better positioning")
                question = question.text.strip() + "\n" + " ".join(["|||{}|||".format(img["src"]) for img in question.find_all("img", src=True)])
            else:
                question = question.text.strip()
            
            shared_content_box = frame.find("div", class_="question-detail")
            if shared_content_box:
                # multiple question mode, mostly in the english variant. This means the questions will have a "shared" part 
                additional_question_content = shared_content_box.text.replace("\xa0", "").strip()
                if additional_question_content:
                    question_prefix = question + "\n\n" + additional_question_content + "\n\n"
                else:
                    question_prefix = question + "\n\n"
                for subquestion_frame in frame.find_all("div", class_="part-item"):
                    subsuffix = subquestion_frame.find("h4", class_="title16Bold").text.strip()
                    answers, right, explanation = parse_data_from_frame(subquestion_frame)
                    data = dict(question=question_prefix+subsuffix, correct_id=right, explanation=explanation, tag=", ".join(tags), category=category, url=url)
                    if(keep_partial_question):
                        data.update({"answer{:d}".format(i+1):a for i, a in enumerate(answers)})   
                    else:
                        a1, a2, a3, a4 = answers
                        data.update(answer1=a1, answer2=a2, answer3=a3, answer4=a4)
                    writer_fn(category, data)
            else:
                # single question mode, vast majority of cases.
                answers, right, explanation = parse_data_from_frame(frame)
    #            print(question, answers, right, explanation)
                data = dict(question=question, correct_id=right, explanation=explanation, tag=", ".join(tags), category=category, url=url)
                if(keep_partial_question):
                    data.update({"answer{:d}".format(i+1):a for i, a in enumerate(answers)})   
                else:
                    a1, a2, a3, a4 = answers
                    data.update(answer1=a1, answer2=a2, answer3=a3, answer4=a4)
#                logger.debug("Single question correctly parsed: {}".format(data))
                writer_fn(category, data)
            generic.logger.info("Link {} has valid quiz(es); appending to \"{}\".".format(url, category))
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
    start_url = [
            "https://tracnghiem.net/de-kiem-tra/{:s}-lop-{:d}/?type=2".format(subject, tier)
            for tier in range(6, 13) 
            for subject in ["toan-hoc", "vat-ly", "sinh-hoc", "tieng-anh", "lich-su", "dia-ly", "gdcd", "cong-nghe", "tin-hoc", "lich-su-va-dia-li", "khoa-hoc-tu-nhien"]
    ]
    DUMP_PATH = "test/tracnghiem_net.pkl"
    if(len(sys.argv) > 2):
        link_location = sys.argv[1]
        assert not link_location.endswith(".csv"), "Must input link_location as not-csv (best as plaintext)"
        data_location = os.path.splitext(link_location)[0] + ".csv"
    else:
        print("Using default: test/tracnghiem_net.txt|.csv")
        link_location = "test/tracnghiem_net.txt"
        data_location = "test/tracnghiem_net.csv"
    all_category, write_by_category_fn = per_category_writer(data_location)
    process_data_fn = partial(process_data, writer_fn=write_by_category_fn)
    return_code = perform_crawl(start_url, link_location, process_data_fn=process_data_fn, recovery_dump_path=DUMP_PATH, prefer_cue="cau-hoi-", retrieve_interval=(0.1, 0.3))
    for file, _ in all_category.values():
        file.close()
    sys.exit(return_code)

