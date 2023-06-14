import flask
from flask import Flask, request, url_for
# from werkzeug.utils import secure_filename
import os, time, re
import traceback 
import shutil

from session import data, current_data, session, submit_route, student_belong_to_session
from session import reload_data, append_data, load_template, student_first_access_session, student_reaccess_session, retrieve_submit_route_anonymous, retrieve_submit_route_restricted, submit_exam_result, remove_session
from convert_file import read_and_convert
from reader import DEFAULT_FILE_PATH, DEFAULT_BACKUP_PATH, _DEFAULT_FILE_PREFIX, TEMPORARY_FILE_DIR, move_file, write_file_xlsx

app = Flask("exam_builder")
app.config["UPLOAD_FOLDER"] = "test"
app._current_file = DEFAULT_FILE_PATH 
app._backup_file = DEFAULT_BACKUP_PATH # if(os.path.isfile(DEFAULT_BACKUP_PATH)) else None # no need; the backup will work here

@app.route("/")
def main():
    """Enter the index page"""
    return flask.render_template("main.html")

@app.route("/data")
def data():
    "Enter the data page, where we can modify the bank and build a new template for an exam"
#    print([r["correct_id"] for r in current_data])
    return flask.render_template("data.html", title="Data", questions=current_data)

@app.route("/export")
def file_export():
    """Allow downloading the database file."""
    return flask.send_file(app._current_file, as_attachment=True)

@app.route("/import", methods=["POST"])
def file_import():
    """Allow overwriting or appending to the database file.
    TODO """
    try:
        is_replace_mode = request.args.get("replace").lower() == "true"
        file = request.files["file"]
        _, file_extension = os.path.splitext(file.filename)
        # use timestamp as filename for temporary file
        temporary_filename = os.path.join(TEMPORARY_FILE_DIR, str(int(time.time())) + file_extension)
        file.save(temporary_filename)
        # backup the current file
        if(is_replace_mode):
            # TODO read and replace current data
            print("File saved to default path; reload data now.")
            reload_data(location=temporary_filename)
            # if reload success, backup the current file
            app._backup_file = move_file(app._current_file, os.path.join(TEMPORARY_FILE_DIR, "backup"), is_target_prefix=True)
            # then move file into current  
            app._current_file = move_file(temporary_filename, _DEFAULT_FILE_PREFIX, is_target_prefix=True)
        else:
            print("File saved to temporary; append and try to write combined")
            # read data as add-on to current data 
            append_data(location=temporary_filename)
            # extract the combination to disk in xlsx
            combined_file = _DEFAULT_FILE_PREFIX + ".xlsx"
            # if reload success, backup the current file
            app._backup_file = move_file(app._current_file, os.path.join(TEMPORARY_FILE_DIR, "backup"), is_target_prefix=True)
            # then write the combined variant
            write_file_xlsx(combined_file, current_data)
            # delete the temporary file 
            os.remove(temporary_filename)
        return flask.jsonify(result=True)
    except Exception as e:
        print(traceback.format_exc())
        return flask.jsonify(result=False, error=str(e))
#    raise NotImplementedError

@app.route("/rollback")
def rollback():
    """Attempt to do a rollback on previous backup."""
    try:
        if(app._backup_file and os.path.isfile(app._backup_file)):
            # TODO maybe need to switch xlsx?
            app._current_file = move_file(app._backup_file, DEFAULT_FILE_PATH, is_target_prefix=False)
            app._backup_file = None
            reload_data(location=app._current_file)
            return flask.jsonify(result=True)
        else:
            return flask.jsonify(result=False, error="No backup available")
    except Exception as e:
        print(traceback.format_exc())
        return flask.jsonify(result=False, error=str(e))

@app.route("/build_template", methods=["POST"])
def build_template():
    """Template data is to be uploaded on the server; provide an admin key to ensure safe monitoring."""
    data = request.get_json()
    print("Received template data:", data)
    key, admin_key = load_template(data)
    # return the key to be accessed by the browser
    return flask.jsonify(session_key=key, admin_key=admin_key)

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
            student_list = session_data["setting"]["student_list"]
            if(student_list is not None):
                if(isinstance(student_list, dict) and len(student_list) > 0):
                    # a valid student list; use restricted access 
                    return retrieve_submit_route_restricted(template_key, student_list)
                else:
                    # invalid student list; voiding 
                    print("Invalid student list found: {}; voiding".format(student_list))
                    session_data["setting"]["student_list"] = None
            # once reached here, the submit_route should have a valid dict ready; redirect to the generic_input html 
            # use sorta anonymous access here
            return retrieve_submit_route_anonymous(template_key)
        except Exception as e:
            return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())
            print(traceback.format_exc())

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
        return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())
        print(traceback.format_exc())

@app.route("/manage")
def manage():
    """Exam maker can access this page to track the current status of the exam; including the choices being made by the student (if chosen to be tracked)
    Not implemented as of now"""
    try:
        template_key = request.args.get("template_key")
        admin_key = request.args.get("key")
        if(template_key is None or admin_key is None):
#            print(session)
            return flask.render_template("session_manager.html", all_session_data=session)
#            return flask.render_template("error.html", error="Missing key specified; TODO allow input box", error_traceback=None)
        # TODO allow a box to supplement key to manage 
        # TODO listing all running templates
        session_data = session[template_key]
        print("Access session data: ", session_data)
        if(admin_key == session_data["admin_key"]):
            return flask.render_template("manage.html", session_data=session_data, template_key=template_key)
        else:
            return flask.render_template("error.html", error="Invalid admin key", error_traceback=None)
    except Exception as e:
        print("Error: ", e)
        return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())

@app.route("/delete_session", methods=["DELETE"])
def delete_session():
    """Only work with a valid admin_key, to prevent some smart mf screwing up sessions."""
    try:
        template_key = request.args.get("template_key")
        admin_key = request.args.get("key")
        return remove_session(template_key, verify=True, verify_admin_key=admin_key)
    except Exception as e:
        print("Error: ", e)
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
        print(qcue, acue)
        text = json_data["text"]
        problems = read_and_convert(text, question_cue=qcue, answer_cues=acue)
        return flask.jsonify(result=True, problems=problems)
    except Exception as e:
        print("Error: ", e)
        return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())
        print(traceback.format_exc())
    

@app.route("/generic_submit", methods=["POST"])
def generic_submit():
    """Generic submission trigger; allowing user to send up custom data to a hooked function.
    Currently, this will trigger binding of new entrant to template
    Each route must be a Callable[List[str, str]] -> Any
    arguments/keys are supplied by the form construction; 
    returning a redirect blob if handled by the string; or returning a true/false json block for further guidance
    """
    try:
        print("Entering generic_submit...")
        form = request.form.to_dict()
        submit_id = form.pop("id")
        if submit_id not in submit_route:
            print("Cannot found route id: ", submit_id)
            return flask.jsonify(result=False, error="No route id available")
        result_blob = submit_route[submit_id](**form)
        if(isinstance(result_blob, str) or not isinstance(result_blob, (list, tuple))):
            # upon data being a redirect blob; just throw it back
            return result_blob 
        else:
            result, data_or_error = result_blob 
            # TODO differentiate between result=True and result=False
            return flask.jsonify(result=result, error=data_or_error, data=data_or_error)
    except Exception as e:
        print("Error: {} - {}".format(e, traceback.format_exc()))
        return flask.jsonify(result=False, error=str(e))

if __name__ == "__main__":
    app.run(debug=True)
