"""Routes strictly for creation & management of exam sessions. Note that the build page will have to use the data table in the data_routes, but this should not affect anything here."""
import flask
from flask import Flask, request, url_for
import traceback 

from src.session import session
from src.session import load_template, student_first_access_session, student_reaccess_session, retrieve_submit_route_anonymous, retrieve_submit_route_restricted, submit_exam_result, remove_session

import logging 
logger = logging.getLogger(__name__)

def build_session_routes(app: Flask, login_decorator: callable=lambda f: f) -> Flask:
    ### SECTION FOR MAKER ###
    @app.route("/build")
    @login_decorator
    def build():
        """Enter the quiz build page where we can build a new template for an exam 
        Modification is now in a separate page
        TODO restrict access
        """
        return flask.render_template("build.html", title="Data", questions=[])
    
    @app.route("/build_template", methods=["POST"])
    @login_decorator
    def build_template():
        """Template data is to be uploaded on the server; provide an admin key to ensure safe monitoring."""
        data = request.get_json()
        category = request.args.get("category", None)
        if(category is None):
            raise NotImplementedError
        logger.info("@build_template: Received template data: {}".format(data))
        result, (arg1, arg2) = load_template(data, category)
        if(result):
            # return the key to be accessed by the browser
            return flask.jsonify(result=True, session_key=arg1, admin_key=arg2)
        else:
            # return the error and concerning traceback
            return flask.jsonify(result=False, error=str(arg1), error_traceback=str(arg2))
    
    @app.route("/single_manager")
    @login_decorator
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
    @login_decorator
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
    @login_decorator
    def session_manager():
        """Manage all sessions created here."""
        return flask.render_template("session_manager.html", all_session_data=session)
    
    @app.route("/delete_session", methods=["DELETE"])
    @login_decorator
    def delete_session():
        """Only work with a valid admin_key, to prevent some smart mf screwing up sessions."""
        try:
            template_key = request.args.get("template_key")
            admin_key = request.args.get("key")
            return remove_session(template_key, verify=True, verify_admin_key=admin_key)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())
     
    ### SECTION FOR TAKER ### 
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
    
    return app   
