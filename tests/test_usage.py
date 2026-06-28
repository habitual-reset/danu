import json

from danu.agent.llm import LLMClient, LLMResponse
from danu.agent.orchestrator import AgentOrchestrator
from danu.channels.base import MessageEnvelope
from danu.db.repositories.usage import UsageRepository
from danu.memory.consolidate import MemoryConsolidator
from danu.usage.rates import (
    estimate_llm_cost_usd,
    estimate_twilio_voice_cost_usd,
)
from danu.usage.tracker import UsageTracker


class JsonLLMClient(LLMClient):
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(
            content=json.dumps(self.payload),
            model="gpt-4.1-mini",
            prompt_tokens=120,
            completion_tokens=45,
        )


def test_rate_estimates_are_positive():
    assert estimate_llm_cost_usd(model="gpt-4.1-mini", prompt_tokens=1000, completion_tokens=200) > 0
    assert estimate_twilio_voice_cost_usd(duration_seconds=60) > 0


def test_tracker_records_llm_and_voice_usage(session):
    tracker = UsageTracker(session)
    tracker.record_llm_completion(
        tenant_id="default",
        user_id="user-1",
        model="gpt-4.1-mini",
        prompt_tokens=500,
        completion_tokens=100,
        conversation_id="conv-1",
        correlation_id="CA123",
        purpose="turn_voice",
    )
    tracker.record_twilio_voice(
        tenant_id="default",
        user_id="user-1",
        duration_seconds=44,
        conversation_id="conv-1",
        call_sid="CA123",
    )

    repo = UsageRepository(session)
    rows = repo.summarize_by_provider(tenant_id="default", user_id="user-1")
    providers = {row["resource_type"] for row in rows}
    assert "llm_completion" in providers
    assert "voice_minute" in providers
    assert repo.total_estimated_cost(tenant_id="default", user_id="user-1") > 0


def test_orchestrator_records_llm_usage_on_turn(session):
    orchestrator = AgentOrchestrator(session, llm=JsonLLMClient({"summary": "x"}))
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="voice",
        correlation_id="CA200",
    )
    orchestrator.handle_turn(
        MessageEnvelope(
            channel="voice",
            tenant_id="default",
            user_id="user-1",
            conversation_id=conversation_id,
            body="Hello",
            correlation_id="CA200",
            raw_payload={},
        )
    )

    repo = UsageRepository(session)
    total = repo.total_estimated_cost(tenant_id="default", user_id="user-1")
    assert total > 0


def test_consolidation_records_llm_usage(session):
    orchestrator = AgentOrchestrator(session)
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="voice",
        correlation_id="CA201",
    )
    for body in ("First message", "Second message"):
        orchestrator.handle_turn(
            MessageEnvelope(
                channel="voice",
                tenant_id="default",
                user_id="user-1",
                conversation_id=conversation_id,
                body=body,
                correlation_id="CA201",
                raw_payload={},
            )
        )

    consolidator = MemoryConsolidator(
        session,
        llm=JsonLLMClient(
            {
                "summary": "Two messages exchanged.",
                "facts": [],
                "entities": [],
                "relations": [],
            }
        ),
    )
    consolidator.consolidate_conversation(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
    )

    repo = UsageRepository(session)
    rows = repo.summarize_by_provider(tenant_id="default", user_id="user-1")
    assert any(row["resource_type"] == "llm_completion" for row in rows)