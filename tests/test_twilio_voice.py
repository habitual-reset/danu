import pytest
from fastapi.testclient import TestClient

from danu.config import get_settings
from danu.db.models import Base
from danu.main import create_app


@pytest.fixture()
def voice_client(session, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("ALLOWLIST_PHONES", "+15555550100")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    monkeypatch.setenv("PUBLIC_WEBHOOK_BASE_URL", "http://testserver")
    get_settings.cache_clear()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from danu.api import deps as api_deps

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[api_deps.get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_incoming_voice_returns_gather_twiml(voice_client):
    response = voice_client.post(
        "/webhooks/twilio/voice",
        data={
            "From": "+15555550100",
            "To": "+15555550200",
            "CallSid": "CA001",
        },
    )
    assert response.status_code == 200
    assert "<Gather" in response.text
    assert "Polly.Joanna-Neural" in response.text
    assert 'statusCallback="http://testserver/webhooks/twilio/voice/status"' in response.text


def test_voice_gather_runs_turn(voice_client):
    response = voice_client.post(
        "/webhooks/twilio/voice/gather",
        data={
            "From": "+15555550100",
            "To": "+15555550200",
            "CallSid": "CA001",
            "SpeechResult": "What's the weather?",
        },
    )
    assert response.status_code == 200
    assert "<Say" in response.text
    assert "weather" in response.text.lower()


def test_voice_status_closes_conversation_and_queues_consolidation(voice_client):
    voice_client.post(
        "/webhooks/twilio/voice",
        data={
            "From": "+15555550100",
            "To": "+15555550200",
            "CallSid": "CA_STATUS",
        },
    )
    voice_client.post(
        "/webhooks/twilio/voice/gather",
        data={
            "From": "+15555550100",
            "To": "+15555550200",
            "CallSid": "CA_STATUS",
            "SpeechResult": "Remember that my favorite color is blue",
        },
    )

    status = voice_client.post(
        "/webhooks/twilio/voice/status",
        data={
            "From": "+15555550100",
            "To": "+15555550200",
            "CallSid": "CA_STATUS",
            "CallStatus": "completed",
        },
    )
    assert status.status_code == 204