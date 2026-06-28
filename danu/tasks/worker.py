import logging
import time

from danu.db.base import get_session_factory
from danu.tasks.handlers import HANDLERS
from danu.tasks.queue import TaskQueue

logger = logging.getLogger(__name__)


def run_once() -> bool:
    session = get_session_factory()()
    try:
        queue = TaskQueue(session)
        task = queue.claim_next()
        if task is None:
            return False

        handler = HANDLERS.get(task.task_type)
        if handler is None:
            queue.fail(task, dead=True)
            session.commit()
            logger.error("Unknown task type: %s", task.task_type)
            return True

        try:
            handler(session, task)
            queue.complete(task)
            session.commit()
            logger.info("Completed task %s (%s)", task.id, task.task_type)
        except Exception:
            session.rollback()
            session = get_session_factory()()
            queue = TaskQueue(session)
            refreshed = session.get(type(task), task.id)
            if refreshed:
                queue.fail(refreshed, dead=refreshed.attempts >= 3)
                session.commit()
            logger.exception("Task failed: %s", task.id)
        return True
    finally:
        session.close()


def main(poll_interval_seconds: float = 2.0) -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("DANU worker started")
    while True:
        processed = run_once()
        if not processed:
            time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    main()