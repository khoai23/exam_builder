"""To update the login/logout"""
import secrets

import flask
from flask import Flask, request, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

from typing import Tuple, List, Optional, Union

import logging 
logger = logging.getLogger(__name__)

class User(UserMixin):
    def __init__(self, username, password, user_id: Optional[str]=None, name: str="N/A", role: int=-1):
        self.id = user_id or secrets.token_hex(8)
        self.username = username 
        self.password = password
        self.name = name 
        self.role = role

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

    def remove_user(user: Union[User, str]):
        # remove the user from the dictionaries 
        if isinstance(user, str):
            # delete by id (str)
            user = user_dict[user]
        user_dict.pop(user.id)
        username_refer_dict.pop(user.username)
        del user

    @app.route("/create_user", methods=["POST"])
    def create_user():
        # TODO only allow creation by important user 
        # TODO prevent duplicate username
        form = request.form.to_dict()
        # check appropriate username, generate id, save password 
        user_id = secrets.token_hex(8)
        while user_id in user_dict:
            # prevent duplication 
            user_id = secrets.token_hex(8)
        new_user = User(form["username"], form["password"], user_id, name=form.get("name", "N/A"), role=form.get("role", None))
        add_user(new_user)
        # if autologin, also log in immediately.
        if request.args.get("autologin", "false") == "true":
            login_user(new_user)
        # which ever cases, back to default
        return flask.redirect(url_for("main"))

    # create first default user (khoai23/khoai23)
    add_user(User("khoai23", "khoai23", "default_admin", name="Creator", role=-1))
    # auto-redirect to the main login page
    manager.login_view = "main"
    manager.init_app(app)

    return app, manager, login_required
