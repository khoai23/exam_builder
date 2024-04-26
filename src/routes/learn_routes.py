"""Routes to support teaching through our website.
Should also helps with proper implementation of roles (Teacher / Student should have their own accessibles)."""
import io
import flask
from flask import Flask, request, url_for

import logging 
logger = logging.getLogger(__name__)

DEFAULT_LEARN_XML_POSITION = "test/learn_bpmn.xml"
def build_learn_routes(app: Flask, login_decorator: callable=lambda f: f) -> Flask:
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

    return app

