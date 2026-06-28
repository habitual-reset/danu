from danu.agent.llm import MockLLMClient
from danu.agent.orchestrator import AgentOrchestrator
from danu.channels.base import MessageEnvelope
from danu.channels.voice import build_hold_twiml
from danu.db.repositories.memory import MemoryRepository
from danu.memory.task_extract import extract_task_ops
from danu.voice.work_detector import classify_work_type, estimate_seconds, needs_hold


def test_needs_hold_for_task_phrases():
    assert needs_hold(
        "My first task is pick up things around the house",
        onboarding_complete=True,
    )
    assert not needs_hold("okay", onboarding_complete=True)
    assert not needs_hold("My name is Matt", onboarding_complete=False)
    assert needs_hold(
        "Mostly I want help staying organized and remembering things around the house",
        onboarding_complete=False,
    )


def test_task_extract_fast_tracks_open_task():
    ops = extract_task_ops("My first task is pick up random things around the house")
    assert len(ops) == 1
    assert ops[0].category == "task"
    assert ops[0].fast_track is True
    assert "pick up" in ops[0].value["text"].lower()


def test_orchestrator_commits_task_during_turn(session):
    orchestrator = AgentOrchestrator(session, llm=MockLLMClient())
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="voice",
        correlation_id="CA_TASK",
    )
    orchestrator.handle_turn(
        MessageEnvelope(
            channel="voice",
            tenant_id="default",
            user_id="user-1",
            conversation_id=conversation_id,
            body="My first task is water the plants tonight",
            correlation_id="CA_TASK",
            raw_payload={},
        )
    )

    memory = MemoryRepository(session)
    items = memory.list_current_items(tenant_id="default", user_id="user-1", category="task")
    assert any("water the plants" in str(item.value_json).lower() for item in items)


def test_hold_twiml_includes_music_and_redirect():
    twiml = build_hold_twiml(
        message="Give me five seconds.",
        music_url="http://example.com/hold.mp3",
        work_url="/webhooks/twilio/voice/work",
        music_loops=2,
    )
    assert "Give me five seconds." in twiml
    assert "http://example.com/hold.mp3" in twiml
    assert 'method="POST"' in twiml
    assert "/webhooks/twilio/voice/work" in twiml


def test_work_type_and_estimate():
    assert classify_work_type("I need to call mom") == "task_memory"
    assert estimate_seconds("word " * 30, work_type="task_memory") >= 7