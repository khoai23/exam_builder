"""Tool to automate any necessary things. Chief use will probably be classroom, so it automatically build up a set of relevant tests every week."""

from apscheduler.schedulers.background import BackgroundScheduler

import logging 
logger = logging.getLogger(__name__)

def initiate_scheduler(bind_atexit: bool=True) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.start()
    if bind_atexit:
        try:
            import atexit 
            atexit.register(lambda: scheduler.shutdown()) # probably unimportant with 
        except Exception as e:
            logger.warning("Scheduler shutdown binding failed; true reason {}. Since it's daemon it's probably safe though.".format(e))
    return scheduler
