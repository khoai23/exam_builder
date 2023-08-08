import flask
from flask import Flask, request, url_for
# from werkzeug.utils import secure_filename
import os, time, re
import traceback 
import shutil

from src.session import current_data, submit_route 
from src.routes import build_login_routes, build_session_routes, build_data_routes, build_game_routes
from src.parser.convert_file import read_and_convert
from src.crawler.generic import get_text_from_url
from src.data.reader import TEMPORARY_FILE_DIR 
from src.map import generate_map_by_region, generate_map_by_subregion, format_arrow

import logging
logger = logging.getLogger(__name__)

app = Flask("exam_builder")
app.secret_key = "liars_punishment_circle_24102023"
app.config["UPLOAD_FOLDER"] = "test"
# bind appropriate functions
app, login_manager, login_decorator = build_login_routes(app)
app = build_session_routes(app, login_decorator=login_decorator)
app = build_data_routes(app, login_decorator=login_decorator)
_, app = build_game_routes(app, login_decorator=login_decorator)
### TODO The import flow will be split in two parts, modifying and committing
app._is_in_commit = False

@app.route("/")
def main():
    """Enter the index page"""
    return flask.render_template("main.html")

@app.route("/test")
def test():
    """Enter the test page, to put and test new stuff"""
    return flask.render_template("test.html")

@app.route("/map")
def map():
    """Test the draw map. 
    This will be base for us to show a little game board representing progress."""
#    polygons = [(0, 0, 200, 200, [(30, 30), (150, 80), (170, 170), (80, 150)], {"bg": "lime", "fg": "green"})]
    # for now create fake data-region to make map
    reduce_fn = lambda s: "".join([c for c in s if c.isupper() or c.isnumeric()])
    fake_data = [dict(category=reduce_fn(cat), tag=str(i)) for cat in current_data.categories for i in range(6)]
    polygons = generate_map_by_subregion(fake_data, bundled_by_category=False, do_recenter=True, do_shrink=0.98, return_connections=True)
    # testing fake arrow 
#    arrow = format_arrow( ((100, 100), (300, 100)), control_offset=(0, -50), thickness=10)
    arrow_fn = lambda a: (0, 0, 1000, 1000, format_arrow(a, control_offset=(0, -0.5), thickness=10, offset_in_ratio_mode=True))
    # take a random polygon regions and draw all associating arrows 
    target = polygons[-4]
    def get_true_center(region):
        center_x, center_y = region[-1]["center"]
        bound_x, bound_y = region[:2]
        return (bound_x+center_x, bound_y+center_y)
    arrows = [arrow_fn((get_true_center(target), get_true_center(polygons[i]))) for i in target[-1]["connection"] if i != len(polygons)-4]
    # temporary de-clutter all texts
    for p in polygons:
        p[-1].pop("text")
    return flask.render_template("map.html", polygons=polygons, arrows=arrows)

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
    app.run(debug=True)
