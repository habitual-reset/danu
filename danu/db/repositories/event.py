from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from danu.db.models.event import Event


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(
        self,
        *,
        tenant_id: str,
        user_id: str,
        event_type: str,
        payload_json: dict,
        conversation_id: str | None = None,
        channel: str | None = None,
        correlation_id: str | None = None,
    ) -> Event:
        event = Event(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            event_type=event_type,
            payload_json=payload_json,
            channel=channel,
            correlation_id=correlation_id,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_for_conversation(self, conversation_id: str, limit: int = 100) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.conversation_id == conversation_id)
            .order_by(Event.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())