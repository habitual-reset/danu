from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from danu.db.models.conversation import Conversation
from danu.db.models.base import utcnow


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel: str,
        correlation_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            channel=channel,
            correlation_id=correlation_id,
        )
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def get_by_id(self, conversation_id: str) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def get_by_correlation_id(self, correlation_id: str) -> Conversation | None:
        stmt = select(Conversation).where(Conversation.correlation_id == correlation_id)
        return self.session.scalars(stmt).first()

    def get_active_for_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel: str,
        idle_minutes: int,
    ) -> Conversation | None:
        cutoff = utcnow() - timedelta(minutes=idle_minutes)
        stmt = (
            select(Conversation)
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id,
                Conversation.channel == channel,
                Conversation.status == "active",
                Conversation.last_activity_at >= cutoff,
            )
            .order_by(Conversation.last_activity_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def touch(self, conversation: Conversation) -> None:
        conversation.last_activity_at = utcnow()
        self.session.flush()

    def close(self, conversation: Conversation) -> None:
        conversation.status = "closed"
        conversation.last_activity_at = utcnow()
        self.session.flush()