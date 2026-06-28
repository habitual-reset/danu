from __future__ import annotations

from sqlalchemy.orm import Session

from danu.db.repositories.usage import UsageRepository
from danu.usage.rates import (
    estimate_embedding_cost_usd,
    estimate_llm_cost_usd,
    estimate_twilio_sms_cost_usd,
    estimate_twilio_voice_cost_usd,
)


class UsageTracker:
    def __init__(self, session: Session) -> None:
        self.repo = UsageRepository(session)

    def record_llm_completion(
        self,
        *,
        tenant_id: str,
        user_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        purpose: str | None = None,
    ) -> None:
        if prompt_tokens <= 0 and completion_tokens <= 0:
            return

        total = prompt_tokens + completion_tokens
        self.repo.record(
            tenant_id=tenant_id,
            user_id=user_id,
            provider="openai",
            resource_type="llm_completion",
            quantity=float(total),
            unit="token",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=estimate_llm_cost_usd(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            metadata_json={"purpose": purpose} if purpose else {},
        )

    def record_embedding(
        self,
        *,
        tenant_id: str,
        user_id: str,
        model: str,
        total_tokens: int,
        conversation_id: str | None = None,
        purpose: str | None = None,
    ) -> None:
        if total_tokens <= 0:
            return

        self.repo.record(
            tenant_id=tenant_id,
            user_id=user_id,
            provider="openai",
            resource_type="embedding",
            quantity=float(total_tokens),
            unit="token",
            model=model,
            estimated_cost_usd=estimate_embedding_cost_usd(model=model, total_tokens=total_tokens),
            conversation_id=conversation_id,
            metadata_json={"purpose": purpose} if purpose else {},
        )

    def record_twilio_voice(
        self,
        *,
        tenant_id: str,
        user_id: str,
        duration_seconds: int,
        conversation_id: str | None = None,
        call_sid: str | None = None,
    ) -> None:
        if duration_seconds <= 0:
            return

        self.repo.record(
            tenant_id=tenant_id,
            user_id=user_id,
            provider="twilio",
            resource_type="voice_minute",
            quantity=float(duration_seconds),
            unit="second",
            estimated_cost_usd=estimate_twilio_voice_cost_usd(duration_seconds=duration_seconds),
            conversation_id=conversation_id,
            correlation_id=call_sid,
        )

    def record_twilio_sms(
        self,
        *,
        tenant_id: str,
        user_id: str,
        segments: int = 1,
        conversation_id: str | None = None,
        message_sid: str | None = None,
        direction: str = "outbound",
    ) -> None:
        self.repo.record(
            tenant_id=tenant_id,
            user_id=user_id,
            provider="twilio",
            resource_type="sms_segment",
            quantity=float(max(segments, 1)),
            unit="segment",
            estimated_cost_usd=estimate_twilio_sms_cost_usd(segments=segments),
            conversation_id=conversation_id,
            correlation_id=message_sid,
            metadata_json={"direction": direction},
        )