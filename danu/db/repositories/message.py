from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from danu.db.models.message import Message


class MessageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        source_event_id: str,
    ) -> Message:
        message = Message(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            source_event_id=source_event_id,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def list_recent(self, conversation_id: str, limit: int = 20) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list(self.session.scalars(stmt).all())
        rows.reverse()
        return rows