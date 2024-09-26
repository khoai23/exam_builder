import secrets 
from enum import IntEnum

from flask_login import UserMixin

from typing import Tuple, List, Optional, Union

class UserRole(IntEnum):
    # decreasing in order of rights
    Creator = 1
    Maintainer = 2
    # leave gaps in case there is a mixed role 
    Admin = 4
    Teacher = 8
    Student = 12
    
    @staticmethod
    def requiresGrant(role: int):
        # roles that need to be granted by higher-level user; for now teacher & above 
        return role <= UserRole.Teacher 

    @staticmethod
    def allowGrant(initiator_role: int, role: int):
        # check if initiator can grant the specified role. For now each can grant all below.
        return initiator_role < role

    @staticmethod
    def allowModifyExamData(role: int):
        # check if role can modify data; for now restrict to Admin 
        return role <= UserRole.Admin 

    @staticmethod
    def allowCreateExam(role: int):
        # check if role allow creating & managing exams 
        return role <= UserRole.Teacher

class User(UserMixin):
    def __init__(self, username, password, user_id: Optional[str]=None, name: str="N/A", role: UserRole=None, info: Optional[dict]=None):
        self.id = user_id or secrets.token_hex(8)
        self.username = username 
        self.password = password
        self.role = role 
        # operation info 
        # For admin+, classes is what they administors; for teacher, classes is what they teach; for student, classes is what they attend
        self.classes = dict()
        # non-critical-to-operation info.
        self.name = name 
        self.info = info or dict()

    def getRole(self) -> str:
        # return the string variant; TODO proper name e.g administrator?
        return UserRole(self.role).name 

    def updateUserInfo(self, **kwargs):
        # update all whatever non-critical stuff we want.
        self.info.update(**kwargs)

    def getUserInfo(self, internal_use: bool=False):
        # if internal_use; also return specifics that is only relevant to internal logic (e.g user id)
        if internal_use:
            return {"id": self.id, "name": self.name, **self.info}
        else:
            return dict(self.info)

    def can_do(self, task: str):
        # shortcut to check with userrole 
        if task == "modify":
            return UserRole.allowModifyExamData(self.role)
        elif task == "create_exam":
            return UserRole.allowCreateExam(self.role)
        else:
            raise ValueError("Invalid query, cannot find required task \"{}\" of the system.".format(task))
