"""Routes strictly for the management & showing of exam data on a tabled format."""
import flask
from flask import Flask, request, url_for
import os, time
import traceback 

from src.session import current_data
from src.session import wipe_session # migrate to external module

import logging 
logger = logging.getLogger(__name__)

def build_data_routes(app: Flask) -> Flask:
    ### For generic data table ###
    @app.route("/filtered_questions", methods=["GET"])
    def filtered_questions():
        # same as above; but receiving corresponding category & tag filtering.
        category = request.args.get("category", None)
        if category is None:
            raise NotImplementedError
        tag_raw_filter = request.args.get("tag", None)
        tag_filter = None if tag_raw_filter is None else tag_raw_filter.split(",") if "," in tag_raw_filter else [tag_raw_filter]
        filtered_data = current_data.load_category(category)
        if(tag_filter):
            filtered_data = (q for q in filtered_data if any((t in q.get("tag", []) for t in tag_filter)))
        filtered_data = list(filtered_data)
        start_index = int(request.args.get("start", 0))
        end_index = int(request.args.get("end", int(request.args.get("length", 1000)) + start_index ))
        if(request.args.get("request_tags", "false") == "true"):
            # tag is requested; parse it from all children
            tags = list(set(t for q in filtered_data for t in q.get("tag", ())))
            return flask.jsonify(questions=filtered_data[start_index:end_index], tags=tags, all_length=len(filtered_data))
        else:
            return flask.jsonify(questions=filtered_data[start_index:end_index], all_length=len(filtered_data))

    @app.route("/all_filter", methods=["GET"])
    def all_filter():
        # returning all categoryfrom the current data 
        return flask.jsonify(categories=current_data.categories)

    ### For modification (edit, delete, import, export) ###
    @app.route("/edit")
    def edit():
        """Enter the edit page where we can submit new data to database; rollback and deleting data (preferably duplicated question)
        TODO restrict access
        """
        return flask.render_template("edit.html", title="Modify", questions=[])
    
    @app.route("/delete_questions", methods=["DELETE"])
    def delete_questions():
        # TODO restrict access 
        delete_ids = request.get_json()
        category = request.args.get("category", None)
        if category is None:
            raise NotImplementedError
        if(not delete_ids or not isinstance(delete_ids, (tuple, list)) or len(delete_ids) == 0):
            return flask.jsonify(result=False, error="Invalid ids sent {}({}); try again.".format(delete_ids, type(delete_ids)))
        else:
            # delete by id
            current_data.delete_data_by_ids(category, delete_ids)
            if request.args.get("wipe", "true").lower() == "true":
                # wipe by default, selectively for only this category. TODO evaluate
                wipe_session(for_categories=[category])
    #        if(result["result"]):
    #            nocommit = request.args.get("nocommit")
    #            if(not nocommit or nocommit.lower() != "true"):
    #                # if nocommit is not enabled; push the current data to backup and write down new one 
    #                perform_commit(filepath_dict["current_path"])
            return flask.jsonify(result=True)
    
    @app.route("/export")
    def file_export():
        """Allow downloading the database file."""
        raise NotImplementedError # disable until further sorting out
    #    return flask.send_file(filepath_dict["current_path"], as_attachment=True)
    
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
            current_data.update_data_from_file(temporary_filename)
            wipe_session()
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
            category = request.args.get("category", None)
            if category is None:
                raise NotImplementedError
            if current_data.category_has_rollback(category):
                current_data.rollback_category(category)
                return flask.jsonify(result=True)
            else:
                return flask.jsonify(result=False, error="No backup available")
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.jsonify(result=False, error=str(e))
    
    return app   