from collections import defaultdict 
import random

from src.authenticate.user import User, UserRole

from typing import Tuple, List, Optional, Union

import logging 
logger = logging.getLogger(__name__)

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

    def create_exam(self, exam_manager, category: Optional[str]=None, tags: Optional[str]=None, use_unrated: bool=True):
        # create a randomized exam on specific category & tag. 
        # TODO report back to the original result once exam closes. Probably need upgrading the "session"
        category = category or self.category
        tags = tags or self.tags 
        questions = exam_manager.quiz_data.load_category(category)
        if tags:
            matched = [i for i, q in enumerate(questions) if any(t in tags for t in q["tag"] )]
            raise NotImplementedError
        else:
            matched = list(range(len(questions)))
        # TODO automatically compose by hardness.
        split_by_hardness = defaultdict(set)
        for i in matched:
            hardness = questions[i].get("hardness", None)
            if not isinstance(hardness, int) or 0 >= hardness or 10 < hardness:
                hardness = None # voiding invalid hardness values
            split_by_hardness[hardness].add(i)
        if not use_unrated:
            del split_by_hardness[None] # do not allow any non-rated question 
        # TODO option to specialize the exam for each student, basing on their prior result. This can't use the template variant ofc.
        # for now just select maximum of 4 hardness type; preferring in order of (defined hardness, >10 questions), (undefined hardness, >10 question), (defined hardness, <10 questions), (undefined hardness, <10 questions)
        selected = list(sorted(split_by_hardness.items(), key=lambda x: (len(x[1]) >= 10, x[0] is not None)))[:4]
        # reorganize & assign score; the harder the score the less point given. 
        # unrated is considered 4.5 for this reorganizing option
        # if 1 cat, 5q of 2p; if 2cat, 3q of easy 3p + 1q of hard 1p; if 3cat, 2q of easy 4p + 1q of harder 1p each; if 4cat, 4q of 4-3-2-1
        qcount_and_score = {1: [(5, 2)], 2: [(3, 3), (1, 1)], 3: [(2, 4), (1, 1), (1, 1)], 4: [(4, 1), (3, 1), (2, 1), (1, 1)]}
        template = [
            (qcount, score, list(all_qids))
            for (qcount, score), (hardness, all_qids) in zip(qcount_and_score[len(selected)], sorted(selected, key=lambda x: x[0] or 4.5))
        ]
        logger.info("Generated template on current data: selected-hardness: {}; generated template {}".format(list(zip(*selected))[0], template))
        # create the appropriate setting object. For now just make it 
        setting = dict(session_name="Generic Exam #{:04d}".format(int(random.random() * 10000)), allow_score=True, allow_result=True, student_list=[std.getUserInfo(internal_use=True) for std in self.students])
        return exam_manager.create_new_session({"template": template, "setting": setting}, category)


def test_autogen_test_classroom(exam_manager, add_user):
    # creating a sample classroom & autogenerate using it.
    example_user_1 = User("test_1", "testpwd", "test_student_1", name="Test Student 1", role=UserRole.Student)
    example_user_2 = User("test_2", "testpwd", "test_student_2", name="Test Student 2", role=UserRole.Student)

    example_teacher = User("test_0", "testpwd", "test_teacher", name="Test Teacher", role=UserRole.Admin)
    
    for u in [example_teacher, example_user_1, example_user_2]:
        add_user(u)
    
    classroom = Classroom(example_teacher, example_teacher, [example_user_1, example_user_2], "GDCD", None)

    result, args = classroom.create_exam(exam_manager)
    if result:
        logger.info("Successfully created the exam; session key {}, admin key {}".format(*args))
        return classroom, args
    else:
        logger.error("Cannot create the exam; make sure to check the traceback.")
        logger.error("Error: {}\nTraceback: {}".format(args))
        return classroom, None
