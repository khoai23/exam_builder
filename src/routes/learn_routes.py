"""Routes to support teaching through our website.
Should also helps with proper implementation of roles (Teacher / Student should have their own accessibles)."""
import io
import flask
from flask import Flask, request, url_for
from flask_login import current_user

import logging 
logger = logging.getLogger(__name__)

DEFAULT_LEARN_XML_POSITION = "test/learn_bpmn.xml"
def build_learn_routes(app: Flask, login_decorator: callable=lambda f: f, lessons_data: dict=None, classroom_data: dict=None) -> Flask:
    # generic section.

    # experiment: brainstorm-like mind map to allow running around in it?
    # much more functionality than required; a happy surprise. Anyway, should make teacher side much more convenient to build up
    @app.route("/self_learn")
    @login_decorator
    def self_learn():
        return flask.render_template("self_learn.html", can_model=True)

    @app.route("/self_learn_upload", methods=["POST"])
    def self_learn_upload():
        # allow uploading the saved xml from bpmn into local storage.
        try:
            content = request.data#.files["file"]
            with io.open(DEFAULT_LEARN_XML_POSITION, "w") as wf:
                wf.write(content.decode("utf-8"))
#            file.save(DEFAULT_LEARN_XML_POSITION)
        except Exception as e:
            return flask.jsonify(result=False, error=str(e))
        return flask.jsonify(result=True, uploaded_location=DEFAULT_LEARN_XML_POSITION)

    @app.route("/self_learn_download", methods=["GET"])
    def self_learn_download():
        # allow downloading the content of the saved xml 
        try: 
            with io.open(DEFAULT_LEARN_XML_POSITION, "r") as rf:
                data = rf.read()
            return flask.jsonify(result=True, data=data)
        except Exception as e:
            return flask.jsonify(result=False, error=str(e))

    # experiment - markdown-based text lesson. Should allow jumping around 
    @app.route("/learn", methods=["GET"])
    def learn():
        lesson_key = request.args.get("key", None)
        if lesson_key is None:
            # TODO use a default path when we has everything.
            return flask.render_template("error.html", error="Must supply a lesson key to access.", error_traceback=None)
        lesson_data = lessons_data.get(lesson_key)
        if not lesson_data:
            return flask.render_template("error.html", error="Invalid lesson key ({}). Check if you used the right link.".format(lesson_key), error_traceback=None)
        else:
            return flask.render_template("graph_learn.html", content=lesson_data)

    @app.route("/class/<class_id>", methods=["GET"])
    @login_decorator
    def enter_class(class_id: str):
        # retrieving & entering the classes interface; should allow access only when it's admin/teacher/student of the class, or 
#        raise NotImplementedError
        classroom = classroom_data.get(class_id, None)
        if classroom is None:
            return flask.render_template("error.html", error="Trying to access an invalid classroom key (\"{}\").".format(class_id))
        display_data = classroom.get_classroom_data(current_user.id)
        return flask.render_template("classroom.html", class_id=class_id, user_id=current_user.id, **display_data)

    return app

