"""Manage current session here.
Migrate the code from app.py to debloat it"""
import time, os, sys
import traceback
import flask 
from flask import url_for
import secrets
from datetime import datetime 
import signal
import threading, _thread
from contextlib import contextmanager

from src.data.reader import read_file, move_file, copy_file, write_file_xlsx, DEFAULT_FILE_PATH, DEFAULT_BACKUP_PATH, _DEFAULT_FILE_PREFIX, _DEFAULT_BACKUP_PREFIX, _DEFAULT_RECOVER_FILE_PREFIX, _DEFAULT_RECOVER_BACKUP_PREFIX 
from src.data.split_load import OnRequestData
from src.organizer import assign_ids, shuffle, check_duplication_in_data, convert_text_with_image

import logging
logger = logging.getLogger(__name__)

from typing import Optional, Dict, List, Tuple, Any, Union, Callable

data = current_data = OnRequestData()
# data["table"] = current_data = read_file(DEFAULT_FILE_PATH)
#data["id"] = current_data.load_category(session_data["category"]] = assign_ids(current_data)
data["session"] = session = dict()
data["submit_route"] = submit_route = dict()
student_belong_to_session = dict()

def wipe_session(for_categories: Optional[List[str]]=None):
    """Wipe all sessions. If specifying category, keep the sessions that are not related to the wipe."""
    if for_categories is None:
        session.clear()
        submit_route.clear()
        student_belong_to_session.clear()
    else:
        rm_sessions = {sid: sdata for sid, sdata in session.items() if sdata["category"] in for_categories}
        for sid, sdata in rm_sessions.items(): 
            session.pop(sid)
            submit_route.pop(sid, None)
            for std in sdata["student"]:
                student_belong_to_session.pop(std, None)

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


"""This section is for redirecting & managing real session data, entry points & management"""

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
        signal.alarm(seconds) # send signal after seconds
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

def test_template_validity(template: List[Tuple[int, float, List]], category: str):
    """Code to test if a template is valid or not. Generate all equations in the template within a specific timeframe; if that fail, return appropriate problem"""
    question_id = 0
    try:
        full_test_template = [(len(l), 0.0, l) for _, _, l in template ]
        full_count = sum((num for num, _, _ in full_test_template))
        with time_limit(full_count * 0.25):
            # maximum 0.25s for every question 
            shuffle(current_data.load_category(category), full_test_template)
            return True, None
    except Exception as e:
        logger.error("Template test failed for question {}: {}\n{}".format(getattr(e, "wrong_question_id", "N/A"), e, traceback.format_exc()))
        return False, (e, traceback.format_exc())

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

def load_template(data: Dict, category: str, check_template: bool=True):
    """Create the session with a normal id key & admin key in the session """
    # format setting: cleaning dates; voiding nulled fields
    setting = convert_template_setting(data["setting"], allow_student_list=True)
    
    if(check_template):
        result, error_type = test_template_validity(data["template"], category)
        if(not result):
            logger.info("Failed validation test. TODO find specific failure row")
            return False, error_type
    # generate a random key for this session.
    key = secrets.token_hex(8)
    if key in session:
        # duplicate generation; do again 
        key = secrets.token_hex(8)
        assert key not in session, "Rare issue when id key cannot be generated; swap to while"
    admin_key = secrets.token_hex(8)
    # TODO add a timer to expire the session when needed 
    # calculate maximum score using current data 
    max_score = sum((count * score for count, score, ids in data["template"]))
    session[key] = {"category": category, "template": data["template"], "setting": setting, "admin_key": admin_key, "expire": None, "student": dict(), "maximum_score": max_score}
    logger.debug("New template: {}".format(session[key]))
    return True, (key, admin_key)


def student_reaccess_session(student_key: str, convert_embedded_image: bool=True):
    # retrieve the session key 
    template_key = student_belong_to_session.get(student_key, None)
    if(template_key is None):
        # TODO return a warning that the student key is not correct/expired; also allow entering the key
        return flask.render_template("error.html", error="Invalid student key, please contact your teacher", error_traceback=None)
    # retrieve the generated test; TODO also keep backup of what was chosen 
    session_data = session[template_key]
    student_data = session_data["student"][student_key]
    logger.debug("Accessing existing key: ", student_key, " with data", student_data)
    # return the exam page directly
    if(session_data["setting"].get("exam_duration", None)):
        # send 2 values: elapsed & remaining if there is a duration
        exam_duration = session_data["setting"]["exam_duration"] * 60 # convert to s
        end_time = student_data["start_time"] + exam_duration
        elapsed = min(time.time() - student_data["start_time"], exam_duration)
        remaining = exam_duration - elapsed 
    else:
        elapsed = remaining = 0.0
        end_time = float("+inf")
    logger.debug("Submitted answer? {}".format("answers" in student_data))
    # if setting is available and actually has score, allow rendering; if not then is None
    student_score = student_data["score"] if "answers" in student_data and session_data["setting"].get("allow_score", False) else None
    if(time.time() > end_time):
        return flask.render_template("error.html", error="Exam over; cannot submit", error_traceback=None)
    else:
        # allow entering
        exam_data = student_data["exam_data"]
        if convert_embedded_image:
            # run a function to convert text + inline image into list of options 
            exam_data = convert_text_with_image(exam_data)
        return flask.render_template("exam.html", student_name=student_data["student_name"], exam_data=exam_data, submitted=("answers" in student_data), elapsed=elapsed, remaining=remaining, exam_setting=session_data["setting"], custom_navbar=True, score=student_score)

def retrieve_submit_route_anonymous(template_key: str):
    """This is for submitting the student info; NOT for submitting the exam result 
    No restriction on student info, anybody can enter
    """
    if(template_key not in submit_route):
        logger.debug("First trigger of identify, building corresponding submit route")
        def receive_form_information(student_name=None, **kwargs):
            # refer to generic_submit for more detail
            # create unique student key for this specific format
            student_key = secrets.token_hex(8)
            # write to session retrieval
            student_belong_to_session[student_key] = template_key
            session_data = session.get(template_key, None)
            # write to session data itself.
            selected, correct = shuffle(current_data.load_category(session_data["category"]), session_data["template"])
            session_data["student"][student_key] = student_data = {
                    "student_name": student_name,
                    "exam_data": selected,
                    "correct": correct,
                    "start_time": time.time()
            }
            logger.info("New student key created: {}; exam triggered at {}".format(student_key, student_data["start_time"]))
            # redirect to enter/ 
            return flask.redirect(url_for("enter", key=student_key))
        # add this to the submit_route dictionary
        submit_route[template_key] = receive_form_information
    return flask.render_template("generic_input.html", 
            title="Enter Exam",
            message="Enter name & submit to start your exam.", 
            submit_key=template_key,
            custom_navbar=True,
            # TODO make this dependent on session setting
            input_fields=[{"id": "student_name", "type": "text", "name": "Student Name"}]) 

def retrieve_submit_route_restricted(template_key: str, restricted_ids: Dict[str, str]):
    """In restricted mode, only valid keys of restricted_ids can be used.
    For now only allow id: name; TODO expand on further properties
    """
    default_setting = dict(
        title="Enter Exam",
        message="Enter ID & submit to start your exam.", 
        submit_key=template_key,
        input_fields=[{"id": "student_id", "type": "text", "name": "Provided ID"}]
    )
    if(template_key not in submit_route):
        student_id_to_key = dict() # shared dictionary to allow this particular function to re-refer to existing session
        def receive_and_check_info(student_id=None, **kwargs):
            student_id = student_id.strip()
            if(student_id not in restricted_ids):
#                return redirect(request.referrer)
                # render with error message
                return flask.render_template("generic_input.html", error="ID {} does not exist in the restriction list.".format(student_id), **default_setting)
                # return flask.jsonify(result=False, error="ID {} does not exist in the restriction list.".format(id))
            if(student_id in student_id_to_key):
                logger.info("Restricted mode: ID {} reaccessing its session")
                student_key = student_id_to_key[student_id]
            else:
                logger.info("Restricted mode: ID {} first-accessing its session")
                student_key = secrets.token_hex(8)
                # write to session retrieval
                student_belong_to_session[student_key] = template_key
                session_data = session.get(template_key, None)
                # write to session data itself.
                selected, correct = shuffle(current_data.load_category(session_data["category"]), session_data["template"])
                session_data["student"][student_key] = student_data = {
                        "student_id": student_id,
                        "student_name": restricted_ids[student_id],
                        "exam_data": selected,
                        "correct": correct,
                        "start_time": time.time()
                }
                logger.info("New student key created: {}; exam triggered at {}".format(student_key, student_data["start_time"]))
                # after everything, record so subsequent accesses will work
                student_id_to_key[student_id] = student_key
            # redirect to enter/ 
            return flask.redirect(url_for("enter", key=student_key))
        submit_route[template_key] = receive_and_check_info

    return flask.render_template("generic_input.html", **default_setting) 

def submit_exam_result(submitted_answers: Dict, student_key: str, calculate_score: bool=True, return_result: Optional[bool]=None, return_score: Optional[bool]=None):
    template_key = student_belong_to_session[student_key]
    student_data = session[template_key]["student"][student_key]
    logger.debug("Student data: {}".format(student_data))
    if("answers" in student_data):
        return flask.jsonify(result=False, error="Already have an submitted answer.")
    else:
        # record to the student info
        student_data["answers"] = submitted_answers 
        # calculate scores immediately 
        if(calculate_score):
            score = 0.0
            detailed_score = []
            for sub, crt, qst in zip(submitted_answers, student_data["correct"], student_data["exam_data"]):
                if(isinstance(crt, (tuple, list))):
                    if(all((s in crt for s in sub))):
                        # upon all correct answers, add to the student score 
                        # TODO partial score mode 
                        score += qst["score"]
                        detailed_score.append(qst["score"])
                        continue
                else:
                    if(sub == crt): 
                        # upon a correct answer submitted; add to the student score
                        score += qst["score"]
                        detailed_score.append(qst["score"])
                        continue
                # if reached here, question is wrong 
                detailed_score.append(0)
            logger.debug("Calculated score: {}".format(score))
            student_data["score"] = score 
            student_data["detailed_score"] = detailed_score 
            # TODO clean this better
            return_result = return_result if return_result is not None else session[template_key]["setting"].get("allow_result", False)
            return_score = return_score if return_score is not None else session[template_key]["setting"].get("allow_score", False)
            if(return_result and return_score):
                return flask.jsonify(result=True, correct=student_data["correct"], score=score)
            elif(return_result):
                return flask.jsonify(result=True, correct=student_data["correct"])
            elif(return_score):
                return flask.jsonify(result=True, score=score)
        return flask.jsonify(result=True)

def remove_session(session_key: str, verify: bool=False, verify_admin_key: Optional[str]=None, callback: Optional[Callable[[str], Any]]=None):
    """This is to remove session. Wipe the session data and all corresponding key related to it.
    If cannot find session by key, or verification failed, return false accordingly.
    Can be feed a callback which receives the deleted session as argument; useful if want to remove & archive it somehow"""
    session_data = session.get(session_key, None)
    if(session_data is None):
        return flask.jsonify(result=False, deleted=True, error="Session key not found, might have deleted/expired already.")
    elif(verify and session_data["admin_key"] != verify_admin_key):
        return flask.jsonify(result=False, deleted=False, error="Secret key incorrect, you do not have right to delete this session.")
    # passed here means ok, start deleting the session, submit_route, and student id
    session_data = session.pop(session_key)
    submit_route.pop(session_key, None)
    for student_key in session_data["student"]:
        student_belong_to_session.pop(student_key, None)
    # once finished deletion, if callback exist, send the session data over 
    if(callback):
        callback(session_data)
    return flask.jsonify(result=True, deleted=True) 

"""This is for a special campaign session. Instead of student id, this session object receives a specific player order and shuffle an appropriate quiz for that."""

def create_campaign_session(campaign, categories: List[str]):
    # select specific quiz range for campaign 
#    print([c not in current_data.categories for c in categories])
    assert isinstance(categories, list) and len(categories) > 0 and all((c in current_data.categories for c in categories)), "Invalid category selected: {} (available {})".format(categories, data.categories)
    session = {"categories": categories, "orders": dict()}
    return session 

_default_coefficient_calculator = lambda c, t: 2.0 * c / t # break even at 50% correct
def build_order_quiz(session: dict, quiz_count: int=10, duration_min: int=15, select_category: Optional[str]=None, coefficient_calculator: callable=_default_coefficient_calculator) -> Tuple[bool, str]:
    # attempt to build a quiz for the order, returning a referring key to be re-accessed if necessary 
    # get a random key
    key = secrets.token_hex(8)
    if select_category:
        # if there is a valid select_category, use that 
        if select_category not in session["categories"]:
            # invalid category, break out 
            return False, "Invalid category {} (possible: {})".format(select_category, session["categories"])
    else:
        # if not, select one of the category randomly
        select_category = random.choice(session["categories"])
    # with a valid category, generate appropriate quiz on range of that category
    # TODO deeper selection mode (e.g by tag)
    available = current_data.load_category(select_category)
    if len(available) < quiz_count:
        # not enough question to load, throw a warning 
        logger.warning("Category \"{}\" only has {} question, while requiring {}. Trimming requirement.".format(select_category, len(available), quiz_count))
        quiz_count = len(available)
    question_ids = random.sample(range(len(available)), k=quiz_count)
    questions, correct = shuffle(available, [(len(question_ids), 0.0, question_ids)])
    # write it into the "orders" section 
    start_time = time.time()
    end_time = time.time() + duration_min * 60
    session["orders"][key] = {"category": select_category, "exam_data": questions, "correct": correct, "start_time": start_time, "end_time": end_time, "coefficient_calculator": coefficient_calculator}
    # return appropriate data to access
    return True, key

def access_order_quiz(session: dict, key: str):
    order_data = session["orders"][key]
    # calculate the remaining time
    end_time = order_data["end_time"]
    elapsed = min(time.time() - order_data["start_time"], exam_duration)
    remaining = exam_duration - elapsed
    # convert the exam_data into image-compatible version
    exam_data = order_data["exam_data"]
    if convert_embedded_image:
        # run a function to convert text + inline image into list of options 
        exam_data = convert_text_with_image(exam_data)
    if(time.time() > end_time):
        # render the error when timer is exceeded
        return flask.render_template("error.html", error="Order quiz over; cannot submit", error_traceback=None)
    else:
        # render normally
        return flask.render_template("exam.html", student_name="Player 0", exam_data=exam_data, submitted=("answers" in order_data), elapsed=elapsed, remaining=remaining, exam_setting=session_data["setting"], custom_navbar=True, score=student_score)

def submit_order_quiz_result(session: dict, submitted_answers: Dict, key: str):
    # simplified variant of the order quiz; 
    order_data = session["orders"][key]
    if("answers" in order_data):
        return flask.jsonify(result=False, error="Already have an submitted answer.")
    else:
        # record to the student info
        order_data["answers"] = submitted_answers 
        # extract the correct vs total; session will create appropriate coefficient by its function
        coefficient_calculator = order_data["coefficient_calculator"]
        correct = 0
        for sub, crt in zip(submitted_answers, order_data["correct"]):
            if sub == crt:
                correct += 1
        total = len(order_data["correct"])
        order_data["order_coef"] = order_coef = coefficient_calculator(correct, total)
        # use the localstorage to trigger update from the campaign map 
        # do not send it over through localstorage; since such data could be tampered with 
        # TODO hook an update for campaign here through the order_data 
        return flask.jsonify(result=True, coef=order_coef, trigger_campaign_update=True)
