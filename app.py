import flask
from flask import Flask, request, url_for
from werkzeug.utils import secure_filename
import secrets
import time 
from datetime import datetime
import traceback

from reader import read_file, DEFAULT_FILE_PATH
from organizer import assign_ids, shuffle

app = Flask("exam_builder")
app.config["UPLOAD_FOLDER"] = "test"

data = {}
data["table"] = current_data = read_file(DEFAULT_FILE_PATH)
data["id"] = id_data = assign_ids(current_data)
data["session"] = session = dict()
data["submit_route"] = submit_route = dict()

def reload_data():
    del current_data[:]; current_data.extend(read_file(DEFAULT_FILE_PATH))
    id_data.clear(); id_data.update(assign_ids(current_data))
    session.clear()
    submit_route.clear()

@app.route("/")
def main():
    """Enter the index page"""
    return flask.render_template("main.html")

@app.route("/data")
def data():
    "Enter the data page, where we can modify the bank and build a new template for an exam"
    return flask.render_template("data.html", questions=current_data)

@app.route("/export")
def file_export():
    """Allow access to the database file."""
    return flask.send_file(DEFAULT_FILE_PATH, as_attachment=True)

@app.route("/import", methods=["POST"])
def file_import():
    """Allow overwriting the database file with a better variant."""
    try:
        file = request.files["file"]
        file.save(DEFAULT_FILE_PATH)
        # TODO read and replace current data
        print("File saved to default path; reload data now.")
        reload_data()
        return flask.jsonify(result=True)
    except Exception as e:
        return flask.jsonify(result=False, error=str(e))
#    raise NotImplementedError

@app.route("/build_template", methods=["POST"])
def build_template():
    """Template data is to be uploaded on the server; provide an admin key to ensure safe monitoring."""
    data = request.get_json()
    print("Received template data:", data)
    # format setting: cleaning dates; voiding nulled fields
    setting = {k: v for k, v in data["setting"].items() if v is not None}
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
    session[key] = {"template": data["template"], "setting": setting, "admin_key": admin_key, "expire": None, "student": dict()}
    print("Session after modification: ", session)
    # return the key to be accessed by the browser
    return flask.jsonify(session_key=key, admin_key=admin_key)

student_belong_to_session = dict()
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
            session_data = session[template_key]
            if(template_key not in submit_route):
                print("First trigger of identify, building corresponding submit route")
                def receive_form_information(student_name=None, **kwargs):
                    # refer to generic_submit for more detail
                    # create unique student key for this specific format
                    student_key = secrets.token_hex(8)
                    # write to session retrieval 
                    student_belong_to_session[student_key] = template_key
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
            # once reached here, the submit_route should have a valid dict ready; redirect to the generic_input html 
            return flask.render_template("generic_input.html", 
                    title="Enter Exam",
                    message="Enter name & submit to start your exam.", 
                    submit_key=template_key,
                    input_fields=[{"id": "student_name", "type": "text", "name": "Student Name"}])
        except Exception as e:
            return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())

@app.route("/enter")
def enter():
    """Enter the exam.
    If the student_key is not available, a specific student key is generated and used to track individual result.
    Subsequent access with student_key will relaunch the same test, preferably with the choices ready
    TODO disallow entering when not in start_exam_date -> end_exam_date; or time had ran out."""
    student_key = request.args.get("key", None)
    if(student_key):
        # retrieve the session key 
        template_key = student_belong_to_session.get(student_key, None)
        if(template_key is None):
            # TODO return a warning that the student key is not correct/expired; also allow entering the key
            return flask.render_template("error.html", error="Missing key; TODO allow input box", error_traceback=None)
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
            flask.render_template("error.html", error="Exam time over.", error_traceback=None)
        else:
            # allow entering
            return flask.render_template("exam.html", exam_data=student_data["exam_data"], submitted=("answers" in student_data), elapsed=elapsed, remaining=remaining, 
                    exam_setting = session[template_key]["setting"])
    else:
        template_key = request.args.get("template_key", None)
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

@app.route("/submit", methods=["POST"])
def submit():
    """Student will submit there answer here
    Must be accomodated by the student_key."""
    try:
        student_key  = request.args.get("key")
        template_key = student_belong_to_session[student_key]
        submitted_answers = request.get_json()
        assert isinstance(submitted_answers, list) and all((a is None or 0 < a <= 4 for a in submitted_answers)), "answers must be list of [1-4]; but is {}".format(submitted_answers)
        student_data = session[template_key]["student"][student_key]
        print(student_data)
        if("answers" in student_data):
            return flask.jsonify(result=False)
        else:
            # record to the student info
            student_data["answers"] = submitted_answers 
            # calculate scores immediately 
            score = 0.0
            for sub, crt, qst in zip(submitted_answers, student_data["correct"], student_data["exam_data"]):
                if(sub == crt): 
                    # upon a correct answer submitted; add to the student score
                    score += qst["score"]
            print("Calculated score: ", score)
            student_data["score"] = score 
            return flask.jsonify(result=True)
    except Exception as e:
        return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())

@app.route("/manage")
def manage():
    """Exam maker can access this page to track the current status of the exam; including the choices being made by the student (if chosen to be tracked)
    Not implemented as of now"""
    try:
        template_key = request.args.get("template_key")
        admin_key = request.args.get("key")
        if(template_key is None or admin_key is None):
            return flask.render_template("error.html", error="Missing key specified; TODO allow input box", error_traceback=None)
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
        return flask.jsonify(result=False, error=str(e))

if __name__ == "__main__":
    app.run(debug=True)
