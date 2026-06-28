from __future__ import annotations

from sqlalchemy.orm import Session

from danu.db.repositories.task import TaskRepository
from danu.memory.schemas import MemoryOp, MemoryOpType
from danu.memory.store import MemoryStore
from danu.reminders.extract import ReminderRequest


class ReminderScheduler:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.tasks = TaskRepository(session)
        self.store = MemoryStore(session)

    def schedule_sms_reminder(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        phone_number: str,
        reminder: ReminderRequest,
        channel: str = "voice",
    ) -> str:
        task = self.tasks.enqueue(
            tenant_id=tenant_id,
            user_id=user_id,
            task_type="send_sms_reminder",
            scheduled_at=reminder.fire_at,
            payload_json={
                "phone_number": phone_number,
                "message": reminder.message,
                "conversation_id": conversation_id,
                "fire_at": reminder.fire_at.isoformat(),
            },
        )

        self.store.stage_memory_ops(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            ops=[
                MemoryOp(
                    op_type=MemoryOpType.CREATE,
                    category="reminder",
                    key=f"reminder_{task.id[:8]}",
                    value={
                        "text": reminder.message,
                        "fire_at": reminder.fire_at.isoformat(),
                        "channel": "sms",
                        "task_id": task.id,
                        "status": "scheduled",
                    },
                    confidence=0.95,
                    fast_track=True,
                )
            ],
            channel=channel,
        )
        return task.id