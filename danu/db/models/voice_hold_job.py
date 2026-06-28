from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from danu.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VoiceHoldJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "voice_hold_jobs"

    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    call_sid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    speech_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    work_type: Mapped[str] = mapped_column(String(32), nullable=False, default="turn")
    estimated_seconds: Mapped[int] = mapped_column(nullable=False, default=5)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)