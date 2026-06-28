from sqlalchemy.orm import Session

from danu.db.models.task import Task
from danu.memory.consolidate import MemoryConsolidator


def handle_consolidate_memory(session: Session, task: Task) -> None:
    payload = task.payload_json
    consolidator = MemoryConsolidator(session)
    consolidator.consolidate_conversation(
        tenant_id=task.tenant_id,
        user_id=task.user_id or "",
        conversation_id=payload["conversation_id"],
    )
    if task.user_id:
        consolidator.process_proposed_events(
            tenant_id=task.tenant_id,
            user_id=task.user_id,
        )


HANDLERS = {
    "consolidate_memory": handle_consolidate_memory,
}