import os, io, csv 
from collections import defaultdict

from src.data.reader import HEADERS, process_field 
from src.data.split_load import quote, unquote 

from src.parser.filter_rule import parse_by_rules, FilterRule, EmptyQuestionRule, DuplicateAnswerRule, FullAnswerRule

from typing import Optional, List, Tuple, Any, Union, Dict

def reparse_csv(filepath: str, rules: List[FilterRule], headers: Optional[List[str]]=None) -> Tuple[List, List]:
    # read a file from `filepath` into a dict. Should at minimum has `question`, `answer1-4`, and `correct_id`
#    correct_data, failed_data = [], []
    with io.open(filepath, "r", encoding="utf-8") as rf:
        reader = csv.DictReader(rf, fieldnames=headers)
        correct_data, failed_data = parse_by_rules(reader, rules, output_removed=True)
#        for row in reader:
#            try:
#                if "question" not in row or not row["question"].strip():
#                    print("Question do not have appropriate text: {}".format(row))
#                    raise ValueError
#                process_field(row)
#                correct_data.append(row)
#            except Exception as e:
#                failed_data.append(row)
    return correct_data, failed_data

def export_valid(correct_data: List[Dict], failed_data: List[Dict], filepath: str):
    """Paired with reparse_csv above"""
    base, ext = os.path.splitext(filepath)
    with io.open(base + "_correct" + ext, "w", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=HEADERS + ["explanation", "url"], dialect="unix") 
        writer.writeheader()
        for row in correct_data:
            writer.writerow(row)
    with io.open(base + "_failed" + ext, "w", encoding="utf-8") as ff:
        writer = csv.DictWriter(ff, fieldnames=HEADERS + ["explanation", "url"], dialect="unix") 
        writer.writeheader()
        for row in failed_data:
            writer.writerow(row)
 
def split_by_category(correct_data: List[Dict]) -> Dict[str, List[Dict]]:
    """Split the correct data into sub-section by category."""
    splitted = defaultdict(list)
    for q in correct_data:
        splitted[q.get("category", "N/A").strip() or "N/A"].append(q)
    return splitted

def export_parsed(splitted: Dict[str, List[Dict]], filepath: str, failed_data: Optional[List]=None):
    base, ext = os.path.splitext(filepath)
    for cat, data in splitted.items():
        with io.open(base + "_" + quote(cat) + ext, "w", encoding="utf-8") as cf:
            writer = csv.DictWriter(cf, fieldnames=HEADERS + ["explanation", "url"], dialect="unix") 
            writer.writeheader()
            for row in data:
                writer.writerow(row)
    if(failed_data):
        with io.open(base + "_failed" + ext, "w", encoding="utf-8") as ff:
            writer = csv.DictWriter(ff, fieldnames=HEADERS + ["explanation", "url"], dialect="unix") 
            writer.writeheader()
            for row in failed_data:
                writer.writerow(row)
            

if __name__ == "__main__":
    # target = sys.argv[1]
    import sys
    if len(sys.argv) < 2:
        print("Script usage: python -m src.parser.filter_data filename [cat]")
        sys.exit(1)
    correct, failed = reparse_csv(sys.argv[1], [EmptyQuestionRule(), FullAnswerRule(), EmptyQuestionRule()])
    if len(sys.argv) > 2 and "cat" in sys.argv:
        splitted = split_by_category(correct)
        export_parsed(splitted, sys.argv[1], failed_data=failed)
    else:
        export_valid(correct, failed, sys.argv[1])
