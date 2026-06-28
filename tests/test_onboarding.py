from danu.agent.llm import MockLLMClient
from danu.agent.orchestrator import AgentOrchestrator
from danu.admin.reset import reset_user_data
from danu.channels.base import MessageEnvelope
from danu.channels.voice import is_farewell
from danu.db.repositories.memory import MemoryRepository
from danu.onboarding.extract import extract_onboarding_ops
from danu.onboarding.service import OnboardingService, OnboardingState
from danu.agent.prompt_builder import build_system_prompt


def test_needs_onboarding_when_profile_empty(session):
    svc = OnboardingService(session)
    assert svc.needs_onboarding(tenant_id="default", user_id="user-1") is True


def test_extract_user_and_agent_names():
    state = OnboardingState()
    ops = extract_onboarding_ops(state, "My name is Matt")
    assert len(ops) == 1
    assert ops[0].key == "user_name"
    assert ops[0].value["text"] == "Matt"

    state.user_name = "Matt"
    ops = extract_onboarding_ops(state, "I'll call you Kosmo")
    assert len(ops) == 1
    assert ops[0].key == "agent_name"
    assert ops[0].value["text"] == "Kosmo"


def test_onboarding_prompt_asks_for_missing_fields():
    prompt = build_system_prompt(
        channel="voice",
        onboarding=OnboardingState(),
        in_onboarding=True,
    )
    assert "onboarding" in prompt.lower()
    assert "user's name" in prompt.lower()


def test_orchestrator_completes_onboarding_from_voice_turns(session):
    orchestrator = AgentOrchestrator(session, llm=MockLLMClient())
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="voice",
        correlation_id="CA_ONBOARD",
    )

    orchestrator.handle_turn(
        MessageEnvelope(
            channel="voice",
            tenant_id="default",
            user_id="user-1",
            conversation_id=conversation_id,
            body="My name is Matt",
            correlation_id="CA_ONBOARD",
            raw_payload={},
        )
    )
    orchestrator.handle_turn(
        MessageEnvelope(
            channel="voice",
            tenant_id="default",
            user_id="user-1",
            conversation_id=conversation_id,
            body="Call you Kosmo",
            correlation_id="CA_ONBOARD",
            raw_payload={},
        )
    )

    svc = OnboardingService(session)
    state = svc.load_state(tenant_id="default", user_id="user-1")
    assert state.user_name == "Matt"
    assert state.agent_name == "Kosmo"
    assert state.completed is True
    assert svc.needs_onboarding(tenant_id="default", user_id="user-1") is False


def test_reset_user_clears_memory(session):
    orchestrator = AgentOrchestrator(session, llm=MockLLMClient())
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="voice",
    )
    orchestrator.handle_turn(
        MessageEnvelope(
            channel="voice",
            tenant_id="default",
            user_id="user-1",
            conversation_id=conversation_id,
            body="Remember that my favorite color is blue",
            correlation_id="CA_RESET",
            raw_payload={},
        )
    )

    counts = reset_user_data(session, tenant_id="default", user_id="user-1")
    assert counts["memory_items"] >= 0

    memory = MemoryRepository(session)
    items = memory.list_current_items(tenant_id="default", user_id="user-1")
    assert items == []

    svc = OnboardingService(session)
    assert svc.needs_onboarding(tenant_id="default", user_id="user-1") is True


def test_is_farewell_detects_goodbye_phrases():
    assert is_farewell("No, that's it for now.")
    assert is_farewell("That's all, thanks!")
    assert not is_farewell("What can you help me with?")