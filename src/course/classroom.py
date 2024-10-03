from collections import defaultdict 
import random

from src.authenticate.user import User, UserRole

from typing import Tuple, List, Optional, Union

import logging 
logger = logging.getLogger(__name__)

class Classroom:
    """A generic class. Should be created & geared toward a single category to make quizzing & teaching simpler."""
    def __init__(self, class_id: str, class_name: str,
            creator: User, teacher: User, students: List[User], 
            category: str=None, tags: Optional[List[str]]=None,
            strict: bool=True):
        self.id = class_id 
        self.name = class_name
        # generic data
        assert creator.role <= UserRole.Admin, "@Classroom: can only be created with Admin user & above."
        self.creator = creator
        creator.classes[class_id] = self
        assert teacher.role <= UserRole.Teacher, "@Classroom: can only be taught with Teacher user & above."
        self.teacher = teacher  # TODO allow multiple teachers.
        teacher.classes[class_id] = self
        assert all(s.role == UserRole.Student for s in students), "@Classroom: can only be created with Student user."
        self.students = students 
        for s in students:
            s.classes[class_id] = self
        self.category = category 
        self.tags = tags
        # learning data - should track the learning progress & result of students. TODO also create appropriate statistic about tags so can concentrate on badly performed subjects
        self._result = {}
        self._exams = {}
        # posting - allow teacher to build up self-learning lessons 
        # reference to lesson/quiz maker?

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

    def create_exam(self, exam_manager, category: Optional[str]=None, tags: Optional[str]=None, use_unrated: bool=False, add_to_class: bool=True):
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
            (min(qcount, len(all_qids)), score, list(all_qids))
            for (qcount, score), (hardness, all_qids) in zip(qcount_and_score[len(selected)], sorted(selected, key=lambda x: x[0] or 4.5))
        ]
        logger.info("Generated template on current data: selected-hardness: {}; generated template {}".format(list(zip(*selected))[0], [(c, s, "({:d} questions)".format(len(q))) for c, s, q in template]))
        # create the appropriate setting object. For now just make it 
        setting = dict(session_name="Generic Exam #{:04d}".format(int(random.random() * 10000)), allow_score=True, allow_result=True, student_list=[std.getUserInfo(internal_use=True) for std in self.students])
        result = exam_manager.create_new_session({"template": template, "setting": setting}, category, on_finish_callback=self.on_exam_finishes)
        if add_to_class: # if enabled (default); keep a reference in the classroom roster
            if not result[0] or isinstance(result[-1], Exception):
                # the exam creation failed; TODO choose between ironing out or retry until it works.
                logger.warning("@Classroom's create_exam: there has been an error when creating the exam. Check your sources.")
                return result
            success_state, (exam_key, admin_key) = result 
            self._exams[exam_key] = session = exam_manager.get_session(exam_key)
        return result

    def on_exam_finishes(self, exam_key: str, full_exam_data: dict):
        """When an exam finish, by default this should update the classroom interface and all the data that comes with it.
        TODO compile actual statistics that are relevant to the class itself."""
        self._result[exam_key] = full_exam_data["student"]


    def get_classroom_html_template(self):
        """Give the necessary template to display the data. Unless requiring a specialized template, this shouldn't need overriding"""
        return "classroom.html"

    def get_classroom_data(self, user_id, observer_mode: bool=False):
        """Give the necessary data depending on teacher or student (e.g if teacher, links to exams will target the manager page whereas student will be either to the test page or greyed)"""
        # same data 
        assert user_id == self.teacher.id or any((user_id == s.id for s in self.students)) or observer_mode, "User {} does not belong to the class {}, this operation cannot be performed".format(user_id, self.id)
        class_info = "This is Class <b>{:s}</b>.".format(self.name)
        if self.category:
            if self.tags:
                class_info += " It is about <b>{:s}</b>'s subsection \"{}\".".format(self.category, self.tag)
            else:
                class_info += " It is about <b>{:s}</b>".format(self.category)
        else:
            if self.tags:
                raise NotImplementedError # should not have tag without category anyway 
            else:
                class_info += " This does not have an assigned objective."
                
        data = {"user": user_id, "teacher": self.teacher, "students": self.students, "class_info": class_info}
        # different 
        is_student = user_id != self.teacher.id 
        if is_student:
            exams = []
            for exam_key, exam_data in self._exams.items(): # TODO sort by exam constructed.
                if exam_key in self._result:
                    # the exam is finished for everyone; greyed out option
                    exams.append((None, exam_data["setting"]["session_name"], "finished"))
                else:
                    entry_key, student_data_in_exam = next(( (sid, sdata) for sid, sdata in exam_data["student"].items() if sdata["id"] == user_id), (None, None))
                    if student_data_in_exam is None:
                        # this should not happen 
                        raise ValueError("A classroom exam ({}) has no relevant entry for corresponding student ({}); check the log.".format(exam_data, user_id))
                    elif "answers" in student_data_in_exam:
                        # already submitted 
                        exams.append((entry_key, exam_data["setting"]["session_name"], "submitted"))
                    else:
                        # not done; TODO if the exam is not active (scheduled for future), ignore it.
                        exams.append((entry_key, exam_data["setting"]["session_name"], "available"))
            data["exams"] = exams 
        else:
            # allow control on everything, plus supplied admin key. also indicate if the exam had been fully finished yet.
            data["exams"] = [ (exam_key, exam_data["setting"]["session_name"], exam_data["admin_key"], exam_key in self._result)  for exam_key, exam_data in self._exams.items()]
        # after everything, funnel this data to the construction of the class
        return data


def test_autogen_test_classroom(exam_manager, add_user):
    # creating a sample classroom & autogenerate using it.
    students = [ User("test_{:d}".format(uid), "testpwd", "test_student_{:d}".format(uid), name="Test Student {:d}".format(uid), role=UserRole.Student)
            for uid in range(1, 21)]
#    example_user_1 = User("test_1", "testpwd", "test_student_1", name="Test Student 1", role=UserRole.Student)
#    example_user_2 = User("test_2", "testpwd", "test_student_2", name="Test Student 2", role=UserRole.Student)

    example_teacher = User("test_0", "testpwd", "test_teacher", name="Test Teacher", role=UserRole.Admin)
    
    for u in [example_teacher] + students:
        add_user(u)
    
    category = random.choice(exam_manager.quiz_data.categories) # choose a random category

    classroom = Classroom("test_classroom", "Test Classroom (For Autogen Exam)", example_teacher, example_teacher, students, category, None)
    result, args = classroom.create_exam(exam_manager, use_unrated=True) # cause we has no data now.

    if result:
        logger.info("Successfully created the exam; session key {}, admin key {}".format(*args))
        return classroom, args
    else:
        logger.error("Cannot create the exam; make sure to check the traceback.")
        logger.error("Error (could be tuple): {}".format(args))
        return classroom, None
