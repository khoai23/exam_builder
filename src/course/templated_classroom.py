"""Upgraded variant of classroom; which has it's own `template` which is basically just a schedule slaved to the start timer. For now only support innate lessons (.md) and exam.
"""
from datetime import datetime, timedelta
from src.course.classroom import Classroom

from typing import List, Tuple, Dict, Optional, Any

import logging 
logger = logging.getLogger(__name__)

class TemplatedClassroom(Classroom):
    def __init__(self, exam_manager, schedule: List[Tuple[timedelta, Any]], *args, start_time: Optional[datetime]=None, end_time: Optional[datetime]=None, **kwargs):
        """Args:
        schedule: The core of the classroom; this will be designated with (timedelta-from-start), (item). Exam would then construct its start/end time upon initialization. Lessons would just be available from this point onward.
        start_time: The time classroom will be in effect. If not specified, default on construction.
        end_time: The time classroom will stop being available. If not specified, default to 1 week after last item available
        """
        # keep the template and allow modification to it 
        # TODO keep track of modification to allow reloading, adding or changing specific nodes.
        self.schedule = schedule 
        if not start_time:
            logger.info("@TemplatedClassroom: start_time not specified; default to the creation time.")
            self.start_time = datetime.today()
        else:
            self.start_time = start_time 

        if not end_time:
            logger.info("@TemplatedClassroom: end_time not specified; value is defaulted to +1week after last scheduled item.")
        else:
            if isinstance(end_time, timedelta):
                self.end_time = self.start_time + end_time 
            else:
                self.end_time = end_time 
        # now calculate items if necessary 
        self.calendar, self.end_time = self.calculate_schedule(exam_manager, self.start_time, self.end_time)

    def calculate_schedule(self, exam_manager, start_time: datetime, end_time: Optional[datetime]):
        """Write directly to a self.content timetable, per-day. A lot of things need to be added:
        - modifying items in the template by the owner
        - modifying items in the actual schedule by the teacher 
        - allowing multiple items in the same day-spot (maybe not necessary?).
        Returns:
            the timetable object, list of (date, task); task item must be convertible to appropriate format by jinja's renderer.
            the end_time timestamp; will be the same as end_time or the default +1week
        """
        content = []
        for delta, task_template in self.schedule:
            task_time = start_time + delta 
            # extract the type; if types require initialization e.g exam; perform so 
            task_type, task_properties = task_template
            if task_type == "exam":
                result, run_count = False, 0
                # for this type it will always have a session_start; session_end SHOULD be enforced but technically not mandatory.
                while not result and run_count < 20:
                    # this will auto-loop around until the exam is properly created; so it's a risk of hanging the whole thread.
                    result, keys = self.create_exam(exam_manager, **task_properties)
                    run_count += 1
                if run_count >= 20:
                    raise ValueError("Exam being constructed with properties {} impossible (20 consecutive failure). Check the data/construction.")
                # if reach here, keys are available and will be used as task properties 
                exam_key, admin_key = keys
                task_properties = {"exam_key": exam_key, "admin_key": admin_key}
            else:
                # recreate the properties object to prevent editing backward.
                task_properties = dict(task_properties)
            # re-bundle and set out as data
            task_data = (task_time, (task_type, task_properties))
            content.append(task_data)
        # if the end time is not specified; we default to 1 week after the last task 
        if not end_time:
            logger.warning("The classroom has no specified end time; default (+1 week) will be used")
            last_task_time, _ = max(content, key=lambda c: c[0])
            end_time = last_task_time + timedelta(days=7)
        # second iteration; assigning each date with one task only; duplicates will be warned but otherwise discarded.
        calendar = []
        datestr_content = [(datetime.strftime(d, "%d/%m/%Y"), d, p) for d, p in content]
        current_date = start_time
        while current_date <= end_time:
            # see any matching value in the content 
            datestr = datetime.strftime(current_date, "%d/%m/%Y")
            has_task = False
            for ds, d, p in datestr_content:
                if ds == datestr: # match by day 
                    if not has_task:
                        # found 1st task (normal), append to calendar as-is
                        has_task = True
                        calendar.append((datestr, current_date, p)) # no real difference to (d, p), but arg
                    else:
                        # found 2nd task (not supported), issue a warning for now. 
                        logger.warning("Calendar cannot tolerate multiple task in the same day ({}) at the moment. The current task ({}) will be ignored.".format(datestr, p))
            if not has_task:
                # has no task, simply append null data 
                calendar.append((datestr, current_date, None))
            # increment at end of calculation
            current_date = current_date + timedelta(days=1)
        # after finishing; the dates are to be saved down by the init 
        return calendar, end_time
                        
    def get_classroom_data(self, user_id, observer_mode: bool=False):
        # a bit wasteful since this will organize the exams data outside of the calendar, but oh well. Revisit later if efficiency is a concern.
        current_data = super(TemplatedClassroom, self).get_classroom_data(user_id, observer_mode=observer_mode)
        # removing the exam data; adding the formatable calendar data
        current_data.pop("exams", None)
        current_data["calendar"] = self.calendar
        return current_data
