from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from danu.db.models.task import Task
from danu.db.models.base import utcnow


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        tenant_id: str,
        task_type: str,
        payload_json: dict,
        user_id: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> Task:
        task = Task(
            tenant_id=tenant_id,
            user_id=user_id,
            task_type=task_type,
            payload_json=payload_json,
            scheduled_at=scheduled_at or utcnow(),
        )
        self.session.add(task)
        self.session.flush()
        return task

    def claim_next(self) -> Task | None:
        stmt = (
            select(Task)
            .where(
                Task.status == "pending",
                Task.scheduled_at <= utcnow(),
            )
            .order_by(Task.scheduled_at.asc())
            .limit(1)
        )
        task = self.session.scalars(stmt).first()
        if task is None:
            return None

        task.status = "running"
        task.attempts += 1
        self.session.flush()
        return task

    def complete(self, task: Task) -> None:
        task.status = "completed"
        task.completed_at = utcnow()
        self.session.flush()

    def fail(self, task: Task, *, dead: bool = False) -> None:
        task.status = "dead" if dead else "failed"
        task.completed_at = utcnow()
        self.session.flush()