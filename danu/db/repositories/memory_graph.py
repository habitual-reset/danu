from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from danu.db.models.memory_graph import MemoryEntity, MemoryRelation


class MemoryGraphRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_entity_by_name(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str,
        entity_type: str,
    ) -> MemoryEntity | None:
        stmt = select(MemoryEntity).where(
            MemoryEntity.tenant_id == tenant_id,
            MemoryEntity.user_id == user_id,
            MemoryEntity.name == name,
            MemoryEntity.entity_type == entity_type,
        )
        return self.session.scalars(stmt).first()

    def upsert_entity(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str,
        entity_type: str,
        source_event_id: str | None = None,
    ) -> MemoryEntity:
        existing = self.get_entity_by_name(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            entity_type=entity_type,
        )
        if existing:
            return existing
        row = MemoryEntity(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            entity_type=entity_type,
            source_event_id=source_event_id,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def add_relation(
        self,
        *,
        tenant_id: str,
        user_id: str,
        from_entity_id: str,
        to_entity_id: str,
        relation_type: str,
        confidence: float = 0.7,
        source_event_id: str | None = None,
    ) -> MemoryRelation:
        row = MemoryRelation(
            tenant_id=tenant_id,
            user_id=user_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relation_type=relation_type,
            confidence=confidence,
            source_event_id=source_event_id,
        )
        self.session.add(row)
        self.session.flush()
        return row