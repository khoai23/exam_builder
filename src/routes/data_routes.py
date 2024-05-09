"""Routes strictly for the management & showing of exam data on a tabled format."""
import flask
from flask import Flask, request, url_for
import sass
import os, time
import traceback 

from src.session import current_data, TEMPORARY_FILE_DIR
from src.session import wipe_session # migrate to external module

import logging 
logger = logging.getLogger(__name__)

def build_data_routes(app: Flask, login_decorator: callable=lambda f: f) -> Flask:
    # prerequisite sass; TODO later when I'm less lazy
    ### For generic data table ###
    @app.route("/filtered_questions", methods=["GET"])
    @login_decorator
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
        # if supply hardness = -1 or specific; 
        hardness = int(request.args.get("hardness", 0))
        if hardness == 0:
            # accept all hardness
            pass
        elif 1 <= hardness <= 10:
            # filter only the ones that match 
            filtered_data = (q for q in filtered_data if int(q.get("hardness", 0) or 0) == hardness)
        elif hardness == -2:
            # filter only the "rated one"
            filtered_data = (q for q in filtered_data if 1 <= int(q.get("hardness", 0) or 0) <= 10)
        else:
            # filter all "unrated" (None or outside boundary)
            filtered_data = (q for q in filtered_data if not 1 <= int(q.get("hardness", 0) or 0) <= 10 )

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
    @login_decorator
    def all_filter():
        # returning all categoryfrom the current data 
        return flask.jsonify(categories=current_data.categories)

    ### For modification (edit, delete, import, export) ###
    @app.route("/edit")
    @login_decorator
    def edit():
        """Enter the edit page where we can submit new data to database; rollback and deleting data (preferably duplicated question)
        TODO restrict access
        """
        return flask.render_template("edit.html", title="Modify", display_legend=True, questions=[], editable=True)
    
    @app.route("/delete_questions", methods=["DELETE"])
    @login_decorator
    def delete_questions():
        """Delete selected questions in specific category. Should allow a rollback."""
        delete_ids = request.get_json()
        category = request.args.get("category", None)
        if category is None:
            return flask.jsonify(result=False, error="Must supply a valid category to delete") 
        if(not delete_ids or not isinstance(delete_ids, (tuple, list)) or len(delete_ids) == 0):
            return flask.jsonify(result=False, error="Invalid ids sent {}({}); try again.".format(delete_ids, type(delete_ids)))
        else:
            # delete by id. TODO ensure rollback capacity
            current_data.delete_data_by_ids(delete_ids, category)
            if request.args.get("wipe", "true").lower() == "true":
                # wipe by default, selectively for only this category. TODO evaluate
                wipe_session(for_categories=[category])
            return flask.jsonify(result=True)
    
    @app.route("/modify_question", methods=["POST"])
    @login_decorator
    def modify_question():
        """Modify a selected question with a specific value. Best to attempt associating rollback once done."""
        modify_data = request.get_json()
        category = request.args.get("category", None)
        if category is None:
            return flask.jsonify(result=False, error="Must supply a valid category to modify")  
        if any(key not in modify_data for key in ("id", "field", "value")):
            return flask.jsonify(result=False, error="Must supply valid modification data to allow changing")
        current_data.modify_data_by_id(int(modify_data["id"]), category, modify_data["field"], modify_data["value"])
        if request.args.get("wipe", "false").lower() == "true":
            wipe_session(for_categories=[category]) # only wipe when asked
        return flask.jsonify(result=True)

    @app.route("/swap_category", methods=["POST"])
    @login_decorator
    def swap_category():
        """Swapping questions to a new category. This probably can't allow a rollback, but if it does, great."""
        swap_ids = request.get_json()
        category = request.args.get("from", None)
        new_category = request.args.get("to", None)
        if category is None or new_category is None:
            return flask.jsonify(result=False, error="Must supply valid categories to swap") 
        if(not swap_ids or not isinstance(swap_ids, (tuple, list)) or len(swap_ids) == 0):
            return flask.jsonify(result=False, error="Invalid ids sent {}({}); try again.".format(swap_ids, type(swap_ids)))
        else:
            current_data.swap_to_new_category(swap_ids, category, new_category)
            if request.args.get("wipe", "true").lower() == "true":
                # wipe by default, selectively for only this category. TODO evaluate
                wipe_session(for_categories=[category, new_category])
            return flask.jsonify(result=True)

    @app.route("/add_tag", methods=["POST"])
    @login_decorator
    def add_tag():
        """Add a new tag into existing questions."""
        target_ids = request.get_json()
        category = request.args.get("category", None)
        tag = request.args.get("tag", None)
        if category is None or tag is None:
            return flask.jsonify(result=False, error="Must supply valid category & tag to add") 
        if(not target_ids or not isinstance(target_ids, (tuple, list)) or len(target_ids) == 0):
            return flask.jsonify(result=False, error="Invalid ids sent {}({}); try again.".format(target_ids, type(target_ids)))
        else:
            # simply update all tags of targetted ids 
            strict = request.args.get("strict", "false").lower() == "true"
            warnings = []
            data = current_data.load_category(category)
            for i in target_ids:
                if tag in data[i].get("tag", []):
                    if strict:
                        # break immediately. TODO revert appropriate changes 
                        return flask.jsonify(result=False, error="Mismatch add request: question {} already have tag {}".format(i, tag))
                    else:
                        warnings.append("Question {:d} already have tag {}, ignoring.".format(i, tag))
                elif "tag" in data[i]:
                    data[i]["tag"].append(tag)
                else:
                    data[i]["tag"] = [tag]
            # once everything is done, re-write to disk
            current_data.update_category(category, data)
            return flask.jsonify(result=True, warnings=warnings)

    @app.route("/remove_tag", methods=["POST"])
    @login_decorator
    def remove_tag():
        """Remove a tag from existing questions."""
        target_ids = request.get_json()
        category = request.args.get("category", None)
        tag = request.args.get("tag", None)
        if category is None or tag is None:
            return flask.jsonify(result=False, error="Must supply valid category & tag to add") 
        if(not target_ids or not isinstance(target_ids, (tuple, list)) or len(target_ids) == 0):
            return flask.jsonify(result=False, error="Invalid ids sent {}({}); try again.".format(target_ids, type(target_ids)))
        else:
            strict = request.args.get("strict", "false").lower() == "true"
            warnings = []
            data = current_data.load_category(category)
            for i in target_ids:
                if tag not in data[i].get("tag", []):
                    if strict:
                        # break immediately. TODO revert appropriate changes 
                        return flask.jsonify(result=False, error="Mismatch add request: question {} already have tag {}".format(i, tag))
                    else:
                        warnings.append("Question {:d} does not have tag {}, ignoring.".format(i, tag))
                else:
                    data[i]["tag"].remove(tag)
                    if len(data[i]["tag"]) == 0: # no more tag, throw away the property 
                        data[i].pop("tag")
            # once everything is done, re-write to disk
            current_data.update_category(category, data)
            return flask.jsonify(result=True, warnings=warnings)

    @app.route("/export")
    @login_decorator
    def file_export():
        """Allow downloading the database file."""
        current_category = current_data.current_category
        current_category_path = current_data._data[current_category]
        logger.debug("Attempting export for {} with path {}".format(current_category, current_category_path))
        if current_category_path:
            return flask.send_file(current_category_path, as_attachment=True)
        return flask.jsonify(result=False, error="Invalid category_path {} for category {}; the operation is not possible".format(current_category_path, current_category))
    #    raise NotImplementedError # disable until further sorting out
    #    return flask.send_file(filepath_dict["current_path"], as_attachment=True)
    
    @app.route("/import", methods=["POST"])
    @login_decorator
    def file_import():
        """Allow overwriting or appending to the database file.
        TODO this is allowing multiple category at the same time; maybe add an enforce_category mode so it can only affect one """
        try:
            is_replace_mode = request.args.get("replace", "false").lower() == "true"
            file = request.files["file"]
            _, file_extension = os.path.splitext(file.filename)
            # use timestamp as filename for temporary file
            temporary_filename = os.path.join(TEMPORARY_FILE_DIR, str(int(time.time())) + file_extension)
            file.save(temporary_filename)
            # performing the importing procedure; ALWAYS creating backup to be used with rollback
            current_data.update_data_from_file(temporary_filename, replacement_mode=is_replace_mode)
            wipe_session()
            return flask.jsonify(result=True)
        except Exception as e:
            logger.error("Error: {}; Traceback:\n{}".format(e, traceback.format_exc()))
            return flask.jsonify(result=False, error=str(e))
        finally:
            keep_backup = request.args.get("keep_backup", "false")
            if(not keep_backup or keep_backup.lower() != "true"):
                if(os.path.isfile(temporary_filename)):
                    logger.info("Finished with import file: {}; removing.".format(temporary_filename))
                    os.remove(temporary_filename)
    #    raise NotImplementedError
    
    @app.route("/rollback")
    @login_decorator
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
