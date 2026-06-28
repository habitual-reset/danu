from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from danu.agent.llm import MockLLMClient
from danu.agent.orchestrator import AgentOrchestrator
from danu.channels.base import MessageEnvelope
from danu.db.models.task import Task
from danu.reminders.extract import extract_reminder_requests


def test_extract_reminder_at_5pm():
    now = datetime(2026, 6, 28, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    reminders = extract_reminder_requests(
        "Can you remind me at 5:00 p.m. to check in on my tasks?",
        now=now,
    )
    assert len(reminders) == 1
    assert reminders[0].fire_at.hour == 17
    assert reminders[0].fire_at.minute == 0


def test_orchestrator_schedules_sms_reminder_task(session, monkeypatch):
    monkeypatch.setenv("ALLOWLIST_PHONES", "+15555550100")
    monkeypatch.setenv("DEFAULT_USER_ID", "user-1")
    from danu.config import get_settings

    get_settings.cache_clear()

    orchestrator = AgentOrchestrator(session, llm=MockLLMClient())
    conversation_id = orchestrator.resolve_conversation(
        tenant_id="default",
        user_id="user-1",
        channel="voice",
        correlation_id="CA_REM",
    )
    orchestrator.handle_turn(
        MessageEnvelope(
            channel="voice",
            tenant_id="default",
            user_id="user-1",
            conversation_id=conversation_id,
            body="Remind me at 5:00 p.m. to check in on progress",
            correlation_id="CA_REM",
            raw_payload={},
        )
    )

    rows = list(session.scalars(select(Task).where(Task.task_type == "send_sms_reminder")).all())
    assert len(rows) == 1
    assert rows[0].payload_json["phone_number"] == "+15555550100"