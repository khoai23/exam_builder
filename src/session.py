"""Manage current session here.
Migrate the code from app.py to debloat it"""
from functools import wraps
import time, os, sys, random
import traceback
import flask 
from flask import url_for
import secrets
from datetime import datetime 
import signal
import threading, _thread
from contextlib import contextmanager

from src.data.reader import read_file, move_file, copy_file, write_file_xlsx, TEMPORARY_FILE_DIR, DEFAULT_FILE_PATH, DEFAULT_BACKUP_PATH, _DEFAULT_FILE_PREFIX, _DEFAULT_BACKUP_PREFIX, _DEFAULT_RECOVER_FILE_PREFIX, _DEFAULT_RECOVER_BACKUP_PREFIX 
from src.data.split_load import OnRequestData 
from src.data.autotagger import AUTOTAG_MATH, AUTOTAG_CHEMISTRY
from src.organizer import assign_ids, shuffle, check_duplication_in_data, convert_text_with_image

import logging
logger = logging.getLogger(__name__)

from typing import Optional, Dict, List, Tuple, Any, Union, Callable

class SessionError(Exception):
    # expected error; if sending this, wrap_try_catch will report back the traceback on DEBUG instead of WARNING to declutter stuff.
    pass

def wrap_try_catch(fn, error_as_str: bool=False) -> callable:
    # function is wrapped in a try-catch; and output the result in either (True, correct_result) or (False, error)
    @wraps(fn)
    def wrapper_fn(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            error_traceback = "\n".join(traceback.format_exception(e))
            logger.log(logging.DEBUG if isinstance(e, SessionError) else logging.WARNING, error_traceback)
            if error_as_str: # might be useful when directly feed to flask
                return (False, str(e))
            else:
                return (False, e)
        return (True, result)
    return wrapper_fn

class ExamManager:
    """Contain & manage all the necessary properties for exams across all version.
    This is slated to update into a version which will support the Classroom object & tailor alongside it need"""
    def __init__(self, quiz_data: OnRequestData):
        self._quiz_data = quiz_data
        self._session = dict()
        self._submit_route = dict()
        self._entry_key_to_session = dict()

    @property
    def quiz_data(self):
        return self._quiz_data

    def generate_unique_str(self, length: int=8, collision_check: Optional[set]=None):
        # create an unique str; if collision_check & the key already exist (VERY unlikely), check & generate a different one 
        key = secrets.token_hex(length)
        if collision_check and key in collision_check:
            return self.generate_unique_str(length, collision_check=collision_check)
        return key

    """Creating, processing & finishing each exam session"""
    @wrap_try_catch
    def create_new_session(self, data: Dict, category: str, check_template: bool=True):
        """Create the session with a normal id key & admin key in the session """
        # format setting: cleaning dates; voiding nulled fields
        setting = convert_template_setting(data["setting"], allow_student_list=True)
        
        if(check_template):
            result, error_type = test_template_validity(data["template"], category, _current_data=self._quiz_data)
            if(not result):
                logger.info("Failed validation test. TODO find specific failure row")
                raise SessionError(error_type)
        # generate a random unique key for this session; plus a key to restrict peer access.
        session_key = self.generate_unique_str(collision_check=self._session)
        admin_key = self.generate_unique_str()
        # calculate the maximum score possible
        max_score = sum((count * score for count, score, ids in data["template"]))
        # put everything to the _session dict
        session_student_record = dict()
        self._session[session_key] = new_exam_session = {"category": category, "template": data["template"], "setting": setting, "admin_key": admin_key, "expire": None, "student": session_student_record, "maximum_score": max_score}
        # if has student_list in setting; pre-generate all the entry key beforehand & disallow student_enter_session from using anonymous mode.
        if setting.get("student_list", None):
            for student_info in setting["student_list"]:
                #print("Adding student: {}".format(student_info))
                entry_key = self.generate_new_student_entrance(new_exam_session, session_key, student_info)
        logger.debug("New exam session with template: {}".format(new_exam_session))
        return (session_key, admin_key)

    def get_session(self, session_key: str):
        return self._session.get(session_key, None)

    def generate_new_student_entrance(self, session: dict, session_key: str, student_data: dict, convert_embedded_image: bool=True) -> str:
        """Universal fn to generate a new student's quiz, timestamp etc. when they enter the exam.
        Need direct access to session; as it might be triggered before being put into the _session referrer.

        A session's `template` consist of a list of (actual_question, score_per_question, total_question_bank); this should theoretically has unlimited amount of section; but realistically it's 4-5 at most. 
        """
        entry_key = self.generate_unique_str(collision_check=self._entry_key_to_session)
        self._entry_key_to_session[entry_key] = session_key 
        # generate the quiz basing on the template
        selected, correct = self.generate_quiz(session["category"], session["template"], convert_embedded_image=convert_embedded_image)
        session["student"][entry_key] = {
                "exam_data": selected,
                "correct": correct,
                "start_time": time.time(),
                **student_data # TODO disallow overriding (if any) here.
        }
        return entry_key

    @wrap_try_catch
    def student_enter_session(self, access_info: dict=None, **access_info_expanded):
        """Student can access by either first-access, which generate an unique key; or reaccess, which must be reached with this unique key already pre-generated.
        first-access can only be reached in anonymous (no-student-list) mode.
        if first-access; the access_info will be something like {{name:..., id:..., properties etc.}, session_key:..., first_access=True}
        if reaccess/restricted: the access_info should only have {key:..., first_access=False}"""
        if access_info is None and access_info_expanded:
            # is in expanded mode; use it instead.
            # expanded mode will be smth like student_enter_session(first_access=True, name=..)
            access_info = dict(access_info_expanded)
        logger.debug("@student_enter_session: received access_info object: {}".format(access_info))

        first_access = access_info.pop("first_access")
        if first_access:
            session_key = access_info.pop("session_key")
            session = self._session[session_key]
            if False:
                # TODO if the session is restricted; kick out 
                raise SessionError("Session {} is restricted; cannot use first_access mode.".format(session_key))
            # granting new key if allowed. TODO bind appropriate per-session info 
            entry_key = self.generate_new_student_entrance(session, session_key, access_info)
            student_data = session["student"][entry_key]
            logger.info("New student key created: {}; exam triggered at {}".format(entry_key, student_data["start_time"]))
        else:
            entry_key = access_info["key"]
            session_key = self._entry_key_to_session[entry_key]
            session = self._session[session_key]
            student_data = session["student"][entry_key]

        setting = session["setting"]
        # regardless of modes; once reaching here, the data is already properly configured
        if(setting.get("exam_duration", None)):
            # send 2 values: elapsed & remaining if there is an exam duration
            exam_duration = setting["exam_duration"] * 60 # convert to second
            end_time = student_data["start_time"] + exam_duration
            elapsed = min(time.time() - student_data["start_time"], exam_duration)
            remaining = exam_duration - elapsed 
        else:
            elapsed = remaining = 0.0
            end_time = float("+inf")

        # if setting is available and actually has score, allow rendering the past questions with correct answers.; if not then feed none & exam.html will reflect that
        student_score = student_data["score"] if "answers" in student_data and setting.get("allow_score", False) else None
        if(time.time() > end_time):
            # TODO just use the exam.html for this.
            raise SessionError("Exam over; you can no longer enter.")
        else:
            # return all the necessary info to populate the exam.html; the real populating is 
            return entry_key, dict(student_name=student_data["name"], exam_data=student_data["exam_data"], submitted=("answers" in student_data), elapsed=elapsed, remaining=remaining, exam_setting=setting, custom_navbar=True, score=student_score)
        
    def calculate_score(self, student_data: Dict, partial_score: bool=False) -> Tuple[int, List]:
        """Calculate basing on the submitted answers. 
        Output result in both default (1 number) variant; or detailed (every correct one) variant.
        If partial_score; partially correct answer in multiple-choice will still have reduced point. Any wrong selection will still beget 0, tho"""
        
        score = 0.0
        detailed_score = []
        for sub, crt, qst in zip(student_data["answers"], student_data["correct"], student_data["exam_data"]):
            if(isinstance(crt, (tuple, list))):
                correct_count = sum((1 if s in sub else 0 for s in crt))
                if not partial_score and correct_count == len(crt) and correct_count == len(sub):
                    # if not partial mode; only count if sending exactly all correct answer
                    score += qst["score"]
                    detailed_score.append(qst["score"])
                    continue 
                else:
                    # if in partial mode; only take extra if all the sub-answer are correct, and if does flag the appropriate ratio
                    if correct_count == len(sub):
                        pscore = qst["score"] * correct_count / len(crt)
                        score += pscore
                        detailed_score.append(pscore)
                        continue 
            else:
                if(sub == crt): 
                    # upon a correct answer submitted; add to the student score
                    score += qst["score"]
                    detailed_score.append(qst["score"])
                    continue
            # if reached here, question is wrong 
            detailed_score.append(0)
        logger.debug("Calculated score: {} | detailed: {}".format(score, detailed_score))
        # write into the dictionary
        student_data["score"] = score 
        student_data["detailed_score"] = detailed_score 
        # return
        return score, detailed_score


    @wrap_try_catch
    def student_submit_answers(self, submitted_answers: Dict, entry_key: str, calculate_score: bool=True, return_result: Optional[bool]=None, return_score: Optional[bool]=None, partial_score: Optional[bool]=False):
        """Student submit their answers; and depend on exam mode, they are given back the correct one or not.
        By default, calculate the results immediately. TODO leave a reference somehow, so bad questions can be recalculated on-demand. This is easier said than done since all quiz element is malleable, it's not reliable to refer to anything unless I implement autogenerated id (and even then it will still run into duplications)
        Alternative is to allow making quizzes from vetted source; and if anybody make from unvetted, their problem."""
        session = self._session[self._entry_key_to_session[entry_key]]
        student_data = session["student"][entry_key]
        logger.debug("Submitter data: {}".format(student_data))
        if("answers" in student_data):
            return flask.jsonify(result=False, error="Already have an submitted answer.")
        else:
            # record to the student data
            student_data["answers"] = submitted_answers 
            # calculate scores immediately if allowed (default).
            if(calculate_score):
                # TODO partial_score part of the setting too
                score, detailed_score = self.calculate_score(student_data, partial_score=partial_score)
                # TODO better wording
                return_result = return_result if return_result is not None else session["setting"].get("allow_result", False)
                return_score = return_score if return_score is not None else session["setting"].get("allow_score", False)
                if(return_result and return_score):
                    return flask.jsonify(result=True, correct=student_data["correct"], score=score)
                elif(return_result):
                    return flask.jsonify(result=True, correct=student_data["correct"])
                elif(return_score):
                    return flask.jsonify(result=True, score=score)
            return flask.jsonify(result=True)
    
    def delete_session(self, session_key: str):
        # remove the specific session; plus all the related entry_key 
        # this will return the session object so it can be put into archive if need to
        session = self._session.pop(session_key, None)
        if session:
            for ek in session["student"]:
                self._entry_key_to_session.pop(ek, None)
        else:
            logger.warning("@delete_session: No session of key {:s}. Check logic.".format(session_key))
        return session

    def wipe_all_sessions(self, for_categories: Optional[List[str]]=None):
        if for_categories is None:
            logger.info("@wipe_all_sessions: wipe all is initiated. All session data will be lost.")
            self._session.clear(); self._entry_key_to_session.clear()
        else:
            targetted = {sid for sid, sdata in session.items() if sdata["category"] in for_categories}
            for sid in targetted:
                self.delete_session(sid) 


    """Code to generate a formatted quiz from specific category. Should be used everywhere that involves making tests."""
    def generate_quiz(self, category: str, template: List[Tuple[int, float, list]], convert_embedded_image: bool=True, **kwargs):
        if not template:
            # when given no template, TODO make its own.
            raise NotImplementedError
        questions, correct = shuffle(self._quiz_data.load_category(category), template, **kwargs)
        if convert_embedded_image:
            # run a function to convert text + inline image into list of options 
            questions = convert_text_with_image(questions)
        return questions, correct

"""Useful helpers that we retains."""

# from https://stackoverflow.com/questions/366682/how-to-limit-execution-time-of-a-function-call
class TimeoutException(Exception):
    pass 

@contextmanager 
def time_limit(seconds):
    def signal_handler(signum=None, frame=None):
        if sys.platform == 'win32': # interrupt the main thread with a KeyboardInterrupt
            _thread.interrupt_main()
        else:  # just sent a signal that way
            raise TimeoutException("Process ran more than {}s. Terminating.".format(seconds))
    if sys.platform == 'win32':
        timer = threading.Timer(seconds, signal_handler)
        timer.start()
    else:
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(int(seconds)+1) # send signal after seconds; has to convert to int for mac/linux
    try:
        yield
    except KeyboardInterrupt:
        # for window, it will be terminated by the 
        raise TimeoutException("Process ran more than {}s. Terminating.".format(seconds))
    finally: # remove signal if either had been ran
        if sys.platform == 'win32':
            timer.cancel()
        else:
            signal.alarm(0)

def test_template_validity(template: List[Tuple[int, float, List]], category: str, _current_data=None):
    """Code to test if a template is valid or not. Generate all equations in the template within a specific timeframe; if that fail, return appropriate problem"""
    question_id = 0
    try:
        full_test_template = [(len(l), 0.0, l) for _, _, l in template ]
        full_count = sum((num for num, _, _ in full_test_template))
        with time_limit(full_count * 0.25):
            # maximum 0.25s for every question 
            shuffle(_current_data.load_category(category), full_test_template)
            return True, None
    except Exception as e:
        logger.error("Template test failed for question {}: {}\n{}".format(getattr(e, "wrong_question_id", "N/A"), e, traceback.format_exc()))
        return False, (e, traceback.format_exc())

def mark_duplication(data: List[Dict]):
    """Mark concerning rows of data with {has_duplicate} and {duplicate_of}."""
    check_dictionary = check_duplication_in_data(data)
    for dfr, dto in check_dictionary.items():
        data[dto]["has_duplicate"] = True 
        data[dfr]["duplicate_of"] = dto
        
def clear_mark_duplication(data: List[Dict]):
    """Deleting all {has_duplicate} and {duplicate_of} mark. 
    TODO add special {verified} mark to prevent deletion in the delete_data_by_ids's safe mode"""
    for d in data:
        d.pop("has_duplicate", None)
        d.pop("duplicate_of", None)

_ALL_ALLOWABLE_SETTING = ["session_name", "student_identifier_name", "exam_duration", "grace_duration", "session_start", "session_end", "allow_score", "allow_result", "student_list"]
def convert_template_setting(setting: Dict, allow_student_list: bool=True, allowed=_ALL_ALLOWABLE_SETTING):
    setting = {k: v for k, v in setting.items() if v is not None and (not isinstance(v, str) or v.strip() != "") and k in allowed}
    if("session_start" in setting):
        # format date & limit entrance
        setting["true_session_start"] = datetime.strptime(setting["session_start"], "%H:%M %d/%m/%Y").timestamp()
    if("session_end" in setting):
        # format date & limit entrance
        setting["true_session_end"] = datetime.strptime(setting["session_end"], "%H:%M %d/%m/%Y").timestamp()
    if(not allow_student_list or ("student_list" in setting and len(setting["student_list"]) == 0)):
        # void the student list if no entry available 
        setting.pop("student_list", None)
    return setting
