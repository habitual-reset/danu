from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from danu.db.models.memory import ConversationSummary, MemoryEmbedding, MemoryItem
from danu.db.models.base import utcnow


class MemoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_item(
        self,
        *,
        tenant_id: str,
        user_id: str,
        category: str,
        key: str,
        value_json: dict,
        confidence: float,
        source_event_id: str | None = None,
    ) -> MemoryItem:
        existing = self.get_current_item(tenant_id=tenant_id, user_id=user_id, key=key)
        item = MemoryItem(
            tenant_id=tenant_id,
            user_id=user_id,
            category=category,
            key=key,
            value_json=value_json,
            confidence=confidence,
            source_event_id=source_event_id,
        )
        self.session.add(item)
        self.session.flush()

        if existing is not None:
            existing.superseded_by_id = item.id
            existing.valid_to = utcnow()
            self.session.flush()

        return item

    def get_current_item(self, *, tenant_id: str, user_id: str, key: str) -> MemoryItem | None:
        stmt = (
            select(MemoryItem)
            .where(
                MemoryItem.tenant_id == tenant_id,
                MemoryItem.user_id == user_id,
                MemoryItem.key == key,
                MemoryItem.superseded_by_id.is_(None),
                MemoryItem.valid_to.is_(None),
            )
            .order_by(MemoryItem.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_current_items(
        self,
        *,
        tenant_id: str,
        user_id: str,
        category: str | None = None,
        limit: int = 100,
    ) -> list[MemoryItem]:
        conditions = [
            MemoryItem.tenant_id == tenant_id,
            MemoryItem.user_id == user_id,
            MemoryItem.superseded_by_id.is_(None),
            MemoryItem.valid_to.is_(None),
        ]
        if category:
            conditions.append(MemoryItem.category == category)

        stmt = (
            select(MemoryItem)
            .where(and_(*conditions))
            .order_by(MemoryItem.confidence.desc(), MemoryItem.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def search_items_by_keyword(
        self,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        pattern = f"%{query.lower()}%"
        stmt = (
            select(MemoryItem)
            .where(
                MemoryItem.tenant_id == tenant_id,
                MemoryItem.user_id == user_id,
                MemoryItem.superseded_by_id.is_(None),
                MemoryItem.valid_to.is_(None),
                or_(
                    MemoryItem.key.ilike(pattern),
                    MemoryItem.category.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def add_summary(
        self,
        *,
        tenant_id: str,
        user_id: str,
        summary: str,
        conversation_id: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> ConversationSummary:
        row = ConversationSummary(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            summary=summary,
            period_start=period_start,
            period_end=period_end,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_summaries(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str | None = None,
        limit: int = 5,
    ) -> list[ConversationSummary]:
        conditions = [
            ConversationSummary.tenant_id == tenant_id,
            ConversationSummary.user_id == user_id,
        ]
        if conversation_id:
            conditions.append(ConversationSummary.conversation_id == conversation_id)

        stmt = (
            select(ConversationSummary)
            .where(and_(*conditions))
            .order_by(ConversationSummary.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def upsert_embedding(
        self,
        *,
        tenant_id: str,
        user_id: str,
        source_type: str,
        source_id: str,
        chunk_text: str,
        embedding: list[float],
    ) -> MemoryEmbedding:
        stmt = select(MemoryEmbedding).where(
            MemoryEmbedding.source_type == source_type,
            MemoryEmbedding.source_id == source_id,
        )
        existing = self.session.scalars(stmt).first()
        if existing:
            existing.chunk_text = chunk_text
            existing.embedding_json = embedding
            self.session.flush()
            return existing

        row = MemoryEmbedding(
            tenant_id=tenant_id,
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            chunk_text=chunk_text,
            embedding_json=embedding,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_embeddings(
        self,
        *,
        tenant_id: str,
        user_id: str,
        limit: int = 500,
    ) -> list[MemoryEmbedding]:
        stmt = (
            select(MemoryEmbedding)
            .where(
                MemoryEmbedding.tenant_id == tenant_id,
                MemoryEmbedding.user_id == user_id,
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())