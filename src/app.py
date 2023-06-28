import flask
from flask import Flask, request, url_for
# from werkzeug.utils import secure_filename
import os, time, re
import traceback 
import shutil

from src.session import data, current_data, session, filepath_dict, submit_route, student_belong_to_session
from src.session import perform_import, perform_rollback, load_template, mark_duplication, delete_data_by_ids # migrate to external module
from src.session import student_first_access_session, student_reaccess_session, retrieve_submit_route_anonymous, retrieve_submit_route_restricted, submit_exam_result, remove_session
from src.parser.convert_file import read_and_convert
from src.reader import DEFAULT_FILE_PATH, DEFAULT_BACKUP_PATH, _DEFAULT_FILE_PREFIX, TEMPORARY_FILE_DIR, move_file, write_file_xlsx 
from src.organizer import check_duplication_in_data 
from src.map import generate_map_by_region

import logging
logger = logging.getLogger(__name__)

app = Flask("exam_builder")
app.config["UPLOAD_FOLDER"] = "test"
### TODO The import flow will be split in two parts, modifying and committing
app._is_in_commit = False

@app.route("/")
def main():
    """Enter the index page"""
    return flask.render_template("main.html")

@app.route("/map")
def map():
    """Test the draw map. 
    This will be base for us to show a little game board representing progress."""
#    polygons = [(0, 0, 200, 200, [(30, 30), (150, 80), (170, 170), (80, 150)], {"bg": "lime", "fg": "green"})]
    polygons = generate_map_by_region(current_data)
    return flask.render_template("map.html", polygons=polygons)

@app.route("/edit")
def edit():
    """Enter the edit page where we can submit new data to database; rollback and deleting data (preferably duplicated question)
    TODO restrict access
    """
#    print([r["correct_id"] for r in current_data])
    return flask.render_template("edit.html", title="Modify", questions=[])

@app.route("/build")
def build():
    """Enter the quiz build page where we can build a new template for an exam 
    Modification is now in a separate page
    TODO restrict access
    """
#    print([r["correct_id"] for r in current_data])
    return flask.render_template("build.html", title="Data", questions=current_data)

@app.route("/questions", methods=["GET"])
def questions():
    # TODO restrict access like data 
    with_duplicate = request.args.get("with_duplicate")
    if(with_duplicate and with_duplicate.lower() == "true"):
        mark_duplication(current_data)
    return flask.jsonify(questions=current_data)

@app.route("/duplicate_questions", methods=["GET"])
def duplicate_questions():
    # TODO restrict access like data 
    # Deprecated for now
    duplicate = check_duplication_in_data(current_data)
    return flask.jsonify(duplicate_ids=duplicate)

@app.route("/delete_questions", methods=["DELETE"])
def delete_questions():
    # TODO restrict access 
    delete_ids = request.get_json()
    if(not delete_ids or not isinstance(delete_ids, (tuple, list)) or len(delete_ids) == 0):
        return flask.jsonify(result=False, error="Invalid ids sent {}({}); try again.".format(delete_ids, type(delete_ids)))
    else:
        result = delete_data_by_ids(delete_ids)
        if(result["true"]):
            nocommit = request.args.get("nocommit")
            if(not nocommit or nocommit.lower() != "true"):
                # if nocommit is not enabled; push the current data to backup and write down new one 
                perform_commit(filepath_dict["current_path"])
        return flask.jsonify(**result)

@app.route("/export")
def file_export():
    """Allow downloading the database file."""
    return flask.send_file(filepath_dict["current_path"], as_attachment=True)

@app.route("/import", methods=["POST"])
def file_import():
    """Allow overwriting or appending to the database file."""
    try:
        is_replace_mode = request.args.get("replace").lower() == "true"
        file = request.files["file"]
        _, file_extension = os.path.splitext(file.filename)
        # use timestamp as filename for temporary file
        temporary_filename = os.path.join(TEMPORARY_FILE_DIR, str(int(time.time())) + file_extension)
        file.save(temporary_filename)
        # performing the importing procedure; ALWAYS creating backup to be used with rollback
        perform_import(temporary_filename, filepath_dict["current_path"])
        return flask.jsonify(result=True)
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        keep_backup = request.args.get("keep_backup")
        if(not keep_backup or keep_backup.lower() != "true"):
            if(os.path.isfile(temporary_filename)):
                logger.info("Detected failed import file: {}; removing.".format(temporary_filename))
                os.remove(temporary_filename)
        return flask.jsonify(result=False, error=str(e))
#    raise NotImplementedError

@app.route("/rollback")
def rollback():
    """Attempt to do a rollback on previous backup."""
    try:
        if(filepath_dict["backup_path"] and os.path.isfile(filepath_dict["backup_path"])):
            perform_rollback(filepath_dict["backup_path"], filepath_dict["current_path"])
            return flask.jsonify(result=True)
        else:
            return flask.jsonify(result=False, error="No backup available")
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        return flask.jsonify(result=False, error=str(e))

@app.route("/build_template", methods=["POST"])
def build_template():
    """Template data is to be uploaded on the server; provide an admin key to ensure safe monitoring."""
    data = request.get_json()
    logger.info("@build_template: Received template data: {}".format(data))
    result, (arg1, arg2) = load_template(data)
    if(result):
        # return the key to be accessed by the browser
        return flask.jsonify(result=True, session_key=arg1, admin_key=arg2)
    else:
        # return the error and concerning traceback
        return flask.jsonify(result=False, error=str(arg1), error_traceback=str(arg2))

@app.route("/identify")
def identify():
    """First part of entering the exam; this link will allow student to input necessary info to be monitored by /manage
    The form should trigger the generic_submit redirect and go to /enter after it."""
    template_key = request.args.get("template_key", None)
    if(template_key is None):
        return flask.render_template("error.html", error="No session key specified; please use one to identify yourself.", error_traceback=None)
    else:
        # with a template key; try to format properly
        try:
            session_data = session.get(template_key, None)
            if(session_data is None):
                return flask.render_template("error.html", error="Invalid session key; the session might be expired or deleted.")
            student_list = session_data["setting"].get("student_list", None)
            logger.info("Checking against student list: {}".format(student_list))
            if(student_list is not None):
                if(isinstance(student_list, dict) and len(student_list) > 0):
                    # a valid student list; use restricted access 
                    return retrieve_submit_route_restricted(template_key, student_list)
                else:
                    # invalid student list; voiding 
                    logger.error("Invalid student list found: {}; voiding".format(student_list))
                    session_data["setting"].pop("student_list", None)
            # once reached here, the submit_route should have a valid dict ready; redirect to the generic_input html 
            # use sorta anonymous access here
            return retrieve_submit_route_anonymous(template_key)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())

@app.route("/enter")
def enter():
    """Enter the exam.
    If the student_key is not available, a specific student key is generated and used to track individual result.
    Subsequent access with student_key will relaunch the same test, preferably with the choices ready
    TODO disallow entering when not in start_exam_date -> end_exam_date; or time had ran out."""
    student_key = request.args.get("key", None)
    if(student_key):
        return student_reaccess_session(student_key)
    else:
        template_key = request.args.get("template_key", None)
        return student_first_access_session(template_key)


@app.route("/submit", methods=["POST"])
def submit():
    """Student will submit there answer here
    Must be accomodated by the student_key."""
    try:
        student_key  = request.args.get("key")
        submitted_answers = request.get_json()
        return submit_exam_result(submitted_answers, student_key)
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())

@app.route("/single_manager")
def single_manager():
    """Exam maker can access this page to track the current status of the exam; including the choices being made by the student (if chosen to be tracked)
    It should be able to modify settings of the exam"""
    try:
        template_key = request.args.get("template_key")
        admin_key = request.args.get("key")
        if(template_key is None or admin_key is None):
#            print(session)
            return flask.render_template("error.html", error="Missing session key and/or template key", error_traceback=None)
        # TODO allow a box to supplement key to manage 
        # TODO listing all running templates
        session_data = session[template_key]
        logger.debug("Access session data: {}".format(session_data))
        if(admin_key == session_data["admin_key"]):
            return flask.render_template("single_manager.html", session_data=session_data, template_key=template_key)
        else:
            return flask.render_template("error.html", error="Invalid admin key", error_traceback=None)
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())

@app.route("/single_session_data", methods=["GET"])
def single_session_data():
    """Retrieving the exact same data being ran on single_manager.
    TODO use this to autoupdate result."""
    template_key = request.args.get("template_key")
    admin_key = request.args.get("key")
    if(template_key is None or admin_key is None):
        return flask.jsonify(result=False, error="Missing key, data cannot be retrieved.")
    session_data = session[template_key]
    if(admin_key == session_data["admin_key"]):
        return flask.jsonify(result=True, data=session_data)
    else:
        return flask.jsonify(result=False, error="Admin key incorrect, data cannot be retrieved")

@app.route("/session_manager")
def session_manager():
    """Manage all sessions created here."""
    return flask.render_template("session_manager.html", all_session_data=session)

@app.route("/delete_session", methods=["DELETE"])
def delete_session():
    """Only work with a valid admin_key, to prevent some smart mf screwing up sessions."""
    try:
        template_key = request.args.get("template_key")
        admin_key = request.args.get("key")
        return remove_session(template_key, verify=True, verify_admin_key=admin_key)
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())
    
@app.route("/convert")
def convert():
    """Page to do a conversion from text file to a table to be imported."""
    return flask.render_template("convert.html")

@app.route("/convert_text_to_table", methods=["POST"])
def convert_text_to_table():
    """Submitted text file and receive the loadout support.
    TODO migrate this to pure js to lessen server workload"""
    try:
        json_data = request.get_json()
        assert all((field in json_data for field in ["text", "cues"])), "Missing field in data: {}".format(json_data)
        # convert cues to pattern variant (for re.finditer); and nulling out empty field
        if(json_data.get("cue_is_regex", False)):
            to_regex = lambda c: c
        else:
            to_regex = lambda c: re.escape(c)
        qcue, *acue = [to_regex(c).strip() if len(c.strip()) > 0 else None for c in json_data["cues"]]
        # logger.debug(qcue, acue)
        text = json_data["text"]
        problems = read_and_convert(text, question_cue=qcue, answer_cues=acue)
        return flask.jsonify(result=True, problems=problems)
    except Exception as e:
#       return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())
        return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())
    

@app.route("/generic_submit", methods=["POST"])
def generic_submit():
    """Generic submission trigger; allowing user to send up custom data to a hooked function.
    Currently, this will trigger binding of new entrant to template
    Each route must be a Callable[List[str, str]] -> Any
    arguments/keys are supplied by the form construction; 
    returning a redirect blob if handled by the string; or returning a true/false json block for further guidance
    """
    try:
        logger.info("Entering generic_submit...")
        form = request.form.to_dict()
        submit_id = form.pop("id")
        if submit_id not in submit_route:
            logger.warning("Cannot found route id: ", submit_id)
            return flask.jsonify(result=False, error="No route id available")
        result_blob = submit_route[submit_id](**form)
        if(isinstance(result_blob, str) or not isinstance(result_blob, (list, tuple))):
            # upon data being a redirect blob; just throw it back
            return result_blob 
        else:
            result, data_or_error = result_blob 
            # result must ALWAYS be false in this case 
            logger.warning("Error from submit_route: {}".format(data_or_error))
            # TODO show the error 
            return flask.redirect(request.referrer)
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        # back to the previous (identify page); TODO show the error
        return flask.redirect(request.referrer)

if __name__ == "__main__":
    app.run(debug=True)
