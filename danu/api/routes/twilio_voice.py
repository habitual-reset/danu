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
from danu.db.repositories.conversation import ConversationRepository
from danu.usage.tracker import UsageTracker

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
    status_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/status")
    return Response(
        content=build_incoming_call_twiml(
            gather_action_url=gather_url,
            status_callback_url=status_url,
        ),
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


@router.post("/voice/status")
async def voice_status(
    voice: TwilioVoiceContext = Depends(get_twilio_voice_context),
    session: Session = Depends(get_db),
) -> Response:
    call_status = voice.params.get("CallStatus", "").strip().lower()
    call_sid = voice.params.get("CallSid", "").strip()

    if call_status != "completed" or not call_sid:
        return Response(status_code=204)

    conversations = ConversationRepository(session)
    conversation = conversations.get_by_correlation_id(call_sid)
    if conversation is None:
        return Response(status_code=204)

    duration_raw = voice.params.get("CallDuration", "0")
    try:
        duration_seconds = int(duration_raw)
    except ValueError:
        duration_seconds = 0

    UsageTracker(session).record_twilio_voice(
        tenant_id=conversation.tenant_id,
        user_id=conversation.user_id,
        duration_seconds=duration_seconds,
        conversation_id=conversation.id,
        call_sid=call_sid,
    )

    orchestrator = AgentOrchestrator(session)
    orchestrator.close_conversation(conversation.id)
    logger.info(
        "Voice call completed (%ss); consolidation queued for %s",
        duration_seconds,
        conversation.id,
    )
    return Response(status_code=204)