import pytest
from fastapi.testclient import TestClient

from danu.config import get_settings
from danu.db.models import Base
from danu.main import create_app
from danu.security.twilio_verify import compute_twilio_signature


@pytest.fixture()
def sms_client(session, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("ALLOWLIST_PHONES", "+15555550100")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    get_settings.cache_clear()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from danu.api import deps as api_deps
    from danu.db.base import get_session_factory

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


def _post_sms(client: TestClient, data: dict, headers: dict | None = None):
    return client.post(
        "/webhooks/twilio/sms",
        data=data,
        headers=headers or {},
    )


def test_inbound_sms_returns_twiml_and_persists_events(sms_client):
    response = _post_sms(
        sms_client,
        {
            "From": "+15555550100",
            "To": "+15555550200",
            "Body": "What's up?",
            "MessageSid": "SM001",
            "AccountSid": "AC001",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Message>" in response.text
    assert "What's up?" in response.text


def test_inbound_sms_rejects_unknown_sender(sms_client):
    response = _post_sms(
        sms_client,
        {
            "From": "+19999999999",
            "To": "+15555550200",
            "Body": "Hello",
            "MessageSid": "SM002",
        },
    )
    assert response.status_code == 403


def test_inbound_sms_validates_signature_when_auth_token_set(sms_client, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_auth_token")
    monkeypatch.setenv("PUBLIC_WEBHOOK_BASE_URL", "http://testserver")
    get_settings.cache_clear()

    data = {
        "From": "+15555550100",
        "To": "+15555550200",
        "Body": "Signed message",
        "MessageSid": "SM003",
    }
    unsigned = _post_sms(sms_client, data)
    assert unsigned.status_code == 403

    url = "http://testserver/webhooks/twilio/sms"
    signature = compute_twilio_signature(url, data, "test_auth_token")
    signed = _post_sms(sms_client, data, headers={"X-Twilio-Signature": signature})
    assert signed.status_code == 200
    assert "Signed message" in signed.text


def test_inbound_sms_stop_keyword(sms_client):
    response = _post_sms(
        sms_client,
        {
            "From": "+15555550100",
            "To": "+15555550200",
            "Body": "STOP",
            "MessageSid": "SMSTOP",
        },
    )
    assert response.status_code == 200
    assert "unsubscribed" in response.text.lower()


def test_inbound_sms_help_keyword(sms_client):
    response = _post_sms(
        sms_client,
        {
            "From": "+15555550100",
            "To": "+15555550200",
            "Body": "HELP",
            "MessageSid": "SMHELP",
        },
    )
    assert response.status_code == 200
    assert "journey@habitualreset.com" in response.text


def test_inbound_sms_handles_empty_body(sms_client):
    response = _post_sms(
        sms_client,
        {
            "From": "+15555550100",
            "To": "+15555550200",
            "Body": "",
            "MessageSid": "SM004",
        },
    )
    assert response.status_code == 200
    assert "didn't catch a message" in response.text.lower()