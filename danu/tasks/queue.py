from sqlalchemy.orm import Session

from danu.db.repositories.task import TaskRepository


class TaskQueue:
    def __init__(self, session: Session) -> None:
        self.repo = TaskRepository(session)

    def enqueue(self, **kwargs):
        return self.repo.enqueue(**kwargs)

    def claim_next(self):
        return self.repo.claim_next()

    def complete(self, task) -> None:
        self.repo.complete(task)

    def fail(self, task, *, dead: bool = False) -> None:
        self.repo.fail(task, dead=dead)