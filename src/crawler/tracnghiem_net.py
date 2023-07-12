import io, csv, re 
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
def process_data(soup, url=None, writer=None):
    """Receive the necessary data and write it to a csv."""
    # print(soup)
    question = soup.find("h1", class_="title28Bold")
    if(question is not None):
        question = question.text.strip()
        answers = (a.text.replace("\xa0", "").strip() for a in soup.find_all("div", class_="radio-control"))
        a1, a2, a3, a4 = answers = [a[2:].strip() if a[1] == "." else a for a in answers]
        right = _CORRECT_NAME.get( soup.find("span", class_="right-answer").find("b").text, -1 )
        explanation = soup.find("div", class_="answer-result").text.strip()
        if(EXPLANATION_TRIM_CUE in explanation):
            # special case: if has this cue; throw the last part away
            explanation = explanation.split(EXPLANATION_TRIM_CUE)[0]
        tag_wrapper, subject_wrapper = soup.find_all("div", class_="topic-col")
        tags = [t.text.strip() for t in tag_wrapper.find_all("a")]
        category = subject_wrapper.find("a").text.strip()
#        print(question, answers, right, explanation)
        data = dict(question=question, answer1=a1, answer2=a2, answer3=a3, answer4=a4, correct_id=right, explanation=explanation, tag=", ".join(tags), category=category)
#        print(data)
        writer.writerow(data)
        generic.logger.debug("Link {} has a valid quiz; appending.".format(url))
    else:
        generic.logger.debug("Link {} is not a valid quiz; exiting.".format(url))

if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.DEBUG)
    start_url = "https://tracnghiem.net/de-thi/cau-hoi-co-su-khac-nhau-ve-mau-da-giua-cac-chung-toc-la-do-dau-149980.html" 
    DUMP_PATH = "test/tracnghiem_net.pkl"
    if(len(sys.argv) > 2):
        target_location = sys.argv[1]
    else:
        print("Using default: test/tracnghiem_net.txt")
        target_location = "test/tracnghiem_net.txt"
    with io.open("test/tracnghiem_net.csv", "w", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["question", "answer1", "answer2", "answer3", "answer4", "correct_id", "category", "tag", "special", "variable_limitation", "explanation"], dialect="unix")
        writer.writeheader()
#        soup = generic.get_parsed(start_url)
#        process_data(soup, start_url, writer=writer)
        process_data_fn = partial(process_data, writer=writer)
        return_code = perform_crawl(start_url, target_location, process_data_fn=process_data_fn, recovery_dump_path=DUMP_PATH)
#    sys.exit(return_code)

