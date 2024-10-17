import flask
from flask import Flask, request, url_for 
from flask_login import current_user
# from werkzeug.utils import secure_filename
import os, time, re, sys, random
import traceback 
import shutil

from src.authenticate.user import UserRole
from src.session import ExamManager, OnRequestData 
from src.course.classroom import test_autogen_test_classroom
from src.routes import build_login_routes, build_session_routes, build_data_routes, build_game_routes, build_learn_routes
from src.parser.convert_file import read_and_convert
from src.crawler.generic import get_text_from_url
from src.data.reader import TEMPORARY_FILE_DIR 
from src.data.markdown_load import MarkdownData
from src.map import generate_map_by_region, generate_map_by_subregion, format_arrow  
from src.generator.scheduler import initiate_scheduler

import logging
logger = logging.getLogger(__name__)

# default app
app = Flask("exam_builder")
app.secret_key = "liars_punishment_circle_24102023"
app.config["UPLOAD_FOLDER"] = "test"
app.scheduler = scheduler = initiate_scheduler()
# related session/questions data; 
quiz_data = OnRequestData()
lessons_data = MarkdownData()
classroom_data = dict()
exam_manager = ExamManager(quiz_data, scheduler)
# bind appropriate functions
app, login_manager, login_decorator = build_login_routes(app)
app = build_session_routes(app, exam_manager, login_decorator=login_decorator)
app = build_data_routes(app, exam_manager, login_decorator=login_decorator)
app = build_learn_routes(app, login_decorator=login_decorator, lessons_data=lessons_data, classroom_data=classroom_data)
_, app = build_game_routes(app, exam_manager, login_decorator=login_decorator) 

### TODO The import flow will be split in two parts, modifying and committing. right now modifying + commiting is one action
app._is_in_commit = False

@app.route("/")
def main():
    """Enter the main page. Either enforce login if not authenticated; or showing a little splash page if do.
    Should show the classes that you are attending/teaching/managing etc."""
    authenticated = current_user.is_authenticated 
    if authenticated:
        action = "attending" if current_user.role == UserRole.Student \
            else "teaching"  if current_user.role == UserRole.Teacher else "managing"
        if current_user.classes:
            classes_link = ["<b><a href=\"class/{:s}\">{:s}</a></b>".format(cls.id, cls.name) for cls in current_user.classes.values()]
            if len(classes_link) <= 2:
                classes_link_full = "and".join(classes_link)
            else:
                classes_link_full = ", ".join(classes_link[:-1]) + " and " + classes_link[-1]
            additional_info = "You are {:s} <b>{:d}</b> classes. Those are: {:s}".format(action, len(current_user.classes),  classes_link_full)
        else:
            additional_info = "You are not {:s} any classes.".format(action)
    else:
        additional_info = None
    return flask.render_template("main.html", authenticated=authenticated, additional_info=additional_info)

@app.route("/test")
def test():
    """Enter the test page, to put and test new stuff"""
    return flask.render_template("test.html", content="# Dummydata\nThis should be parsed by markdown.")

@app.route("/retrieve_text", methods=["GET"])
def retrieve_text():
    # read a specified html and strip it down to pure text.
    url = request.args.get("url");
    if(url is None):
        return flask.jsonify(result=False, error="URL not specified.")
    try:
        return flask.jsonify(result=True, data=get_text_from_url(url))
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        return flask.jsonify(result=False, error=str(e))
   
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
    raise NotImplementedError("Dont need this level of complexity yet")
    try:
        logger.info("Entering generic_submit...")
        form = request.form.to_dict()
        submit_id = form.pop("id")
        if submit_id not in submit_route:
            logger.warning("Cannot found route id: ", submit_id)
            flask.flash("No such route id: {}".format(submit_id), "danger")
            flask.redirect(request.referrer)
            # return flask.jsonify(result=False, error="No route id available")
        result_blob = submit_route[submit_id](**form)
        if(isinstance(result_blob, str) or not isinstance(result_blob, (list, tuple))):
            # upon data being a redirect blob; just throw it back
            return result_blob 
        else:
            result, data_or_error = result_blob 
            # result must ALWAYS be false in this case 
            logger.warning("Error from submit_route: {}".format(data_or_error))
            flask.flash("Submit error: {}".format(data_or_error), "danger")
            # TODO show the error 
            return flask.redirect(request.referrer)
    except Exception as e:
        logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
        # back to the previous (identify page); 
        flask.flash("Error: {}".format(e), "danger")
        return flask.redirect(request.referrer)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "log" in sys.argv:
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for logger in loggers:
            logger.setLevel(logging.DEBUG)
    if "test" in sys.argv:
        # Autogen for specific 
        classroom, keys_if_any = test_autogen_test_classroom(exam_manager, app.add_user)
        if keys_if_any:
            test_exam_key, test_admin_key = keys_if_any
            print("Created classroom {} with test exam {}(adminkey {})".format(classroom, test_exam_key, test_admin_key))
            classroom_data[classroom.id] = classroom
    app.run(debug=True)
