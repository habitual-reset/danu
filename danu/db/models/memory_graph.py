from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from danu.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MemoryEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memory_entities"

    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class MemoryRelation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memory_relations"

    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    to_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)