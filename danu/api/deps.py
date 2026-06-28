from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from danu.config import Settings, get_settings
from danu.db.base import get_session_factory
from danu.security.allowlist import resolve_user_from_phone
from danu.security.twilio_verify import should_validate_twilio_signature, validate_twilio_signature


@dataclass
class TwilioSmsContext:
    params: dict[str, str]
    from_number: str
    user_id: str


@dataclass
class TwilioVoiceContext:
    params: dict[str, str]
    from_number: str
    user_id: str


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_app_settings() -> Settings:
    return get_settings()


async def _parse_twilio_request(request: Request, settings: Settings) -> dict[str, str]:
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}

    if should_validate_twilio_signature(settings):
        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Twilio signature")

        webhook_url = settings.twilio_webhook_url_for(request.url.path)
        if not validate_twilio_signature(
            url=webhook_url,
            params=params,
            signature=signature,
            auth_token=settings.twilio_auth_token,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    return params


async def get_twilio_sms_context(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> TwilioSmsContext:
    params = await _parse_twilio_request(request, settings)

    from_number = params.get("From", "").strip()
    if not from_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sender number")

    user_id = resolve_user_from_phone(from_number)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sender not allowlisted")

    return TwilioSmsContext(params=params, from_number=from_number, user_id=user_id)


async def get_twilio_voice_context(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> TwilioVoiceContext:
    params = await _parse_twilio_request(request, settings)

    from_number = params.get("From", "").strip()
    if not from_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing caller number")

    user_id = resolve_user_from_phone(from_number)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Caller not allowlisted")

    return TwilioVoiceContext(params=params, from_number=from_number, user_id=user_id)