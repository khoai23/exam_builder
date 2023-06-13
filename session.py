"""Manage current session here.
Migrate the code from app.py to debloat it"""
import flask 
from flask import url_for
import secrets
from datetime import datetime 
import time

from reader import read_file, DEFAULT_FILE_PATH
from organizer import assign_ids, shuffle 

from typing import Optional, Dict, List, Tuple, Any, Union, Callable

data = {}
data["table"] = current_data = read_file(DEFAULT_FILE_PATH)
data["id"] = id_data = assign_ids(current_data)
data["session"] = session = dict()
data["submit_route"] = submit_route = dict()
student_belong_to_session = dict()

def reload_data(location=DEFAULT_FILE_PATH):
    """Reload - clear everything and then re-load the data. No session will be kept, since id would likely be completely screwed"""
    del current_data[:]; current_data.extend(read_file(location))
    id_data.clear(); id_data.update(assign_ids(current_data))
    session.clear()
    submit_route.clear()
    student_belong_to_session.clear()

def append_data(location=DEFAULT_FILE_PATH):
    """Append - update the data after the current one; sessions will be kept since id would not be moved"""
    current_data.extend(read_file(location))
    id_data.clear(); id_data.update(assign_ids(current_data))
#    print([r["correct_id"] for r in current_data])

def load_template(data: Dict):
    # format setting: cleaning dates; voiding nulled fields
    setting = {k: v for k, v in data["setting"].items() if v is not None and (not isinstance(v, str) or v.strip() != "")}
    if("session_start" in setting):
        # format date & limit entrance
        setting["true_session_start"] = datetime.strptime(setting["session_start"], "%H:%M %d/%m/%Y").timestamp()
    if("session_end" in setting):
        # format date & limit entrance
        setting["true_session_end"] = datetime.strptime(setting["session_end"], "%H:%M %d/%m/%Y").timestamp()

    # generate a random key for this session.
    key = secrets.token_hex(8)
    admin_key = secrets.token_hex(8)
    # Maybe TODO check here if the template is valid?
    # TODO add a timer to expire the session when needed 
    # calculate maximum score using current data 
    max_score = sum((count * score for count, score, ids in data["template"]))
    session[key] = {"template": data["template"], "setting": setting, "admin_key": admin_key, "expire": None, "student": dict(), "maximum_score": max_score}
    print("Session after modification: ", session)
    return key, admin_key

def student_first_access_session(template_key: str):
    session_data = session.get(template_key, None)
    if(template_key is None or session_data is None):
        # TODO return a warning that session is not correct/expired; also enter the key as above
        return flask.render_template("error.html", error="Missing key or missing exam session; TODO allow input box", error_traceback=None)   
    # create the new student key 
    student_key = secrets.token_hex(8)
    # write to session retrieval 
    student_belong_to_session[student_key] = template_key
    # write to session data itself.
    selected, correct = shuffle(id_data, session_data["template"])
    session_data["student"][student_key] = student_data = {
            "exam_data": selected,
            "correct": correct,
            "start_time": time.time()
    }
    print("New student key created: ", student_key, ", exam triggered at ", student_data["start_time"])
    # redirect to self 
    return flask.redirect(url_for("enter", key=student_key))

def student_reaccess_session(student_key: str):
    # retrieve the session key 
    template_key = student_belong_to_session.get(student_key, None)
    if(template_key is None):
        # TODO return a warning that the student key is not correct/expired; also allow entering the key
        return flask.render_template("error.html", error="Invalid student key, please contact your teacher", error_traceback=None)
    # retrieve the generated test; TODO also keep backup of what was chosen
    student_data = session[template_key]["student"][student_key]
    print("Accessing existing key: ", student_key, " with data", student_data)
    # return the exam page directly
    # send 2 values: elapsed & remaining 
    end_time = student_data["start_time"] + 3600.0 # 1 hr fixed for now 
    elapsed = min(time.time() - student_data["start_time"], 3600.0)
    remaining = 3600.0 - elapsed
    print("Submitted answer? ", ("answers" in student_data))
    if(time.time() > end_time):
        flask.render_template("error.html", error="Exam over; cannot submit", error_traceback=None)
    else:
        # allow entering
        return flask.render_template("exam.html", exam_data=student_data["exam_data"], submitted=("answers" in student_data), elapsed=elapsed, remaining=remaining, exam_setting=session[template_key]["setting"])

def retrieve_submit_route(template_key: str):
    """This is for submitting the student info; NOT for submitting the exam result"""
    if(template_key not in submit_route):
        print("First trigger of identify, building corresponding submit route")
        def receive_form_information(student_name=None, **kwargs):
            # refer to generic_submit for more detail
            # create unique student key for this specific format
            student_key = secrets.token_hex(8)
            # write to session retrieval
            student_belong_to_session[student_key] = template_key
            session_data = session.get(template_key, None)
            # write to session data itself.
            selected, correct = shuffle(id_data, session_data["template"])
            session_data["student"][student_key] = student_data = {
                    "student_name": student_name,
                    "exam_data": selected,
                    "correct": correct,
                    "start_time": time.time()
            }
            print("New student key created: ", student_key, ", exam triggered at ", student_data["start_time"])
            # redirect to enter/ 
            return flask.redirect(url_for("enter", key=student_key))
        # add this to the submit_route dictionary
        submit_route[template_key] = receive_form_information 
    return template_key 

def submit_exam_result(submitted_answers: Dict, student_key: str, calculate_score: bool=True, return_score: bool=None):
    template_key = student_belong_to_session[student_key]
    student_data = session[template_key]["student"][student_key]
    print(student_data)
    if("answers" in student_data):
        return flask.jsonify(result=False, error="Already have an submitted answer.")
    else:
        # record to the student info
        student_data["answers"] = submitted_answers 
        # calculate scores immediately 
        if(calculate_score):
            score = 0.0
            for sub, crt, qst in zip(submitted_answers, student_data["correct"], student_data["exam_data"]):
                if(isinstance(crt, (tuple, list))):
                    if(all((s in crt for s in sub))):
                        # upon all correct answers, add to the student score 
                        # TODO partial score mode 
                        score += qst["score"]
                else:
                    if(sub == crt): 
                        # upon a correct answer submitted; add to the student score
                        score += qst["score"]
            print("Calculated score: ", score)
            student_data["score"] = score 
            if(return_score):
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
