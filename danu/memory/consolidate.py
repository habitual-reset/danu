"""Background memory consolidation. Full LLM extraction lands in Phase 2."""

from __future__ import annotations

from sqlalchemy.orm import Session

from danu.db.repositories.event import EventRepository
from danu.db.repositories.memory import MemoryRepository
from danu.db.repositories.message import MessageRepository
from danu.memory.store import MemoryStore


class MemoryConsolidator:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = EventRepository(session)
        self.messages = MessageRepository(session)
        self.memory = MemoryRepository(session)
        self.store = MemoryStore(session)

    def consolidate_conversation(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        min_messages: int = 20,
    ) -> str | None:
        messages = self.messages.list_recent(conversation_id, limit=200)
        if len(messages) < min_messages:
            return None

        lines = [f"{msg.role}: {msg.content}" for msg in messages]
        summary = "Conversation summary:\n" + "\n".join(lines[-10:])

        self.memory.add_summary(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            summary=summary,
            period_start=messages[0].created_at,
            period_end=messages[-1].created_at,
        )
        return summary

    def process_proposed_events(
        self,
        *,
        tenant_id: str,
        user_id: str,
        confidence_threshold: float = 0.8,
    ) -> int:
        """Commit staged memory proposals that meet the confidence threshold."""
        from danu.db.models.event import Event
        from sqlalchemy import select

        stmt = (
            select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.user_id == user_id,
                Event.event_type == "memory.proposed",
            )
            .order_by(Event.created_at.asc())
        )
        events = list(self.session.scalars(stmt).all())
        committed = 0

        for event in events:
            already_committed = any(
                e.event_type == "memory.committed"
                and e.payload_json.get("source_event_id") == event.id
                for e in self.session.scalars(
                    select(Event).where(
                        Event.tenant_id == tenant_id,
                        Event.event_type == "memory.committed",
                    )
                ).all()
            )
            if already_committed:
                continue

            for raw_op in event.payload_json.get("ops", []):
                confidence = float(raw_op.get("confidence", 0.5))
                if confidence < confidence_threshold and not raw_op.get("fast_track"):
                    continue

                from danu.memory.schemas import MemoryOp, MemoryOpType

                op = MemoryOp(
                    op_type=MemoryOpType(raw_op["op_type"]),
                    category=raw_op["category"],
                    key=raw_op["key"],
                    value=raw_op["value"],
                    confidence=confidence,
                    fast_track=bool(raw_op.get("fast_track")),
                )
                self.store.commit_memory_op(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    op=op,
                    source_event_id=event.id,
                )
                committed += 1

        return committed