"""To update the login/logout"""
import secrets 

import flask
from flask import Flask, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required

from src.authenticate.user import User, UserRole 

from typing import Tuple, List, Optional, Union

import logging 
logger = logging.getLogger(__name__)

def build_login_routes(app: Flask) -> Tuple[Flask, LoginManager, callable]:
    """Build appropriate login routes, interface and support."""
    manager = LoginManager()
    user_dict = dict()
    username_refer_dict = dict()

    @manager.user_loader
    def load_user(user_id):
        return user_dict.get(user_id, None)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = request.form.to_dict()
        targetted_id = username_refer_dict.get(form["username"], None)
        if targetted_id is None:
            flask.flash("Invalid username.", "danger")
            return flask.redirect(request.referrer)
        user = user_dict.get(targetted_id, None)
        if user is None:
            logger.warning("Residue username referrer: {}; wiping it.".format(form["username"]))
            username_refer_dict.pop(form["username"])
            flask.flash("Invalid username.", "danger")
            return flask.redirect(request.referrer)
        if user.password != form["password"]:
            flask.flash("Wrong password.", "danger")
            return flask.redirect(request.referrer)
        # check everything ok, sign in 
        login_user(user)
        return flask.redirect(url_for("main")) # go back to default 

    @app.route("/logout", methods=["GET"])
    def logout():
        logout_user()
        flask.flash("User logged out.", "success")
        return flask.redirect(url_for("main"))

    def add_user(user: User):
        # add new user into the dictionaries, to be referred as needed
        user_dict[user.id] = user 
        username_refer_dict[user.username] = user.id 

    def remove_user(user: Union[User, str]) -> bool:
        # remove the user from the dictionaries 
        if isinstance(user, str):
            # delete by id (str)
            user = user_dict.get(user, None)
        if not isinstance(user, User):
            return False
        user_dict.pop(user.id)
        username_refer_dict.pop(user.username)
        del user 
        return True

    @app.route("/create_user", methods=["GET", "POST"])
    @login_required
    def create_user():
        if request.method == "GET":
            initiator_role = current_user.role
            createable_roles = [(r.name, r.name) for r in [UserRole.Admin, UserRole.Teacher, UserRole.Student] if UserRole.allowGrant(initiator_role, r)]
            # launch the barebone creation page, using generic_input
            return flask.render_template("generic_input.html", 
                        title="Create User",
                        message="Create a new user. You are limited to the roles allowed in the dropdown.", 
                        submit_route="create_user",
                        submit_key="unused",
                        custom_navbar=True,
                        input_fields=[
                            {"id": "username", "type": "text", "name": "Username"},
                            {"id": "password", "type": "text", "name": "Password"},
                            {"id": "name", "type": "text", "name": "Display Name"},
                            {"id": "role", "type": "dropdown", "name": "Role", "options": createable_roles}
                        ])
        # TODO only allow creation of higher-up positions by important user 
        # TODO prevent duplicate username
        form = request.form.to_dict()
        # check appropriate username, generate id, save password 
        user_id = secrets.token_hex(8)
        while user_id in user_dict:
            # prevent duplication 
            user_id = secrets.token_hex(8)
        # get the appropriate role item
        role_cue = form.get("role", None)
        if isinstance(role_cue, str):
            role_cue = role_cue.strip()
            # upload cue in string mode; try to retrieve it from the UserRole enum 
            role = getattr(UserRole, role_cue[0].upper() + role_cue[1:].lower(), None)
        elif isinstance(role_cue, int):
            # upload cue in int mode; just use
            role = UserRole(role_cue)
        else:
            role = None
        if role is None:
            # cannot create a matching role; return the associating error 
            flask.flash("Cannot find role \"{}\"; user cannot be created.".format(role_cue))
            return flask.redirect(request.referrer)
        if UserRole.allowGrant(current_user.role, role):
            flask.flash("You don't have enough permission, role \"{}\" cannot be created.".format(role_cue))
            # anonymous/insufficient permission, cannot create specialized role; return the associating error 
            return flask.redirect(request.referrer)
        new_user = User(form["username"], form["password"], user_id, name=form.get("name", "N/A"), role=role)
        add_user(new_user)
        # if autologin, also log in immediately.
        if request.args.get("autologin", "false") == "true":
            login_user(new_user)
        # which ever cases, back to default
        return flask.redirect(url_for("main"))
    
    @app.route("/test_user")
    @login_required
    def test_user():
        print("User: ", current_user.username, " ID: ", current_user.id, "role: ", current_user.role)
        return flask.jsonify(done=True)

    # create first default user (khoai23/khoai23)
    add_user(User("khoai23", "khoai23", "default_admin", name="Khoai", role=UserRole.Creator))
    # auto-redirect to the main login page
    manager.login_view = "main"
    manager.init_app(app)
    # bind directly to the app object; TODO generalize & not rely on ducttaping?
    app.add_user = add_user
    app.remove_user = remove_user

    return app, manager, login_required 
