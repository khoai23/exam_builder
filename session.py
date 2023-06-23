"""Manage current session here.
Migrate the code from app.py to debloat it"""
import time, os 
import flask 
from flask import url_for
import secrets
from datetime import datetime 

from reader import read_file, move_file, write_file_xlsx, DEFAULT_FILE_PATH, _DEFAULT_FILE_PREFIX, _DEFAULT_BACKUP_PREFIX
from organizer import assign_ids, shuffle, check_duplication_in_data

from typing import Optional, Dict, List, Tuple, Any, Union, Callable

data = {}
data["table"] = current_data = read_file(DEFAULT_FILE_PATH)
data["id"] = id_data = assign_ids(current_data)
data["session"] = session = dict()
data["submit_route"] = submit_route = dict()
student_belong_to_session = dict()

"""Section working with data: importing, deleting and rolling back will be put here.
TODO put all this to a different corresponding files to debloat"""

def reload_data(location=DEFAULT_FILE_PATH, check_duplication: bool=True):
    """Reload - clear everything and then re-load the data. No session will be kept, since id would likely be completely screwed"""
    del current_data[:]; current_data.extend(read_file(location))
    id_data.clear(); id_data.update(assign_ids(current_data))
    session.clear()
    submit_route.clear()
    student_belong_to_session.clear()
    if(check_duplication):
        mark_duplication(current_data)

def append_data(location=DEFAULT_FILE_PATH, check_duplication: bool=True):
    """Append - update the data after the current one; sessions will be kept since id would not be moved"""
    current_data.extend(read_file(location))
    id_data.clear(); id_data.update(assign_ids(current_data))
    if(check_duplication):
        mark_duplication(current_data)
#    print([r["correct_id"] for r in current_data])

def delete_data_by_ids(ids: List[int], safe: bool=False, strict: bool=True, preserve_session: bool=False):
    """Deleting specific data. 
    If safe, only allow deletion of uncommitted data (set with a specific flag).
    If strict, will reject deletion if trying to delete strange id. Still allow duplicate though
    For now allow deleting anything."""
    if(safe):
        raise NotImplementedError
    else:
        ids = set((int(i) for i in ids))
        new_data = []
        for i, q in enumerate(current_data):
            if(i in ids):
                # found; removing 
                ids.remove(i)
            else:
                # not found; re-add 
                new_data.append(q)
            # TODO create a refer (old_id -> new_id, and migrate all standing session using this dict)
        if(strict and len(ids) > 0):
            return {"result": False, "error": "Invalid list of id: {} not found".format(ids)}
        # put the new_data back in
        del current_data[:]
        current_data.extend(new_data)
    print("Reupdated data: ", current_data)
    # re-set the question ids
    id_data.clear(); id_data.update(assign_ids(current_data))
    if(preserve_session):
        raise NotImplementedError
    else:
        session.clear()
        submit_route.clear()
        student_belong_to_session.clear()
    return {"result": True}

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

def create_backup(current_file: str, backup_prefix=_DEFAULT_BACKUP_PREFIX):
    """Function will move the file to backup position while being mindful of its extension."""
    return move_file(current_file, backup_prefix, is_target_prefix=True)


def perform_import(import_file: str, current_file: str, replace_mode: bool=False, delete_import_after_done: bool=True):
    """Performing appropriate importing protocol. Reloading/updating data as needed depending on replace_mode
    Assuming an import file is created at {import_file}, and can be read by reload_data(); the file at {current_file} will be replaced with the latest update of each variant
    Always return "backup_path" & "current_path"
    """
    backup_path = create_backup(current_file)
    # add/replace the data
    if(replace_mode):
        print("Import and add the data to current")
        reload_data(location=import_file)
    else:
        print("Import and replace the data to current")
        append_data(location=import_file)
    # regardless of mode; write the current data to the current path 
    current_path = _DEFAULT_FILE_PREFIX + ".xlsx"
    write_file_xlsx(current_path, current_data)
    # clean up if flag is set
    if(delete_import_after_done):
        os.remove(import_file)
    # done, only return correct 
    return (backup_path, current_path)

def perform_rollback(backup_file: str, current_path: str):
    """Performing rollback. Just move the file back in and reload it."""
    os.remove(current_path)
    current_path = move_file(backup_file, _DEFAULT_FILE_PREFIX, is_target_prefix=True)
    backup_path = None
    reload_data(location=current_path)
    return current_path, backup_path


"""This section is for redirecting & managing real session data, entry points & management"""

def load_template(data: Dict):
    # format setting: cleaning dates; voiding nulled fields
    setting = {k: v for k, v in data["setting"].items() if v is not None and (not isinstance(v, str) or v.strip() != "")}
    if("session_start" in setting):
        # format date & limit entrance
        setting["true_session_start"] = datetime.strptime(setting["session_start"], "%H:%M %d/%m/%Y").timestamp()
    if("session_end" in setting):
        # format date & limit entrance
        setting["true_session_end"] = datetime.strptime(setting["session_end"], "%H:%M %d/%m/%Y").timestamp()
    if("student_list" in setting and len(setting["student_list"]) == 0):
        # void the student list if no entry available 
        setting.pop("student_list", None)

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
    """Deprecated as retrieve_submit_route_anonymous & retrieve_submit_route_restricted will perform duty for this hardpoint"""
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
    session_data = session[template_key]
    student_data = session_data["student"][student_key]
    print("Accessing existing key: ", student_key, " with data", student_data)
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
    print("Submitted answer? ", ("answers" in student_data))
    if(time.time() > end_time):
        return flask.render_template("error.html", error="Exam over; cannot submit", error_traceback=None)
    else:
        # allow entering
        return flask.render_template("exam.html", student_name=student_data["student_name"], exam_data=student_data["exam_data"], submitted=("answers" in student_data), elapsed=elapsed, remaining=remaining, exam_setting=session[template_key]["setting"], custom_navbar=True)

def retrieve_submit_route_anonymous(template_key: str):
    """This is for submitting the student info; NOT for submitting the exam result 
    No restriction on student info, anybody can enter
    """
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
    return flask.render_template("generic_input.html", 
            title="Enter Exam",
            message="Enter name & submit to start your exam.", 
            submit_key=template_key,
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
                print("Restricted mode: ID {} reaccessing its session")
                student_key = student_id_to_key[student_id]
            else:
                print("Restricted mode: ID {} first-accessing its session")
                student_key = secrets.token_hex(8)
                # write to session retrieval
                student_belong_to_session[student_key] = template_key
                session_data = session.get(template_key, None)
                # write to session data itself.
                selected, correct = shuffle(id_data, session_data["template"])
                session_data["student"][student_key] = student_data = {
                        "student_id": student_id,
                        "student_name": restricted_ids[student_id],
                        "exam_data": selected,
                        "correct": correct,
                        "start_time": time.time()
                }
                print("New student key created: ", student_key, ", exam triggered at ", student_data["start_time"])
                # after everything, record so subsequent accesses will work
                student_id_to_key[student_id] = student_key
            # redirect to enter/ 
            return flask.redirect(url_for("enter", key=student_key))
        submit_route[template_key] = receive_and_check_info

    return flask.render_template("generic_input.html", **default_setting) 

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
            print("Calculated score: ", score)
            student_data["score"] = score 
            student_data["detailed_score"] = detailed_score
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
