"""Routes strictly for creation & management of exam sessions. Note that the build page will have to use the data table in the data_routes, but this should not affect anything here."""
import flask
from flask import Flask, request, url_for
from flask_login import current_user
import traceback 

from src.session import ExamManager, convert_template_setting
#from src.session import load_template, student_reaccess_session, retrieve_submit_route_anonymous, retrieve_submit_route_restricted, submit_exam_result, remove_session, convert_template_setting

import logging 
logger = logging.getLogger(__name__)

def build_session_routes(app: Flask, exam_manager: ExamManager, login_decorator: callable=lambda f: f) -> Flask:
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
        result, args = exam_manager.create_new_session(data, category)
        if(result):
            # return the key to be accessed by the browser 
            session_key, admin_key = args
            return flask.jsonify(result=True, session_key=session_key, admin_key=admin_key)
        else:
            # return the error and concerning traceback 
            error_traceback = "\n".join(traceback.format_exception(args))
            return flask.jsonify(result=False, error=str(args), error_traceback=error_traceback)
    
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
            session = exam_manager.get_session(template_key)
            logger.debug("Access session data: {} by key {}".format(session, template_key))
            if not session:
                return flask.render_template("error.html", error="Invalid session key.", error_traceback=None)
            if(admin_key == session["admin_key"]):
                return flask.render_template("single_manager.html", session_data=session, template_key=template_key)
            else:
                return flask.render_template("error.html", error="Invalid admin key.", error_traceback=None)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())
    
    @app.route("/single_session", methods=["GET"])
    @login_decorator
    def single_session():
        """Retrieving the exact same data being ran on single_manager.
        TODO use this to autoupdate result."""
        template_key = request.args.get("template_key")
        admin_key = request.args.get("key")
        if(template_key is None or admin_key is None):
            return flask.jsonify(result=False, error="Missing key, data cannot be retrieved.")
        session = exam_manager.get_session(template_key)
        if session is None:
            return flask.jsonify(result=False, error="Invalid key {:s}, session not found.".format(template_key))
        if(admin_key == session["admin_key"]):
            return flask.jsonify(result=True, data=session)
        else:
            return flask.jsonify(result=False, error="Admin key incorrect, data cannot be retrieved.")
    
    @app.route("/update_setting_session", methods=["POST"])
    @login_decorator
    def update_setting_session():
        """Allow changing specific part of the session, e.g setting. Will throw an error if something failed."""
        template_key = request.args.get("template_key")
        admin_key = request.args.get("key")
        if(template_key is None or admin_key is None):
            return flask.jsonify(result=False, error="Missing key, modification failed.")
        data = request.get_json()
        # TODO safe-check important setting argument later 
        session = exam_manager.get_session(template_key, None)
        if session is None:
            return flask.jsonify(result=False, error="Invalid key {:s}, session not found.".format(template_key))
        if(admin_key == session["admin_key"]):
            # reconvert appropriate setting
            session["setting"].update(convert_template_setting(data, allow_student_list=False))
            return flask.jsonify(result=True)
        else:
            return flask.jsonify(result=False, error="Admin key incorrect, setting cannot be changed.")
        


    @app.route("/session_manager")
    @login_decorator
    def session_manager():
        """Manage all sessions created here."""
        return flask.render_template("session_manager.html", all_session_data=exam_manager._session)
    
    @app.route("/delete_session", methods=["DELETE"])
    @login_decorator
    def delete_session():
        """Only work with a valid admin_key, to prevent some smart mf screwing up sessions."""
        try:
            template_key = request.args.get("template_key")
            admin_key = request.args.get("key")
            return exam_manager.delete_session(template_key, verify=True, verify_admin_key=admin_key)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())
     
    ### SECTION FOR TAKER ### 
    @app.route("/identify", methods=["GET", "POST"])
    def identify():
        """First part of entering the exam; this link will allow student to input necessary info to be monitored by /manage
        The form should trigger the generic_submit redirect and go to /enter after it."""
        template_key = request.args.get("template_key", None)
        if(template_key is None):
            return flask.render_template("error.html", error="No session key specified. You need one to enter the correct test/exam.", error_traceback=None)
        else:
            if request.method == "GET":
                # with a template key, trying access - render generic_input that send POST to itself with all the necessary identifier
                try:
                    session = exam_manager.get_session(template_key)
                    if(session is None):
                        return flask.render_template("error.html", error="Invalid session key; the session might be expired or deleted.")
                    student_list = session["setting"].get("student_list", None)
                    logger.info("Checking against student list: {}".format(student_list))
                    if(student_list is not None):
                        if(isinstance(student_list, list) and len(student_list) > 0):
                            # a valid student list; use restricted access
                            if current_user:
                                # search for the user in the list; if cannot found, throw error
                                entry_key = next((key for key, stdinfo in session["student"].items() if stdinfo["id"] == current_user.id), None)
                                if entry_key is None:
                                    raise SessionError("User of id \"{:s}\" is not part of the exam, access not granted")
                                return flask.redirect(url_for("enter", key=entry_key)) #
                            else:
                                raise SessionError("Exam in restricted access mode; unsigned access is not allowed. For now.")
                            # 
#                            return flask.render_template("generic_input.html", title="Enter Exam", message="The exam is restricted to specific students. Enter provided key to access the exam.", submit_route="identify?template_key={:s}".format(template_key), submit_key=template_key, custom_navbar=True, input_fields=[{"id": "key", "type": "text", "name": "Entry Key"}])
                        else:
                            # invalid student list; voiding 
                            logger.error("Invalid student list found: {}; voiding".format(student_list))
                            session["setting"].pop("student_list", None)
                    # once reached here, the submit_route should have a valid dict ready; redirect to the generic_input html 
                    # use sorta anonymous access here 
                    # TODO use what the session requests instead.
                    return flask.render_template("generic_input.html", title="Enter Exam", message="The exam is unrestricted. Make sure to keep the link after identifying yourself - multiple submissions may be penalized.", submit_route="identify?template_key={:s}".format(template_key), submit_key=template_key, custom_navbar=True, input_fields=[
                        {"id": "id", "type": "text", "name": "Student ID"},
                        {"id": "name", "type": "text", "name": "Student Name"}])
                except Exception as e:
                    logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
                    return flask.render_template("error.html", error=str(e), error_traceback=traceback.format_exc())
            else:
                # POST mode; if anonymous, create the new entry key here.
                # either way, redirect to /enter subsection with it.
                data = request.form.to_dict()
                if "key" in data:
                    # restricted mode
                    # result, page_or_error = exam_manager.student_enter_session(first_access=False, key=data["key"])
                    return flask.redirect(url_for("enter", key=data["key"]))
                else:
                    # anonymous mode, generate a matching key & redirect to enter
                    result, page_or_error = exam_manager.student_enter_session(first_access=True, session_key=template_key, id=data["id"], name=data["name"])
                    if result:
                        key, page_props = page_or_error
                        return flask.redirect(url_for("enter", key=key)) 
                    else:
                        return flask.render_template("error.html", error=page_or_error, error_traceback=None)
    
    @app.route("/enter")
    def enter():
        """Enter the exam.
        If the student_key is not available, a specific student key is generated and used to track individual result.
        Subsequent access with student_key will relaunch the same test, preferably with the choices ready
        TODO disallow entering when not in start_exam_date -> end_exam_date; or time had ran out."""
        student_key = request.args.get("key", None)
        if(student_key):
            result, page_or_error = exam_manager.student_enter_session(first_access=False, key=student_key)
            if result:
                key, page_props = page_or_error # this return the formatting used for the page; TODO verify student_key = key
                return flask.render_template("exam.html", **page_props)
            else:
                return flask.render_template("error.html", error=page_or_error, error_traceback=None) # something failed; use generic
        else:
            # no longer allowed - anonymous or restricted must both redirect to here with a key
#            raise NotImplementedError
            return flask.render_template("error.html", error="Keyless access to exam is prohibited.", error_traceback=None)
#            template_key = request.args.get("template_key", None)
#            return student_first_access_session(template_key)
    
    
    @app.route("/submit", methods=["POST"])
    def submit():
        """Student will submit there answer here
        Must be accomodated by the student_key."""
        try:
            student_key  = request.args.get("key")
            submitted_answers = request.get_json()
            result, page_or_error = exam_manager.student_submit_answers(submitted_answers, student_key)
            if result:
                return page_or_error
            else:
                return flask.jsonify(result=False, error=str(page_or_error), error_traceback=None)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.jsonify(result=False, error=str(e), error_traceback=traceback.format_exc())
    
    return app   
