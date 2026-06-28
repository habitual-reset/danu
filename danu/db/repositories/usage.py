from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from danu.db.models.usage_event import UsageEvent


class UsageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        tenant_id: str,
        user_id: str,
        provider: str,
        resource_type: str,
        quantity: float,
        unit: str,
        model: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> UsageEvent:
        row = UsageEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            resource_type=resource_type,
            quantity=quantity,
            unit=unit,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=estimated_cost_usd,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            metadata_json=metadata_json or {},
        )
        self.session.add(row)
        self.session.flush()
        return row

    def summarize_by_provider(self, *, tenant_id: str, user_id: str | None = None) -> list[dict]:
        conditions = [UsageEvent.tenant_id == tenant_id]
        if user_id:
            conditions.append(UsageEvent.user_id == user_id)

        stmt = (
            select(
                UsageEvent.provider,
                UsageEvent.resource_type,
                func.count(UsageEvent.id),
                func.sum(UsageEvent.quantity),
                func.sum(UsageEvent.estimated_cost_usd),
            )
            .where(*conditions)
            .group_by(UsageEvent.provider, UsageEvent.resource_type)
            .order_by(UsageEvent.provider, UsageEvent.resource_type)
        )
        rows = self.session.execute(stmt).all()
        return [
            {
                "provider": provider,
                "resource_type": resource_type,
                "event_count": count,
                "total_quantity": float(total_qty or 0),
                "estimated_cost_usd": float(total_cost or 0),
            }
            for provider, resource_type, count, total_qty, total_cost in rows
        ]

    def total_estimated_cost(self, *, tenant_id: str, user_id: str | None = None) -> float:
        conditions = [UsageEvent.tenant_id == tenant_id]
        if user_id:
            conditions.append(UsageEvent.user_id == user_id)

        stmt = select(func.sum(UsageEvent.estimated_cost_usd)).where(*conditions)
        total = self.session.scalar(stmt)
        return float(total or 0)