import secrets 
from enum import IntEnum

from flask_login import UserMixin

from typing import Tuple, List, Optional, Union

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
    def __init__(self, username, password, user_id: Optional[str]=None, name: str="N/A", role: UserRole=None, info: Optional[dict]=None):
        self.id = user_id or secrets.token_hex(8)
        self.username = username 
        self.password = password
        self.role = role 
        # non-critical-to-operation info.
        self.name = name 
        self.info = info or dict()

    def getRole(self) -> str:
        # return the string variant; TODO proper name e.g administrator?
        return UserRole(self.role).name 

    def updateUserInfo(self, **kwargs):
        # update all whatever non-critical stuff we want.
        self.info.update(**kwargs)
