import json

from danu.agent.llm import LLMClient, LLMResponse
from danu.agent.orchestrator import AgentOrchestrator
from danu.channels.base import MessageEnvelope
from danu.db.repositories.memory import MemoryRepository
from danu.db.repositories.memory_graph import MemoryGraphRepository
from danu.memory.consolidate import MemoryConsolidator


class JsonLLMClient(LLMClient):
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(content=json.dumps(self.payload))


def test_consolidate_extracts_summary_facts_and_graph(session):
    orchestrator = AgentOrchestrator(session)
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="voice",
        correlation_id="CA100",
    )

    for body in ("My dog is named Biscuit", "He loves the park"):
        orchestrator.handle_turn(
            MessageEnvelope(
                channel="voice",
                tenant_id="default",
                user_id="user-1",
                conversation_id=conversation_id,
                body=body,
                correlation_id="CA100",
                raw_payload={},
            )
        )

    payload = {
        "summary": "User talked about their dog Biscuit who loves the park.",
        "facts": [
            {
                "category": "person",
                "key": "dog_name",
                "value": {"text": "Biscuit"},
                "confidence": 0.9,
            }
        ],
        "entities": [
            {"name": "Biscuit", "entity_type": "person"},
            {"name": "park", "entity_type": "place"},
        ],
        "relations": [
            {
                "from_name": "Biscuit",
                "to_name": "park",
                "from_type": "person",
                "to_type": "place",
                "relation_type": "prefers",
                "confidence": 0.85,
            }
        ],
    }

    consolidator = MemoryConsolidator(session, llm=JsonLLMClient(payload))
    summary = consolidator.consolidate_conversation(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
    )

    assert summary == payload["summary"]

    memory = MemoryRepository(session)
    summaries = memory.list_summaries(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
    )
    assert len(summaries) == 1

    items = memory.list_current_items(tenant_id="default", user_id="user-1")
    assert any(item.key == "dog_name" for item in items)

    graph = MemoryGraphRepository(session)
    biscuit = graph.get_entity_by_name(
        tenant_id="default",
        user_id="user-1",
        name="Biscuit",
        entity_type="person",
    )
    assert biscuit is not None


def test_consolidate_skips_short_conversations(session):
    orchestrator = AgentOrchestrator(session)
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="sms",
    )

    consolidator = MemoryConsolidator(session, llm=JsonLLMClient({"summary": "nope"}))
    result = consolidator.consolidate_conversation(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
        min_messages=2,
    )
    assert result is None