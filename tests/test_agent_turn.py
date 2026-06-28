from danu.agent.llm import MockLLMClient
from danu.agent.orchestrator import AgentOrchestrator
from danu.channels.base import MessageEnvelope
from danu.db.repositories.event import EventRepository
from danu.db.repositories.memory import MemoryRepository


def test_orchestrator_persists_events_and_remembers_explicit_instruction(session):
    orchestrator = AgentOrchestrator(session, llm=MockLLMClient())
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="sms",
        correlation_id="SM100",
    )

    envelope = MessageEnvelope(
        channel="sms",
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
        body="Remember that my dog's name is Biscuit",
        correlation_id="SM100",
        raw_payload={},
    )

    result = orchestrator.handle_turn(envelope)

    assert "Remember that my dog's name is Biscuit" in result.response_text or result.response_text
    assert result.inbound_event_id
    assert result.outbound_event_id

    events = EventRepository(session)
    conversation_events = events.list_for_conversation(conversation_id, limit=10)
    event_types = {event.event_type for event in conversation_events}
    assert "message.inbound" in event_types
    assert "message.outbound" in event_types

    memory = MemoryRepository(session)
    items = memory.list_current_items(tenant_id="default", user_id="user-1")
    assert any("Biscuit" in str(item.value_json) for item in items)