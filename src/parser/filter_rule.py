"""Rules to find issue in crawled data & rejecting them.
Should be shared by the more primitive filter_data to test; and read_file to help isolating/catching bugs."""
from abc import ABC, abstractmethod 
from enum import IntEnum 
import re

from src.generator.dynamic_problem import MathJaxSymbols

from typing import Optional, List, Tuple, Any, Union, Dict

import logging
logger = logging.getLogger(__name__)

class FilterAction(IntEnum):
    PASS = 0    # this means question is valid and can be carried on
    STOP = 1    # this means to invalidate the whole section. Don't see any reason to use, yet 
    REMOVE = 2  # this means the question is not recoverable at all and will be discarded from current data.
    TAG = 3     # this means the question is recoverable manually; TODO put a special tag to it.
    RESNTAG = 4 # this means the question can be recoverable automatically but also need further manual confirmation or changes. (autoresolve n tag). Will probably be the main operation
    AUTORES = 5 # this means the question can be recoverable automatically & need no additional tag (autoresolve)

class FilterRule(ABC):
    @abstractmethod
    def check_question(self, question: dict) -> FilterAction:
        """This is the base check of the question. Output will be a FilterAction enum value."""
        raise NotImplementedError  

    def resolve(self, question: dict) -> dict:
        """If FilterAction returned RESNTAG or AUTORES, this will be autorun to help with the recovery."""
        raise NotImplementedError

class EmptyQuestionRule(FilterRule):
    """If empty question, just throw away."""
    def check_question(self, question):
        if question.get("question", "").strip():
            return FilterAction.PASS 
        return FilterAction.REMOVE

class DuplicateAnswerRule(FilterRule):
    ALL_ANSWERS_PAIRINGS = [(i, j) for i in range(0, 3) for j in range(i+1, 4)]
    AUTORESOLVE_TAG = "missing_answer"
    """If has duplicate answers,
        if there are more than 1 duplicate pairing, throw away
        if the duplicate is not correct, or correct in single_choice, can automerge them with a tag 
    """
    def check_question(self, question):
        answers = [question.get("answer{:d}".format(i+1), "").strip() for i in range(4)]
        if any(answers[i] and answers[j] and answers[i] == answers[j] for i, j in DuplicateAnswerRule.ALL_ANSWERS_PAIRINGS):
            if question.get("is_multiple_choice", True):
                return FilterAction.REMOVE
            all_duplicates = [(i, j) for i, j in DuplicateAnswerRule.ALL_ANSWERS_PAIRINGS if answers[i] and answers[j] and answers[i] == answers[j]]
            if len(all_duplicates) > 1:
                return FilterAction.REMOVE  
            # if reach here, can be autorecovered
            return FilterAction.RESNTAG  
        # if condition not triggered, no duplication
        return FilterAction.PASS 

    def resolve(self, question):
        # if reach here, there is a RESNTAG trigger; collapse the duplicates to the 1st one, and migrate the correct_id over if it has to 
        answers = [question["answer{:d}".format(i+1)].strip() for i in range(4)]
        dup_1, dup_2 = next( ((i, j) for i, j in DuplicateAnswerRule.ALL_ANSWERS_PAIRINGS if answers[i] and answers[j] and answers[i] == answers[j]) )
        if question["correct_id"] == dup_2+1:
            question["correct_id"] = dup_1+1 # move to 1st in anticipation of removal 
        question.pop("answer{:d}".format(dup_2+1), None)
        # TODO this is better of on special?
        tag = question["tag"] = question.get("tag", list())
        if DuplicateAnswerRule.AUTORESOLVE_TAG not in tag:
            tag.append(DuplicateAnswerRule.AUTORESOLVE_TAG)
        return question

class FullAnswerRule(FilterRule):
    AUTORESOLVE_TAG = "missing_answer"
    """If has <=4 answers, 
        if is_single_equation, this is not even considered; TODO enforce answer1?
        if is_single_option, remove. TODO also tag with some stronger restriction?
        if is neither, tag for maybe manual fix; as it could work with <4 """
    def check_question(self, question):
        if question.get("is_single_equation", False):
            return FilterAction.PASS
        if not all(question.get("answer{:d}".format(i+1), "").strip() for i in range(4)):
            if question.get("is_single_option", False):
                return FilterAction.REMOVE
            else:
                return FilterAction.TAG 
        return FilterAction.PASS 

    def resolve(self, question):
        tag = question["tag"] = question.get("tag", list())
        if FullAnswerRule.AUTORESOLVE_TAG not in tag:
            tag.append(FullAnswerRule.AUTORESOLVE_TAG)
        return question 

class OutdatedDynamicFormattingRule(FilterRule):
    TAG = "reformat_syntax"
    """Starting from when this rule was created, dynamic variable declaration is nested in as {{...}} instead of {..} to prevent collision with LaTeX grouping. If found a "special" question that uses LaTeX but with no {{...}} bracket, it will be tagged to be manually reinspected."""
    def __init__(self, all_dynamic_keyword: List=["is_fixed_equation", "is_single_equation"]):
        # need to do this instead of linking src.data.reader as this is a dependency from there
        self.all_dynamic_keyword = all_dynamic_keyword

    def check_question(self, question):
        if any(question.get(sk, None) for sk in self.all_dynamic_keyword):
            # is special 
            all_text = "\n".join(question.get(f, "") for f in ("question", "answer1", "answer2", "answer3", "answer4"))
            if re.search(MathJaxSymbols, all_text) and not any(cue in all_text for cue in ("{{", "}}")):
                # no matching symbol, tagging is required.
                return FilterAction.TAG 
        return FilterAction.PASS 

    def resolve(self, question):
        tag = question["tag"] = question.get("tag", list())
        if OutdatedDynamicFormattingRule.TAG not in tag:
            tag.append(OutdatedDynamicFormattingRule.TAG)
        return question 
        
class CorrectAnswerFormatRule(FilterRule):
    TAG = "invalid_answer"
    """If correct_id is not a valid number and the question is not is_single_equation, remove it. TODO allow tagging?"""
    def check_question(self, question):
        if q.get("is_single_equation", False):
            return FilterAction.PASS 
        if "correct_id" not in q:
            return FilterAction.REMOVE
        if q.get("is_multiple_choice", False):
            # multiple choice, check all inside 
            if all(0 < int(c) <= 4 for c in q["correct_id"]):
                return FilterAction.PASS 
            else:
                return FilterAction.REMOVE 
        else:
            if 0 < int(q["correct_id"]) <= 4:
                return FilterAction.PASS 
            else:
                return FilterAction.REMOVE

def parse_by_rules(data: List[dict], rules: List[FilterRule], output_removed: bool=True) -> Tuple[Dict, Optional[Dict]]:
    # perform parsing with a list of rules conforming with FilterRule's mechanism.
    filtered, removed = list(), list()
    for q in data:
        keep = True
        for r in rules:
            action = r.check_question(q)
            if action == FilterAction.PASS:
                continue 
            elif action == FilterAction.STOP:
                raise ValueError("Question {} had been intercepted by rule {} and the whole data had been invalidated. Check clarity.")
            elif action == FilterAction.REMOVE:
                keep = False 
                break
            else:
                logger.debug("Question {} had resolvable {} with \"{}\"; resolving.".format(q, action, r))
                q = r.resolve(q)
        if keep:
            filtered.append(q)
        elif output_removed:
            removed.append(q)
    return filtered, (removed if output_removed else None)
