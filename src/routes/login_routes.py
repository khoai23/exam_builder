"""To update the login/logout"""
import secrets 
from enum import IntEnum

import flask
from flask import Flask, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required

from typing import Tuple, List, Optional, Union

import logging 
logger = logging.getLogger(__name__)

class UserRole(IntEnum):
    # decreasing in order of rights
    Creator = 1
    Maintainer = 2
    Admin = 3
    Teacher = 4 
    Student = 5 
    
    @staticmethod
    def requiresGrant(role: int):
        # roles that need to be granted by higher-level user; for now teacher & above 
        return role <= UserRole.Teacher 

    @staticmethod
    def allowGrant(initiator_role: int, role: int):
        # check if initiator can grant the specified role. For now each can grant all below.
        return initiator_role < role

class User(UserMixin):
    def __init__(self, username, password, user_id: Optional[str]=None, name: str="N/A", role: UserRole=None):
        self.id = user_id or secrets.token_hex(8)
        self.username = username 
        self.password = password
        self.name = name 
        self.role = role 

    def getRole(self) -> str:
        # return the string variant; TODO proper name e.g administrator?
        return UserRole(self.role).name

class Classroom:
    """A generic class. Should be created & geared toward a single category to make quizzing & teaching simpler."""
    def __init__(self, 
            creator: User, teacher: User, students: List[User], 
            category: str=None, tags: Optional[List[str]]=None,
            strict: bool=True):
        # generic data
        self.creator = creator 
        assert creator.role <= UserRole.Admin, "@Classroom: can only be created with Admin user & above."
        self.teacher = teacher  # TODO allow multiple teachers.
        assert teacher.role <= UserRole.Teacher, "@Classroom: can only be taught with Teacher user & above."
        self.students = students 
        assert all(s.role == UserRole.Student for s in students), "@Classroom: can only be created with Student user."
        self.category = category 
        self.tags = tags
        # learning data - should track the learning progress & result of students. TODO also create appropriate statistic about tags so can concentrate on badly performed subjects
        self._result = {}
        self._exams = {}
        # reference to lesson/quiz maker 

    def update_students(self, add: Optional[List]=None, remove: Optional[List]=None, strict: bool=True):
        """Update the student list - adding or removing."""
        if remove:
            for ra in remove:
                sidx = next((i for i, s in enumerate(self.students) if s.id == ra.id), None)
                if sidx is None:
                    logger.debug("@update_students: Cannot find student {}({}) in class; removal ignored.".format(ra.name, ra.id))
                else:
                    self.students.pop(sidx)
        if add:
            for sa in add:
                assert not strict or sa.role == UserRole.Student, "@update_students: cannot attempt adding non-student to class."
                sidx = next((i for i, s in enumerate(self.students) if s.id == sa.id), None)
                if sidx is not None:
                    logger.debug("@update_students: Student {}({}) already in class; addition ignored.".format(sa.name, sa.id))
                else:
                    self.students.append(sa)

    def create_exam(self, session, category: Optional[str]=None, tags: Optional[str]=None):
        # create a randomized exam on specific category & tag. 
        # TODO automatically compose by hardness.
        # TODO option to specialize the exam for each student, basing on their prior result 
        # TODO report back to the original result once exam closes.
        raise NotImplementedError


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

    return app, manager, login_required
