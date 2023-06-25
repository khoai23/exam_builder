"""Code to help organizing data by adding an unique ID, then dividing them by category, difficulty and/or tag."""
import re
from collections import defaultdict
import random 
import unicodedata 

from dynamic_problem import convert_dynamic_key_problem, convert_single_option_problem, convert_fixed_equation_problem, convert_single_equation_problem

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

shared_generator = {}
def get_past_generator(qid: int, question_template: Dict, generator_fn: callable):
    # try to retrieve past generator
    q_generator = shared_generator.get(qid, None)
    if(q_generator is not None):
        q_test = next(q_generator, None) # try to draw another object from generator 
        if(q_test is not None):
            # has object, continue 
            q = q_test
        else:
            # no object, create generator, draw it, and put back into generator library
            shared_generator[qid] = q_generator = generator_fn(question_template)
            q = next(q_generator)
    else:
        # no generator, draw and put back into the generator
        shared_generator[qid] = q_generator = generator_fn(question_template)
        q = next(q_generator)
    return q

# TODO wipe this upon data reload
def shuffle(data: Dict[int, Dict], all_questions: List[Tuple[int, float, List]], seed=None):
    # handle multiple questions already selected 
    # the selected should already been sub-divided to its minor section; this process will shuffle both the choices and the order of the answers and provide correct answer ids for them.
    # for specific dynamic problem; propels it into corresponding dynamic_problem function
    # not one step back further after the score var
    if(seed):
        random.seed(seed)
    selected, correct = [], []
    for qnum, qsc, qids in all_questions:
        qids = random.sample(qids, qnum)
        for qid in qids:
            q = data[qid]
            answer_shuffle = random.sample(list(range(1, 5)), 4)
            if(q.get("is_dynamic_key", False)):
                # TODO allow dynamic_key with fixed/single equation
                q = convert_dynamic_key_problem(q)
            elif(q.get("is_fixed_equation", False)):
                q = convert_fixed_equation_problem(q)
            elif(q.get("is_single_equation", False)):
                q = get_past_generator(qid, q, convert_single_equation_problem)
            elif(q.get("is_single_option", False)):
                q = get_past_generator(qid, q, convert_single_option_problem)
            # shuffle to create the new_question
            new_question = {"question": q["question"], "answers": [q["answer{:d}".format(i)] for i in answer_shuffle], "score": qsc, "is_multiple_choice": q["is_multiple_choice"] }
            if(q["is_multiple_choice"]):
                new_correct_id = tuple((i+1 for i, aid in enumerate(answer_shuffle) if aid in q["correct_id"]))
            else:
                new_correct_id = next((i for i, aid in enumerate(answer_shuffle) if aid == q["correct_id"])) + 1
            #print(answer_shuffle, q["correct_id"])
            #print("->", new_correct_id)
            selected.append(new_question)
            correct.append(new_correct_id)
    return selected, correct

ignore_tokens_duplication = re.compile(r"\|\|\|.+?\|\|\||{.+?}|\W")
# from https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def remove_nonchar(input_str):
    return remove_accents(re.sub(ignore_tokens_duplication, "", input_str))

def check_duplication_in_data(data: List[Dict], deviation: Optional[int]=None):
    """Perform check and find duplication.
    Check question's static section only (word-based, no special token, no space), and only allow upto {deviation} difference. For now, only deviation=0 (exact match) is allowed."""
    question_stripped = ( (q["id"], remove_nonchar(q["question"])) for q in data)
    check_dictionary = {}
    duplicate_dictionary = {}
    for qid, qstr in question_stripped:
        # TODO find closest deviation instead
        if(qstr in duplicate_dictionary):
            # found duplicate, record to check_dictionary
            previous_qid = duplicate_dictionary[qstr]
            check_dictionary[qid] = previous_qid
        else:
            # not found duplicate, add to duplicate_dictionary
            duplicate_dictionary[qstr] = qid 
    # result is dictionary for duplicate_new vs duplicate_old; since newer one should be removed
    return check_dictionary


if __name__ == "__main__":
    from reader import read_file, DEFAULT_FILE_PATH
    data = read_file(DEFAULT_FILE_PATH)
    id_data = assign_ids(data)
    print(shuffle(id_data, [(1, 5, [0, 1, 2]), (2, 5, [3, 4, 5, 6])]))
