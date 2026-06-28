from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from danu.db.models.base import utcnow
from danu.db.models.sms_subscription import SmsSubscription


class SmsSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, *, tenant_id: str, phone_number: str) -> SmsSubscription | None:
        stmt = select(SmsSubscription).where(
            SmsSubscription.tenant_id == tenant_id,
            SmsSubscription.phone_number == phone_number,
        )
        return self.session.scalars(stmt).first()

    def is_opted_in(self, *, tenant_id: str, phone_number: str) -> bool:
        row = self.get(tenant_id=tenant_id, phone_number=phone_number)
        if row is None:
            return True
        return row.status == "opted_in"

    def set_status(self, *, tenant_id: str, phone_number: str, status: str) -> SmsSubscription:
        row = self.get(tenant_id=tenant_id, phone_number=phone_number)
        if row is None:
            row = SmsSubscription(
                tenant_id=tenant_id,
                phone_number=phone_number,
                status=status,
            )
            self.session.add(row)
        else:
            row.status = status
            row.updated_at = utcnow()
        self.session.flush()
        return row