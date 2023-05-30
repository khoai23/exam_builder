from flask import Flask, render_template, request, jsonify, redirect, url_for
import secrets
import time

from reader import read_file
from organizer import assign_ids, shuffle

app = Flask("exam_builder")
data = {}
data["table"] = current_data = read_file("test/sample.csv")
data["id"] = id_data = assign_ids(current_data)
data["session"] = session = dict()

@app.route("/")
def main():
    """Enter the index page"""
    return render_template("main.html")

@app.route("/data")
def data():
    "Enter the data page, where we can modify the bank and build a new template for an exam"
    return render_template("data.html", questions=current_data)

@app.route("/build_template", methods=["POST"])
def build_template():
    """Template data is to be uploaded on the server; provide an admin key to ensure safe monitoring."""
    template = request.get_json()
    print("Received template data:", template)
    # generate a random key for this session.
    key = secrets.token_hex(8)
    admin_key = secrets.token_hex(8)
    # Maybe TODO check here if the template is valid?
    # TODO add a timer to expire the session when needed
    # TODO wipe all sessions when a new import had been made.
    session[key] = {"template": template, "admin_key": admin_key, "expire": None, "student": dict()}
    print("Session after modification: ", session)
    # return the key to be accessed by the browser
    return jsonify(session_key=key, admin_key=admin_key)

student_belong_to_session = dict()
@app.route("/enter")
def enter():
    """Enter the exam.
    If the student_key is not available, a specific student key is generated and used to track individual result.
    Subsequent access with student_key will relaunch the same test, preferably with the choices ready"""
    student_key = request.args.get("key", None)
    if(student_key):
        # retrieve the session key 
        template_key = student_belong_to_session.get(student_key, None)
        if(template_key is None):
            # TODO return a warning that the student key is not correct/expired; also allow entering the key
            raise NotImplementedError
        # retrieve the generated test; TODO also keep backup of what was chosen
        student_data = session[template_key]["student"][student_key]
        print("Accessing existing key: ", student_key, " with data", student_data)
        # return the exam page directly
        # send 2 values: elapsed & remaining 
        end_time = student_data["start_time"] + 3600.0 # 1 hr fixed for now 
        elapsed = min(time.time() - student_data["start_time"], 3600.0)
        remaining = 3600.0 - elapsed
        print("Submitted answer? ", ("answers" in student_data))
        return render_template("exam.html", exam_data=student_data["exam_data"], submitted=("answers" in student_data), elapsed=elapsed, remaining=remaining)
    else:
        template_key = request.args.get("template_key", None)
        if(template_key is None):
            # TODO return a page allowing to enter the key 
            raise NotImplementedError
        template = session.get(template_key, None)
        if(template is None):
            # TODO return a warning that session is not correct/expired; also enter the key as above
            raise NotImplementedError
        # create the new student key 
        student_key = secrets.token_hex(8)
        # write to session retrieval 
        student_belong_to_session[student_key] = template_key
        # write to session data itself.
        selected, correct = shuffle(id_data, template["template"])
        session[template_key]["student"][student_key] = student_data = {
                "exam_data": selected,
                "correct": correct,
                "start_time": time.time()
        }
        print("New student key created: ", student_key, ", exam triggered at ", student_data["start_time"])
        # redirect to self 
        return redirect(url_for("enter", key=student_key))

@app.route("/submit", methods=["POST"])
def submit():
    """Student will submit there answer here
    Must be accomodated by the student_key."""
    try:
        student_key  = request.args.get("key")
        template_key = student_belong_to_session[student_key]
        submitted_answers = request.get_json()
        assert isinstance(submitted_answers, list) and all((a is None or 0 <= a < 4 for a in submitted_answers)), "answers must be list of [0-3]; but is {}".format(submitted_answers)
        student_data = session[template_key]["student"][student_key]
        print(student_data)
        if("answers" in student_data):
            return jsonify(result=False)
        else:
            student_data["answers"] = submitted_answers 
            return jsonify(result=True)
    except Exception as e:
        return jsonify(result=False, error=str(e))

@app.route("/manage")
def manage():
    """Exam maker can access this page to track the current status of the exam; including the choices being made by the student (if chosen to be tracked)
    Not implemented as of now"""
    raise NotImplementedError

if __name__ == "__main__":
    app.run(debug=True)
