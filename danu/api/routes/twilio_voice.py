from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from danu.agent.orchestrator import AgentOrchestrator
from danu.api.deps import TwilioVoiceContext, get_app_settings, get_db, get_twilio_voice_context
from danu.channels.voice import (
    build_gather_response_twiml,
    build_incoming_call_twiml,
    build_no_speech_twiml,
    build_voice_envelope,
    parse_twilio_voice,
)
from danu.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])


@router.post("/voice")
async def incoming_voice(
    voice: TwilioVoiceContext = Depends(get_twilio_voice_context),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    orchestrator = AgentOrchestrator(session)
    orchestrator.resolve_conversation(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
        channel="voice",
        correlation_id=voice.params.get("CallSid"),
    )

    gather_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/gather")
    return Response(
        content=build_incoming_call_twiml(gather_action_url=gather_url),
        media_type="application/xml",
    )


@router.post("/voice/gather")
async def voice_gather(
    voice: TwilioVoiceContext = Depends(get_twilio_voice_context),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    parsed = parse_twilio_voice(voice.params)
    gather_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/gather")

    if not parsed["speech_result"]:
        return Response(
            content=build_no_speech_twiml(gather_action_url=gather_url),
            media_type="application/xml",
        )

    orchestrator = AgentOrchestrator(session)
    conversation_id = orchestrator.resolve_conversation(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
        channel="voice",
        correlation_id=parsed["call_sid"],
    )

    envelope = build_voice_envelope(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
        conversation_id=conversation_id,
        body=parsed["speech_result"],
        parsed=parsed,
        raw_payload=voice.params,
    )

    try:
        result = orchestrator.handle_turn(envelope)
        reply = result.response_text
    except Exception:
        logger.exception(
            "Voice turn failed for user=%s conversation=%s",
            voice.user_id,
            conversation_id,
        )
        session.rollback()
        reply = "Something went wrong. Please try again."

    return Response(
        content=build_gather_response_twiml(text=reply, gather_action_url=gather_url),
        media_type="application/xml",
    )