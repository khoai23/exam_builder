"""Code to help organizing data by adding an unique ID, then dividing them by category, difficulty and/or tag."""
from collections import defaultdict
import random 

from typing import Optional, Dict, List, Tuple, Any, Union

def assign_ids(data: List[Dict]):
    id_based_data = {}
    for i, row in enumerate(data): # most basic form
        row["id"] = i;
        id_based_data[i] = row
    return id_based_data

def organize(data: List[Dict], default_category: str="unknown"):
    # category are single-choice, mutually exclusive identifier
    # tags is not 
    categorized_data = defaultdict(list)
    for row in data:
        cat = row.get("category", default_category)
        categorized_data[cat].append(row)
    return categorized_data 

def shuffle(data: Dict[int, Dict], all_questions: List[Tuple[int, List]], seed=None):
    # handle multiple questions already selected 
    # the selected should already been sub-divided to its minor section; this process will shuffle both the choices and the order of the answers and provide correct answer ids for them.
    if(seed):
        random.seed(seed)
    selected, correct = [], []
    for qnum, qids in all_questions:
        qids = random.sample(qids, qnum)
        for qid in qids:
            q = data[qid]
            answer_shuffle = random.sample(list(range(1, 5)), 4)
            new_question = {"question": q["question"], "answers": [q["answer{:d}".format(i)] for i in answer_shuffle] }
            new_correct_id = answer_shuffle[q["correct_id"]] - 1
            selected.append(new_question)
            correct.append(new_correct_id)
    return selected, correct

if __name__ == "__main__":
    from reader import read_file
    data = read_file("test/sample.csv")
    id_data = assign_ids(data)
    print(shuffle(id_data, [(1, [0, 1, 2]), (2, [3, 4, 5, 6])]))
