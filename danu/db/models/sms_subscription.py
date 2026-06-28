from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from danu.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class SmsSubscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sms_subscriptions"
    __table_args__ = (UniqueConstraint("tenant_id", "phone_number", name="uq_sms_sub_tenant_phone"),)

    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="opted_in", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)